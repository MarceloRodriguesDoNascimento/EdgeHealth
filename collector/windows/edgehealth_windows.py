"""EdgeHealth collector for Windows: setup window, scheduled-task "service" and uninstaller.

Wraps collector/edgehealth_collector.py without changing it: same Api, Queue and Collector,
same protocol. Built into a single EdgeHealthColetor.exe with PyInstaller (see build.ps1).

    EdgeHealthColetor.exe                     setup window (or status window when installed)
    EdgeHealthColetor.exe --servico           collector loop, started by the scheduled task
    EdgeHealthColetor.exe --instalar --url URL --token-file FILE   unattended install
    EdgeHealthColetor.exe --parar | --iniciar | --desinstalar

Data (config, credential, local queue, logs) lives in %ProgramData%\\EdgeHealth when run as
administrator, otherwise in %LOCALAPPDATA%\\EdgeHealth. The credential is never logged.
"""
import argparse
import ctypes
import hashlib
import json
import logging
import logging.handlers
import os
import shutil
import ssl
import subprocess
import sys
import tempfile
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from xml.sax.saxutils import escape

if not getattr(sys, 'frozen', False):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import edgehealth_collector as core  # noqa: E402  (protocol and loop, unchanged)

# Overridable (--pasta, --nome-tarefa) only to test an isolated install next to a real one.
APP = 'EdgeHealth'
TASK = 'EdgeHealth Coletor'
EXE = 'EdgeHealthColetor.exe'
DEFAULT_API = 'https://marcelodomingos.pythonanywhere.com'
MAX_CLOCK_SKEW = 120  # COLLECTOR_MAX_CLOCK_SKEW_SECONDS: the API rejects samples beyond this
SYSTEM_SID, ADMINS_SID = 'S-1-5-18', 'S-1-5-32-544'
NO_WINDOW = 0x08000000
log = logging.getLogger('edgehealth.windows')


# --- Transport -------------------------------------------------------------------------------
def use_bundled_certificates():
    """Some Windows certificate stores reject the current Let's Encrypt chain ("certificate has
    expired"). The collector's urllib calls go through this opener, which trusts the certifi
    bundle shipped in the .exe; certificate verification stays on."""
    try:
        import certifi
        context = ssl.create_default_context(cafile=certifi.where())
    except (ImportError, OSError):
        return None
    urllib.request.install_opener(urllib.request.build_opener(urllib.request.HTTPSHandler(context=context)))
    return context


# --- Locations -------------------------------------------------------------------------------
def is_admin():
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except (AttributeError, OSError):
        return False


def scope_dir(scope):
    base = os.environ['ProgramData'] if scope == 'maquina' else os.environ['LOCALAPPDATA']
    return Path(base) / APP


# A program started from a terminal inside an MSIX-packaged app (e.g. the Claude desktop app)
# inherits that package: its writes to %LOCALAPPDATA% are silently redirected to
# %LOCALAPPDATA%/Packages/<family>/LocalCache/Local. Task Scheduler runs outside the package, so
# a task pointing at the path the installer *saw* fails with 0x80070002 (file not found).
def packaged():
    length = ctypes.c_uint(0)
    try:
        return ctypes.windll.kernel32.GetCurrentPackageFullName(ctypes.byref(length), None) == 122  # buffer too small
    except (AttributeError, OSError):
        return False


def physical(path):
    """The real on-disk path of an existing folder, resolving package redirection."""
    k = ctypes.windll.kernel32
    k.CreateFileW.restype = ctypes.c_void_p
    handle = k.CreateFileW(str(path), 0, 7, None, 3, 0x02000000, None)  # OPEN_EXISTING, BACKUP_SEMANTICS (folders)
    if handle in (None, ctypes.c_void_p(-1).value):
        return Path(path)
    try:
        buf = ctypes.create_unicode_buffer(1024)
        n = k.GetFinalPathNameByHandleW(ctypes.c_void_p(handle), buf, 1024, 0)
    finally:
        k.CloseHandle(ctypes.c_void_p(handle))
    if not n or n >= 1024:
        return Path(path)
    return Path(strip_long_prefix(buf.value))


def strip_long_prefix(final):
    """GetFinalPathNameByHandle returns \\\\?\\C:\\... or \\\\?\\UNC\\server\\share\\..."""
    for prefix, replacement in ((r'\\?\UNC' + '\\', r'\\'), (r'\\?' + '\\', '')):
        if final.startswith(prefix):
            return replacement + final[len(prefix):]
    return final


