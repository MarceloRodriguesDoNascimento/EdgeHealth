# API temporária usada nos testes do frontend
import json
import os
import sys
import tempfile
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from flask_migrate import upgrade
from werkzeug.serving import make_server
from app import create_app, db
from models import Dispositivo, utcnow
from services.diagnosticos.popular_catalogo_service import PopularCatalogoService
from services.monitoramento import ProbeResult, ColetarDispositivoService


def main():
    with tempfile.TemporaryDirectory(prefix='edgehealth-ui-') as directory:
        app = create_app({'TESTING': True, 'SQLALCHEMY_DATABASE_URI': 'sqlite:///' + directory + '/test.db',
                          'SESSION_COOKIE_SECURE': False, 'LOGIN_MAX_ATTEMPTS': 100})
        with app.app_context():
            upgrade(directory=str(Path(__file__).resolve().parents[1] / 'migrations'))
            PopularCatalogoService().executar()
            db.session.commit()
        server = make_server('127.0.0.1', int(os.environ.get('UI_SERVER_PORT', 0)), app, threaded=True)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        print(json.dumps({'ready': f'http://127.0.0.1:{server.server_port}'}), flush=True)
        try:
            for line in sys.stdin:
                command = json.loads(line)
                with app.app_context():
                    device = db.session.get(Dispositivo, command['device_id'])
                    if not device:
                        raise ValueError('Dispositivo de teste não encontrado')
                    device.proxima_coleta = utcnow()
                    db.session.commit()
                result = ProbeResult(command['sent'], command['received'], command['latency_ms'])
                success = ColetarDispositivoService().executar(app, command['device_id'], lambda *_: result)
                print(json.dumps({'id': command['id'], 'success': success}), flush=True)
        finally:
            server.shutdown()
            thread.join(timeout=5)
            with app.app_context():
                db.session.remove()
                db.engine.dispose()


if __name__ == '__main__':
    main()
