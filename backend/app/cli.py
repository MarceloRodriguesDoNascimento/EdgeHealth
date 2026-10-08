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


def register_cli(app):
    @app.cli.command('seed-catalog')
    def seed():
        """Create the corrective-action catalog without creating monitoring data."""
        PopularCatalogoService().executar()
        Transacao.confirmar()
        click.echo('Catálogo de recomendações disponível.')

    @app.cli.command('monitor')
    @click.option('--once',is_flag=True,help='Executa um único ciclo e encerra.')
    def monitor(once):
        """Run the independent network collector, never the web reloader."""
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

    @app.cli.command('probe')
    @click.argument('address')
    def probe(address):
        """Execute a real bounded ICMP probe without persisting data."""
        try:
            ValidarConfiguracaoMonitorService().executar(app.config)
            result=SondaIcmpService().executar(address,app.config['MONITOR_PACKETS'],app.config['MONITOR_TIMEOUT'])
        except (CollectorError, ValueError) as error:
            raise click.ClickException(str(error)) from error
        click.echo(f'Enviados={result.sent} Recebidos={result.received} Latência_ms={result.latency_ms} Perda_pct={result.loss}')

    @app.cli.command('import-legacy')
    @click.option('--source', required=True, type=click.Path(exists=True, dir_okay=False))
    def legacy(source):
        """Import prototype records read-only into a newly migrated, empty DB."""
        try:
            result = ImportarLegadoService().executar(source)
        except (ValueError, OSError) as error:
            raise click.ClickException(str(error)) from error
        click.echo(json.dumps(result, ensure_ascii=False, indent=2))

    @app.cli.command('activate-user')
    @click.option('--email', required=True)
    @click.option('--admin', is_flag=True, help='Concede administração da empresa vinculada à conta.')
    @click.password_option(confirmation_prompt=True, prompt='Nova senha')
    def activate_user(email, admin, password):
        """Local operator recovery for an existing account; never creates a tenant."""
        try:
            AtivarUsuarioService().executar(email, password, admin)
        except ValueError as error:
            raise click.ClickException(str(error)) from error
        except BadRequest as error:
            raise click.ClickException(error.description) from error
        click.echo('Conta ativada e sessões anteriores revogadas.')

    @app.cli.command('purge-history')
    @click.option('--days', type=click.IntRange(30, 3650), default=None, help='Retenção das amostras em dias (padrão: METRIC_RETENTION_DAYS).')
    @click.option('--dry-run', is_flag=True, help='Somente informa quantos registros seriam removidos.')
    def purge_history(days, dry_run):
        """Apply the retention policy to raw samples and expired security records."""
        result = ExpurgarHistoricoService().executar(days or app.config['METRIC_RETENTION_DAYS'], dry_run)
        click.echo(json.dumps(result, ensure_ascii=False))

    @app.cli.command('anonymize-user')
    @click.option('--email', required=True)
    @click.option('--yes', is_flag=True, help='Confirma a operação irreversível.')
    def anonymize_user(email, yes):
        """Data-subject request: remove name/e-mail of an account while keeping company history."""
        if not yes:
            raise click.ClickException('Operação irreversível. Revise o pedido do titular e repita com --yes.')
        try:
            AnonimizarUsuarioService().executar(email.strip().lower())
        except ValueError as error:
            raise click.ClickException(str(error)) from error
        click.echo('Conta anonimizada e sessões revogadas.')

    @app.cli.command('backup')
    @click.option('--output', required=True, type=click.Path(dir_okay=False))
    def backup(output):
        """Consistent online copy of the SQLite database (never overwrites a file)."""
        try:
            BackupBancoService().executar(output)
        except (ValueError, OSError) as error:
            raise click.ClickException(str(error)) from error
        click.echo('Backup concluído. Armazene-o com acesso restrito: contém dados pessoais e da infraestrutura.')

    @app.cli.command('export-legacy')
    @click.option('--output', required=True, type=click.Path(dir_okay=False))
    def export_legacy(output):
        """Local operator-only export of quarantined/converted source records."""
        ExportarLegadoService().executar(output)
        click.echo('Registros legados exportados para revisão pelo operador.')