def virtualized(path):
    parts = [x.lower() for x in Path(path).parts]
    return 'packages' in parts and 'localcache' in parts


def virtualized_copies():
    """User installs made from a packaged terminal, seen from outside the package."""
    root = Path(os.environ['LOCALAPPDATA']) / 'Packages'
    try:
        return sorted(d for d in root.glob(f'*/LocalCache/Local/{APP}') if (d / 'config.json').exists())
    except OSError:
        return []


def installed():
    """(scope, directory) of an existing installation, machine-wide first."""
    for scope in ('maquina', 'usuario'):
        d = scope_dir(scope)
        try:
            if (d / 'config.json').exists():
                return scope, d
        except PermissionError:  # machine install opened without elevation: the folder is restricted
            return scope, d
    copies = virtualized_copies()
    return ('usuario', copies[0]) if copies else (None, None)


def read_config(d):
    return json.loads((d / 'config.json').read_text(encoding='utf-8'))


def run(args, check=True):
    out = subprocess.run(args, capture_output=True, text=True, creationflags=NO_WINDOW)
    if check and out.returncode:
        raise RuntimeError((out.stderr or out.stdout).strip() or f'{args[0]} falhou ({out.returncode})')
    return out


def current_user_sid():
    out = run(['whoami', '/user', '/fo', 'csv', '/nh']).stdout.strip()
    return out.rsplit(',', 1)[1].strip('"')


def restrict(d, scope):
    """Only SYSTEM, Administrators and (user install) the current user can read the folder."""
    grants = [f'*{SYSTEM_SID}:(OI)(CI)F', f'*{ADMINS_SID}:(OI)(CI)F']
    if scope == 'usuario':
        grants.append(f'*{current_user_sid()}:(OI)(CI)F')
    # External tools may run outside an app package: always hand them the physical path.
    run(['icacls', str(physical(d)), '/inheritance:r', *sum((['/grant:r', g] for g in grants), [])])


# --- Connection test -------------------------------------------------------------------------
def test_connection(url, token, api_factory=core.Api, now=lambda: datetime.now(timezone.utc)):
    """Returns (ok, message, devices). Messages are for non-technical users."""
    token = token.strip()
    if not token.startswith('ehc_'):
        return False, 'A credencial começa com "ehc_". Copie-a da tela Coletores do site.', 0
    try:
        url = core.check_url(url.strip(), False)
    except SystemExit:
        return False, 'O endereço da API deve começar com https://', 0
    try:
        config = api_factory(url, token, timeout=15).call('GET', '/api/coletor/configuracao')
    except core.AuthError:
        return False, 'Credencial inválida ou revogada. Gere uma nova credencial na tela Coletores do site.', 0
    except core.ApiUnavailable as error:
        if 'Sem conexão' in str(error):
            return False, 'Sem conexão com o servidor. Verifique a internet deste computador e o endereço da API.', 0
        return False, f'O servidor não aceitou a conexão agora ({error}). Tente novamente em alguns minutos.', 0
    server = datetime.fromisoformat(config['servidor_em'].replace('Z', '+00:00'))
    skew = (now() - server).total_seconds()
    if abs(skew) > MAX_CLOCK_SKEW:
        direction = 'adiantado' if skew > 0 else 'atrasado'
        return False, (f'O relógio deste computador está {abs(skew) / 60:.0f} min {direction}. Ajuste em Configurações > '
                       'Hora e idioma > Data e hora > "Sincronizar agora" e tente de novo.'), 0
    n = len(config['dispositivos'])
    return True, f'Conectado — {n} dispositivo{"" if n == 1 else "s"}', n


