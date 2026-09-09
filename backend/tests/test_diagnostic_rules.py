from datetime import timedelta
from sqlalchemy import select
from app import db
from app.models import Dispositivo, Falha, Diagnostico, utcnow
from app.services.monitoring import ProbeResult, record_result
from app.services.diagnostics import refresh_company


def rule_codes(failure):
    return {c['regra'] for c in db.session.scalar(select(Diagnostico).where(Diagnostico.falha_id == failure.id)).causas}


def test_localized_and_shared_outage_require_current_peer_evidence(app, device):
    with app.app_context():
        first = db.session.get(Dispositivo, device['id'])
        peer = Dispositivo(empresa_id=first.empresa_id, nome='Outro', ip='127.0.0.2', tipo='Servidor', localizacao='TI')
        db.session.add(peer)
        db.session.flush()
        now = utcnow() - timedelta(seconds=100)
        record_result(peer, ProbeResult(4, 4, 1), now)
        for i in range(3):
            record_result(first, ProbeResult(4, 0, None), now + timedelta(seconds=i + 1))
        failure = db.session.scalar(select(Falha).where(Falha.dispositivo_id == first.id))
        assert rule_codes(failure) == {'LOCALIZADA'}
        for i in range(3):
            record_result(peer, ProbeResult(4, 0, None), now + timedelta(seconds=i + 4))
        assert 'COMPARTILHADA' in rule_codes(failure)
        assert 'LOCALIZADA' not in rule_codes(failure)
        # Stale or future observations must not support a shared-outage claim.
        peer.ultima_coleta = now - timedelta(hours=1)
        refresh_company(first.empresa_id, now + timedelta(seconds=7))
        assert 'COMPARTILHADA' not in rule_codes(failure)


def test_latency_recurrence_and_closed_diagnosis_preserved(app, device):
    with app.app_context():
        d = db.session.get(Dispositivo, device['id'])
        now = utcnow() - timedelta(minutes=10)
        for cycle in range(3):
            at = now + timedelta(minutes=cycle)
            record_result(d, ProbeResult(4, 4, 220), at)
            failure = db.session.scalar(select(Falha).where(Falha.dispositivo_id == d.id, Falha.estado == 'ABERTA'))
            assert 'LATENCIA' in rule_codes(failure)
            if cycle == 2:
                assert 'RECORRENTE' in rule_codes(failure)
            diag = db.session.scalar(select(Diagnostico).where(Diagnostico.falha_id == failure.id))
            evidence = diag.evidencias.copy()
            codes = rule_codes(failure)
            record_result(d, ProbeResult(4, 4, 1), at + timedelta(seconds=10))
            record_result(d, ProbeResult(4, 4, 1), at + timedelta(seconds=20))
            assert failure.estado == 'ENCERRADA'
            assert rule_codes(failure) == codes
            assert diag.evidencias == evidence


def test_severity_duration_and_group_boundaries(app, device):
    with app.app_context():
        d = db.session.get(Dispositivo, device['id'])
        now = utcnow() - timedelta(hours=2)
        record_result(d, ProbeResult(4, 3, 50), now)
        failure = db.session.scalar(select(Falha))
        assert failure.severidade == 'BAIXA'
        for minutes, expected in [(5, 'MEDIA'), (15, 'ALTA'), (60, 'CRITICA')]:
            refresh_company(d.empresa_id, now + timedelta(minutes=minutes))
            assert failure.severidade == expected
        for i in (2, 3):
            other = Dispositivo(empresa_id=d.empresa_id, nome=f'D{i}', ip=f'127.0.0.{i}', tipo='Servidor', localizacao='TI')
            db.session.add(other)
            db.session.flush()
            record_result(other, ProbeResult(4, 3, 50), now + timedelta(seconds=i))
        assert failure.severidade == 'ALTA'
        assert failure.justificativa['dispositivos_afetados'] == 3
