import signal
import threading
import json
import logging
import click
from sqlalchemy import select
from werkzeug.exceptions import BadRequest
from werkzeug.security import generate_password_hash
from .extensions import db
from .models import Usuario, AuthSession, RegistroLegado
from .services.catalog import seed_catalog
from .services.monitoring import run_cycle, validate_monitor_config, real_probe, CollectorError

def register_cli(app):
    @app.cli.command('seed-catalog')
    def seed():
        """Create the corrective-action catalog without creating monitoring data."""
        seed_catalog()
        db.session.commit()
        click.echo('Catálogo de recomendações disponível.')

    @app.cli.command('monitor')
    @click.option('--once',is_flag=True,help='Executa um único ciclo e encerra.')
    def monitor(once):
        """Run the independent network collector, never the web reloader."""
        logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s %(message)s')
        try:
            validate_monitor_config(app.config)
        except ValueError as error:
            raise click.ClickException(str(error)) from error
        stop=threading.Event()
        if not once:
            signal.signal(signal.SIGINT,lambda *_:stop.set())
            signal.signal(signal.SIGTERM,lambda *_:stop.set())
        click.echo('Coletor iniciado. Cada dispositivo possui um lease exclusivo no banco.')
        while not stop.is_set():
            count=run_cycle(app)
            if once:
                click.echo(f'Coletas concluídas: {count}')
                break
            stop.wait(min(app.config['MONITOR_INTERVAL'],2))

    @app.cli.command('probe')
    @click.argument('address')
    def probe(address):
        """Execute a real bounded ICMP probe without persisting data."""
        try:
            validate_monitor_config(app.config)
            result=real_probe(address,app.config['MONITOR_PACKETS'],app.config['MONITOR_TIMEOUT'])
        except (CollectorError, ValueError) as error:
            raise click.ClickException(str(error)) from error
        click.echo(f'Enviados={result.sent} Recebidos={result.received} Latência_ms={result.latency_ms} Perda_pct={result.loss}')

    @app.cli.command('import-legacy')
    @click.option('--source', required=True, type=click.Path(exists=True, dir_okay=False))
    def legacy(source):
        """Import prototype records read-only into a newly migrated, empty DB."""
        from .services.legacy import import_legacy
        try:
            result = import_legacy(source)
        except (ValueError, OSError) as error:
            raise click.ClickException(str(error)) from error
        click.echo(json.dumps(result, ensure_ascii=False, indent=2))

    @app.cli.command('activate-user')
    @click.option('--email', required=True)
    @click.option('--admin', is_flag=True, help='Concede administração da empresa vinculada à conta.')
    @click.password_option(confirmation_prompt=True, prompt='Nova senha')
    def activate_user(email, admin, password):
        """Local operator recovery for an existing account; never creates a tenant."""
        from .validation import password as validate_password
        user = db.session.scalar(select(Usuario).where(Usuario.email == email.strip().lower()))
        if not user:
            raise click.ClickException('Conta não encontrada. Revise os registros em quarentena.')
        try:
            new_password = validate_password(password)
        except BadRequest as error:
            raise click.ClickException(error.description) from error
        user.senha_hash = generate_password_hash(new_password)
        user.ativo = True
        user.papel = 'ADMIN' if admin else user.papel
        AuthSession.query.filter_by(usuario_id=user.id).delete()
        db.session.commit()
        click.echo('Conta ativada e sessões anteriores revogadas.')

    @app.cli.command('purge-history')
    @click.option('--days', type=click.IntRange(30, 3650), default=None, help='Retenção das amostras em dias (padrão: METRIC_RETENTION_DAYS).')
    @click.option('--dry-run', is_flag=True, help='Somente informa quantos registros seriam removidos.')
    def purge_history(days, dry_run):
        """Apply the retention policy to raw samples and expired security records."""
        from .services.privacy import purge_history as purge
        result = purge(days or app.config['METRIC_RETENTION_DAYS'], dry_run)
        click.echo(json.dumps(result, ensure_ascii=False))

    @app.cli.command('anonymize-user')
    @click.option('--email', required=True)
    @click.option('--yes', is_flag=True, help='Confirma a operação irreversível.')
    def anonymize_user(email, yes):
        """Data-subject request: remove name/e-mail of an account while keeping company history."""
        from .services.privacy import anonymize_user as anonymize
        if not yes:
            raise click.ClickException('Operação irreversível. Revise o pedido do titular e repita com --yes.')
        try:
            anonymize(email.strip().lower())
        except ValueError as error:
            raise click.ClickException(str(error)) from error
        click.echo('Conta anonimizada e sessões revogadas.')

    @app.cli.command('backup')
    @click.option('--output', required=True, type=click.Path(dir_okay=False))
    def backup(output):
        """Consistent online copy of the SQLite database (never overwrites a file)."""
        from .services.privacy import backup_sqlite
        try:
            backup_sqlite(output)
        except (ValueError, OSError) as error:
            raise click.ClickException(str(error)) from error
        click.echo('Backup concluído. Armazene-o com acesso restrito: contém dados pessoais e da infraestrutura.')

    @app.cli.command('export-legacy')
    @click.option('--output', required=True, type=click.Path(dir_okay=False))
    def export_legacy(output):
        """Local operator-only export of quarantined/converted source records."""
        # Exclusive creation avoids overwriting an existing file or backup.
        with open(output, 'x', encoding='utf-8') as stream:
            for record in db.session.scalars(select(RegistroLegado).order_by(RegistroLegado.id)):
                stream.write(json.dumps(dict(tabela=record.tabela, chave=record.chave_original,
                    empresa_id=record.empresa_id, resultado=record.resultado, motivo=record.motivo,
                    fonte_sha256=record.fonte_sha256, dados=record.dados), ensure_ascii=False) + '\n')
        click.echo('Registros legados exportados para revisão pelo operador.')