# --- Scheduled task --------------------------------------------------------------------------
def task_xml(scope, command, arguments, user_sid=None):
    """Hidden task, restarted every minute on failure, no time limit, also on battery."""
    if scope == 'maquina':
        trigger = '<BootTrigger><Enabled>true</Enabled><Delay>PT30S</Delay></BootTrigger>'
        principal = f'<Principal id="Author"><UserId>{SYSTEM_SID}</UserId><RunLevel>HighestAvailable</RunLevel></Principal>'
    else:
        trigger = f'<LogonTrigger><Enabled>true</Enabled><UserId>{user_sid}</UserId><Delay>PT30S</Delay></LogonTrigger>'
        principal = (f'<Principal id="Author"><UserId>{user_sid}</UserId><LogonType>InteractiveToken</LogonType>'
                     '<RunLevel>LeastPrivilege</RunLevel></Principal>')
    return f'''<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.4" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo><Description>Coletor EdgeHealth: mede os dispositivos da rede e envia as medições por HTTPS.</Description></RegistrationInfo>
  <Triggers>{trigger}</Triggers>
  <Principals>{principal}</Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <StartWhenAvailable>true</StartWhenAvailable>
    <RunOnlyIfNetworkAvailable>false</RunOnlyIfNetworkAvailable>
    <IdleSettings><StopOnIdleEnd>false</StopOnIdleEnd><RestartOnIdle>false</RestartOnIdle></IdleSettings>
    <Hidden>true</Hidden>
    <Enabled>true</Enabled>
    <ExecutionTimeLimit>PT0S</ExecutionTimeLimit>
    <Priority>7</Priority>
    <RestartOnFailure><Interval>PT1M</Interval><Count>999</Count></RestartOnFailure>
  </Settings>
  <Actions Context="Author"><Exec><Command>{escape(command)}</Command><Arguments>{escape(arguments)}</Arguments></Exec></Actions>
</Task>
'''


def service_command(d):
    if getattr(sys, 'frozen', False):
        return str(d / EXE), f'--servico --dados "{d}"'
    return sys.executable, f'"{Path(__file__).resolve()}" --servico --dados "{d}"'


def register_task(scope, d):
    command, arguments = service_command(physical(d))  # the path Task Scheduler will actually find
    xml = task_xml(scope, command, arguments, None if scope == 'maquina' else current_user_sid())
    with tempfile.NamedTemporaryFile('w', suffix='.xml', delete=False, encoding='utf-16') as f:
        f.write(xml)
    try:
        run(['schtasks', '/Create', '/TN', TASK, '/XML', str(physical(f.name)), '/F'])  # %TEMP% may be redirected too
    finally:
        os.unlink(f.name)


def task_state():
    out = run(['schtasks', '/Query', '/TN', TASK, '/FO', 'CSV', '/NH'], check=False)
    if out.returncode:
        return None
    # "TaskName","Next Run Time","Status" — the status text follows the Windows language.
    return out.stdout.strip().rsplit(',', 1)[-1].strip('"')


def start():
    run(['schtasks', '/Change', '/TN', TASK, '/ENABLE'], check=False)
    run(['schtasks', '/Run', '/TN', TASK])


def end_service():
    """Ends the running collector. schtasks /End alone is not enough: the single-file .exe runs
    as a launcher plus a child process, and the child would keep running. The service records
    the child's PID; the setup window (same image name) is never touched."""
    run(['schtasks', '/End', '/TN', TASK], check=False)
    _, d = installed()
    pid_file = d / 'coletor.pid' if d else None
    if pid_file and pid_file.exists():
        pid = pid_file.read_text(encoding='ascii').strip()
        if pid.isdigit() and int(pid) != os.getpid():
            run(['taskkill', '/PID', pid, '/T', '/F'], check=False)
        pid_file.unlink(missing_ok=True)


def stop():
    run(['schtasks', '/Change', '/TN', TASK, '/DISABLE'], check=False)  # first, or the task would restart it
    end_service()


# --- Install / uninstall ---------------------------------------------------------------------
def install(url, token, scope):
    d = scope_dir(scope)
    (d / 'logs').mkdir(parents=True, exist_ok=True)
    restrict(d, scope)
    (d / 'coletor.token').write_text(token.strip(), encoding='ascii', newline='')
    (d / 'config.json').write_text(json.dumps(dict(api_url=url.strip().rstrip('/'), escopo=scope, versao=core.VERSION,
                                                   instalado_em=datetime.now(timezone.utc).isoformat(timespec='seconds')),
                                              indent=2), encoding='utf-8')
    if getattr(sys, 'frozen', False) and Path(sys.executable).resolve() != (d / EXE).resolve():
        stop_running_copy()
        for attempt in range(10):  # the previous service process may take a moment to exit
            try:
                shutil.copy2(sys.executable, d / EXE)  # the downloaded file can be deleted afterwards
                break
            except PermissionError:
                if attempt == 9:
                    raise
                time.sleep(1)
    register_task(scope, d)
    start()
    return physical(d)


