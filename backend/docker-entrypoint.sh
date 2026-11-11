#!/bin/sh
# Prepara o banco e inicia o servidor dentro do Docker
set -eu
case "${1:-web}" in
  web)
    python -m flask --app run.py db upgrade
    python -m flask --app run.py seed-catalog
    exec waitress-serve --listen=0.0.0.0:8000 --threads="${WAITRESS_THREADS:-8}" run:app
    ;;
  worker)
    exec python -m flask --app run.py monitor
    ;;
  *)
    exec "$@"
    ;;
esac
