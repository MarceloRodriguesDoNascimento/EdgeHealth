import secrets
from datetime import timedelta
from flask import current_app
from models import utcnow
from repositories import DispositivoRepository, Transacao


class ReservarDispositivoService:
    """Atomically takes the exclusive per-device lease shared by the worker and the ingestion.

    Without `coletor`: lease for the local worker (device not assigned to a collector and due).
    With `coletor`: lease for an ingestion request of the collector that owns the device.
    Returns the owner token, or None when another process holds the lease.
    """

    def executar(self, dispositivo_id, coletor=None):
        now = utcnow()
        owner = secrets.token_hex(16)
        until = now + timedelta(seconds=current_app.config['MONITOR_LEASE_SECONDS'])
        if coletor is None:
            claimed = DispositivoRepository.reservar_para_worker(dispositivo_id, owner, until, now, devido_ate=now)
        else:
            claimed = DispositivoRepository.reservar_para_coletor(dispositivo_id, coletor.id, coletor.empresa_id, owner, until, now)
        Transacao.confirmar()
        return owner if claimed else None