def repair():
    """Re-registers the task of the existing installation, keeping credential, queue and logs.
    Run outside a packaged terminal, an installation that was redirected into an app's
    LocalCache is first moved to the real %LOCALAPPDATA%, so it no longer depends on that app."""
    scope, d = installed()
    if not d:
        raise RuntimeError('Nenhuma instalação do coletor encontrada.')
    source = physical(d)
    end_service()  # also the copy started by hand: it records its PID in the same folder
    target = source
    if scope == 'usuario' and virtualized(source) and not packaged():
        target = scope_dir('usuario')
        shutil.copytree(source, target, dirs_exist_ok=True, ignore=shutil.ignore_patterns('coletor.pid', EXE))
        restrict(target, 'usuario')
    if getattr(sys, 'frozen', False) and Path(sys.executable).resolve() != (target / EXE).resolve():
        for attempt in range(10):  # this (fixed) build replaces the installed copy
            try:
                shutil.copy2(sys.executable, target / EXE)
                break
            except PermissionError:
                if attempt == 9:
                    raise
                time.sleep(1)
    elif not (target / EXE).exists() and (source / EXE).exists():
        shutil.copy2(source / EXE, target / EXE)
    register_task(scope, target)
    start()
    if target != source:
        for _ in range(5):
            shutil.rmtree(source, ignore_errors=True)
            if not source.exists():
                break
            time.sleep(1)
    return physical(target)


def stop_running_copy():
    end_service()


def uninstall():
    scope, d = installed()
    run(['schtasks', '/Change', '/TN', TASK, '/DISABLE'], check=False)
    end_service()
    run(['schtasks', '/Delete', '/TN', TASK, '/F'], check=False)
    time.sleep(1)  # let the ended service process release its files
    if not d:
        return None
    own_copy = getattr(sys, 'frozen', False) and Path(sys.executable).resolve().parent == d.resolve()
    for _ in range(0 if own_copy else 5):  # an ended process can keep its .exe locked for a moment
        shutil.rmtree(d, ignore_errors=True)
        if not d.exists():
            break
        time.sleep(1)
    if d.exists():
        # Still locked (or this very .exe lives there): remove it right after this process exits.
        subprocess.Popen(f'cmd /c ping -n 4 127.0.0.1 >nul & rmdir /s /q "{d}"', creationflags=NO_WINDOW, shell=True)
    return d


# --- Service mode ----------------------------------------------------------------------------
def instance_name(scope, d):
    """One collector per installation: the lock is named after the physical data folder, so a copy
    started by hand from a packaged terminal and the scheduled task still exclude each other."""
    digest = hashlib.sha256(os.path.normcase(str(physical(d))).encode()).hexdigest()[:16]
    return ('Global\\' if scope == 'maquina' else 'Local\\') + 'EdgeHealthColetor-' + digest


def single_instance(scope, d):
    name = instance_name(scope, d)
    handle = ctypes.windll.kernel32.CreateMutexW(None, False, name)
    return handle if ctypes.windll.kernel32.GetLastError() != 183 else None  # 183: already exists


def service(d):
    d = Path(d)
    cfg = read_config(d)
    handler = logging.handlers.RotatingFileHandler(d / 'logs' / 'coletor.log', maxBytes=1_000_000, backupCount=5, encoding='utf-8')
    logging.basicConfig(level=logging.INFO, handlers=[handler], format='%(asctime)s %(levelname)s %(message)s')
    if not single_instance(cfg.get('escopo', 'maquina'), d):
        log.info('Outra instância do coletor já está em execução; encerrando esta.')
        return 0
    (d / 'coletor.pid').write_text(str(os.getpid()), encoding='ascii')
    token = (d / 'coletor.token').read_text(encoding='ascii').strip()
    collector = core.Collector(core.Api(core.check_url(cfg['api_url'], False), token),
                               core.Queue(d / 'fila.jsonl', 5000), workers=4)
    try:
        collector.run()
    except core.AuthError as error:
        # Exit code != 0: the task restarts every minute, so a new credential is picked up.
        log.error('%s Gere uma nova credencial na tela Coletores e reconfigure o coletor.', error)
        return 2
    return 0


# --- Windows ---------------------------------------------------------------------------------
def relaunch_as_admin():
    params = ' '.join(f'"{a}"' for a in sys.argv[1:])
    exe, args = (sys.executable, params) if getattr(sys, 'frozen', False) else (sys.executable, f'"{Path(__file__).resolve()}" {params}')
    return ctypes.windll.shell32.ShellExecuteW(None, 'runas', exe, args, None, 1) > 32


