#!/bin/sh
# web:    apply migrations, load the catalog (idempotent) and serve API + interface.
# worker: local ICMP worker, only for devices reachable from the server itself.
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
