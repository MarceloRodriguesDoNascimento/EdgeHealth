# Comandos de terminal do servidor (flask <comando>)
import signal
import threading
import json
import logging
import click
from werkzeug.exceptions import BadRequest
from repositories import Transacao
from services.diagnosticos.popular_catalogo_service import PopularCatalogoService
from services.legado.exportar_legado_service import ExportarLegadoService
from services.legado.importar_legado_service import ImportarLegadoService
from services.monitoramento import (CollectorError, ExecutarCicloMonitoramentoService, SondaIcmpService,
                                    ValidarConfiguracaoMonitorService)
from services.privacidade.anonimizar_usuario_service import AnonimizarUsuarioService
from services.privacidade.backup_banco_service import BackupBancoService
from services.privacidade.expurgar_historico_service import ExpurgarHistoricoService
from services.usuarios.ativar_usuario_service import AtivarUsuarioService


# Registra os comandos de terminal na aplicação
def register_cli(app):
    # flask seed-catalog: cadastra as recomendações do diagnóstico
    @app.cli.command('seed-catalog')
    def seed():
        PopularCatalogoService().executar()
        Transacao.confirmar()
        click.echo('Catálogo de recomendações disponível.')

    # flask monitor: worker local que mede os dispositivos em laço
    @app.cli.command('monitor')
    @click.option('--once',is_flag=True,help='Executa um único ciclo e encerra.')
    def monitor(once):
        logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s %(message)s')
        try:
            ValidarConfiguracaoMonitorService().executar(app.config)
        except ValueError as error:
            raise click.ClickException(str(error)) from error
        stop=threading.Event()
        if not once:
            signal.signal(signal.SIGINT,lambda *_:stop.set())
            signal.signal(signal.SIGTERM,lambda *_:stop.set())
        click.echo('Coletor iniciado. Cada dispositivo possui um lease exclusivo no banco.')
        ciclo=ExecutarCicloMonitoramentoService()
        while not stop.is_set():
            count=ciclo.executar(app)
            if once:
                click.echo(f'Coletas concluídas: {count}')
                break
            stop.wait(min(app.config['MONITOR_INTERVAL'],2))

    # flask probe <ip>: faz um ping de teste sem gravar nada
    @app.cli.command('probe')
    @click.argument('address')
    def probe(address):
        try:
            ValidarConfiguracaoMonitorService().executar(app.config)
            result=SondaIcmpService().executar(address,app.config['MONITOR_PACKETS'],app.config['MONITOR_TIMEOUT'])
        except (CollectorError, ValueError) as error:
            raise click.ClickException(str(error)) from error
        click.echo(f'Enviados={result.sent} Recebidos={result.received} Latência_ms={result.latency_ms} Perda_pct={result.loss}')

    # Importa o banco do protótipo antigo para um banco novo
    @app.cli.command('import-legacy')
    @click.option('--source', required=True, type=click.Path(exists=True, dir_okay=False))
    def legacy(source):
        try:
            result = ImportarLegadoService().executar(source)
        except (ValueError, OSError) as error:
            raise click.ClickException(str(error)) from error
        click.echo(json.dumps(result, ensure_ascii=False, indent=2))

    # Recupera uma conta: define nova senha e reativa
    @app.cli.command('activate-user')
    @click.option('--email', required=True)
    @click.option('--admin', is_flag=True, help='Concede administração da empresa vinculada à conta.')
    @click.password_option(confirmation_prompt=True, prompt='Nova senha')
    def activate_user(email, admin, password):
        try:
            AtivarUsuarioService().executar(email, password, admin)
        except ValueError as error:
            raise click.ClickException(str(error)) from error
        except BadRequest as error:
            raise click.ClickException(error.description) from error
        click.echo('Conta ativada e sessões anteriores revogadas.')

    # Apaga medições mais antigas que o prazo de retenção (LGPD)
    @app.cli.command('purge-history')
    @click.option('--days', type=click.IntRange(30, 3650), default=None, help='Retenção das amostras em dias (padrão: METRIC_RETENTION_DAYS).')
    @click.option('--dry-run', is_flag=True, help='Somente informa quantos registros seriam removidos.')
    def purge_history(days, dry_run):
        result = ExpurgarHistoricoService().executar(days or app.config['METRIC_RETENTION_DAYS'], dry_run)
        click.echo(json.dumps(result, ensure_ascii=False))

    # Troca nome e e-mail de uma conta por dados anônimos (LGPD)
    @app.cli.command('anonymize-user')
    @click.option('--email', required=True)
    @click.option('--yes', is_flag=True, help='Confirma a operação irreversível.')
    def anonymize_user(email, yes):
        if not yes:
            raise click.ClickException('Operação irreversível. Revise o pedido do titular e repita com --yes.')
        try:
            AnonimizarUsuarioService().executar(email.strip().lower())
        except ValueError as error:
            raise click.ClickException(str(error)) from error
        click.echo('Conta anonimizada e sessões revogadas.')

    # Faz uma cópia segura do banco SQLite
    @app.cli.command('backup')
    @click.option('--output', required=True, type=click.Path(dir_okay=False))
    def backup(output):
        try:
            BackupBancoService().executar(output)
        except (ValueError, OSError) as error:
            raise click.ClickException(str(error)) from error
        click.echo('Backup concluído. Armazene-o com acesso restrito: contém dados pessoais e da infraestrutura.')

    # Exporta os registros do protótipo que ficaram em quarentena
    @app.cli.command('export-legacy')
    @click.option('--output', required=True, type=click.Path(dir_okay=False))
    def export_legacy(output):
        ExportarLegadoService().executar(output)
        click.echo('Registros legados exportados para revisão pelo operador.')