def gui():  # pragma: no cover - interactive
    import threading
    import tkinter as tk
    from tkinter import messagebox, ttk

    root = tk.Tk()
    root.title('Coletor EdgeHealth')
    # Icon bundled by build.ps1 (--add-data); in development it is read from collector/build.
    icon = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parents[1] / 'build')) / 'icone.ico'
    if icon.exists():
        root.iconbitmap(default=str(icon))
    root.resizable(False, False)
    frame = ttk.Frame(root, padding=22)
    frame.grid()
    style = ttk.Style()
    style.configure('Title.TLabel', font=('Segoe UI', 15, 'bold'))
    style.configure('Ok.TLabel', foreground='#15765f')
    style.configure('Err.TLabel', foreground='#a82532')
    ttk.Label(frame, text='Coletor EdgeHealth', style='Title.TLabel').grid(row=0, column=0, columnspan=2, sticky='w')
    status = ttk.Label(frame, text='', wraplength=430, justify='left')

    def show(text, ok=None):
        status.configure(text=text, style='Ok.TLabel' if ok else 'Err.TLabel' if ok is False else 'TLabel')

    def busy(button, text):
        button.state(['disabled']); show(text); root.update_idletasks()

    scope, d = installed()
    try:
        cfg = read_config(d) if d else None
    except PermissionError:
        ttk.Label(frame, text='O coletor está instalado para todo o computador. Para ver a situação, parar ou desinstalar,\n'
                              'abra este programa como administrador.', justify='left').grid(row=1, column=0, sticky='w', pady=(8, 12))
        ttk.Button(frame, text='Abrir como administrador', command=lambda: relaunch_as_admin() and root.destroy()).grid(row=2, column=0, sticky='w')
        root.mainloop()
        return
    if d:
        where = 'todo o computador (inicia com o Windows)' if scope == 'maquina' else 'este usuário (inicia ao entrar no Windows)'
        ttk.Label(frame, text=f'Instalado para {where}.\nServidor: {cfg["api_url"]}\nDados e logs: {d}', justify='left',
                  wraplength=430).grid(row=1, column=0, columnspan=2, sticky='w', pady=(8, 12))
        state = ttk.Label(frame, text='')
        state.grid(row=2, column=0, columnspan=2, sticky='w')

        def refresh():
            s = task_state()
            state.configure(text=f'Situação da tarefa: {s or "não registrada"}')

        def check():
            busy(buttons[0], 'Testando a conexão…')
            def work():
                ok, msg, _ = test_connection(cfg['api_url'], (d / 'coletor.token').read_text(encoding='ascii'))
                root.after(0, lambda: (show(msg, ok), buttons[0].state(['!disabled'])))
            threading.Thread(target=work, daemon=True).start()

        def do(action, done):
            try:
                action(); show(done, True)
            except (RuntimeError, OSError) as e:
                show(str(e), False)
            refresh()

        def remove():
            if messagebox.askyesno('Desinstalar', 'Remover o coletor, a tarefa agendada e os dados locais (credencial, fila e logs)?'):
                do(uninstall, 'Coletor desinstalado. Você pode apagar o arquivo baixado.')
                for b in buttons[1:]:
                    b.state(['disabled'])

        row = ttk.Frame(frame); row.grid(row=4, column=0, columnspan=2, sticky='w', pady=(14, 0))
        buttons = [ttk.Button(row, text='Testar conexão', command=check),
                   ttk.Button(row, text='Iniciar coletor', command=lambda: do(start, 'Coletor iniciado.')),
                   ttk.Button(row, text='Parar coletor', command=lambda: do(stop, 'Coletor parado. Ele não iniciará com o Windows até ser iniciado de novo.')),
                   ttk.Button(row, text='Abrir pasta de logs', command=lambda: os.startfile(d / 'logs')),
                   ttk.Button(row, text='Desinstalar', command=remove)]
        for i, b in enumerate(buttons):
            b.grid(row=0, column=i, padx=(0, 6))
        status.grid(row=3, column=0, columnspan=2, sticky='w', pady=(10, 0))
        refresh()
    else:
        admin = is_admin()
        ttk.Label(frame, text='Cole a credencial gerada na tela Coletores do site. O coletor mede os dispositivos da rede\n'
                              'e envia as medições por HTTPS; nenhuma porta é aberta neste computador.',
                  justify='left').grid(row=1, column=0, columnspan=2, sticky='w', pady=(6, 14))
        ttk.Label(frame, text='Endereço do EdgeHealth').grid(row=2, column=0, sticky='w')
        url = ttk.Entry(frame, width=52); url.insert(0, DEFAULT_API); url.grid(row=3, column=0, columnspan=2, sticky='we', pady=(2, 10))
        ttk.Label(frame, text='Credencial do coletor (ehc_…)').grid(row=4, column=0, sticky='w')
        token = ttk.Entry(frame, width=52, show='•'); token.grid(row=5, column=0, columnspan=2, sticky='we', pady=(2, 4)); token.focus()
        note = ('Será instalado para todo o computador e iniciará junto com o Windows.' if admin else
                'Sem permissão de administrador: será instalado só para este usuário e iniciará ao entrar no Windows.')
        ttk.Label(frame, text=note, wraplength=430, justify='left', foreground='#586b80').grid(row=6, column=0, columnspan=2, sticky='w', pady=(4, 10))
        status.grid(row=8, column=0, columnspan=2, sticky='w', pady=(10, 0))
        row = ttk.Frame(frame); row.grid(row=7, column=0, columnspan=2, sticky='w')

        def connect():
            busy(go, 'Conectando…')
            u, t = url.get(), token.get()
            def work():
                ok, msg, _ = test_connection(u, t)
                if ok:
                    try:
                        where = install(u, t, 'maquina' if admin else 'usuario')
                        msg += f'.\nColetor instalado e em execução. Dados e logs em {where}. Pode fechar esta janela.'
                    except (RuntimeError, OSError) as e:
                        ok, msg = False, f'Conectado, mas a instalação falhou: {e}'
                root.after(0, lambda: (show(msg, ok), go.state(['disabled' if ok else '!disabled'])))
            threading.Thread(target=work, daemon=True).start()

        go = ttk.Button(row, text='Conectar', command=connect)
        go.grid(row=0, column=0, padx=(0, 6))
        root.bind('<Return>', lambda _e: connect())
        if not admin:
            ttk.Button(row, text='Instalar para todo o computador (administrador)',
                       command=lambda: relaunch_as_admin() and root.destroy()).grid(row=0, column=1)
    root.mainloop()


