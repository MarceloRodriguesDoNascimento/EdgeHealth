# PythonAnywhere WSGI entry point for EdgeHealth.
# Paste this content into the WSGI configuration file linked on the "Web" tab,
# replacing SEU_USUARIO with your PythonAnywhere username.
# Settings come from /home/SEU_USUARIO/EdgeHealth/backend/.env (loaded by app/config.py).
import sys

BACKEND = '/home/SEU_USUARIO/EdgeHealth/backend'
if BACKEND not in sys.path:
    sys.path.insert(0, BACKEND)

from run import app as application  # noqa: E402  (run.py never calls app.run() on import)
