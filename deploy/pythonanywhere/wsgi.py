# Arquivo WSGI que liga o EdgeHealth no PythonAnywhere
import sys

BACKEND = '/home/SEU_USUARIO/EdgeHealth/backend'
if BACKEND not in sys.path:
    sys.path.insert(0, BACKEND)

from run import app as application