def attach_console():
    """The .exe has no console window; command-line modes print to the calling terminal."""
    if getattr(sys, 'frozen', False) and ctypes.windll.kernel32.AttachConsole(-1):
        sys.stdout = open('CONOUT$', 'w', encoding='utf-8', errors='replace')
        sys.stderr = sys.stdout


def main(argv=None):
    use_bundled_certificates()
    p = argparse.ArgumentParser(description='Coletor EdgeHealth para Windows')
    p.add_argument('--servico', action='store_true', help='executa o coletor (usado pela tarefa agendada)')
    p.add_argument('--dados', help='pasta de dados (padrão: instalação existente)')
    p.add_argument('--instalar', action='store_true', help='instalação sem janela: exige --token-file')
    p.add_argument('--url', default=DEFAULT_API)
    p.add_argument('--token-file')
    p.add_argument('--parar', action='store_true')
    p.add_argument('--iniciar', action='store_true')
    p.add_argument('--desinstalar', action='store_true')
    p.add_argument('--reparar', action='store_true', help='re-registra a tarefa da instalação existente, sem trocar a credencial')
    p.add_argument('--pasta', help=argparse.SUPPRESS)        # test isolation: data folder name
    p.add_argument('--nome-tarefa', help=argparse.SUPPRESS)  # test isolation: scheduled task name
    args = p.parse_args(argv)
    global APP, TASK
    APP, TASK = args.pasta or APP, args.nome_tarefa or TASK
    if args.instalar or args.parar or args.iniciar or args.desinstalar or args.reparar:
        attach_console()
    if args.servico:
        d = args.dados or installed()[1]
        return service(d) if d else 2
    if args.instalar:
        token = Path(args.token_file).read_text(encoding='utf-8').strip()
        ok, msg, _ = test_connection(args.url, token)
        print(msg)
        if not ok:
            return 1
        print(f'Instalado em {install(args.url, token, "maquina" if is_admin() else "usuario")}')
        return 0
    if args.parar:
        stop(); return 0
    if args.iniciar:
        start(); return 0
    if args.reparar:
        print(f'Tarefa re-registrada; dados em {repair()}')
        return 0
    if args.desinstalar:
        d = uninstall(); print(f'Removido: {d or "nada instalado"}'); return 0
    gui()
    return 0


if __name__ == '__main__':
    sys.exit(main())
