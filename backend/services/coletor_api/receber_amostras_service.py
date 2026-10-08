import logging
from datetime import timedelta
from itertools import groupby
from flask import current_app
from werkzeug.exceptions import BadRequest
from models import Dispositivo, iso, utcnow
from repositories import DispositivoRepository, MetricaRepository, Transacao
from services.monitoramento.registrar_medicao_service import RegistrarMedicaoService
from services.monitoramento.reservar_dispositivo_service import ReservarDispositivoService
from .interpretar_amostra_service import InterpretarAmostraService
from .registrar_erro_coletor_service import RegistrarErroColetorService

log = logging.getLogger(__name__)


class ReceberAmostrasService:
    """Idempotent ingestion of a batch: every sample gets ACEITA, ATRASADA, DUPLICADA, REJEITADA
    or TENTAR_NOVAMENTE (the collector keeps it queued and retries)."""

    def executar(self, coletor, dados):
        cfg = current_app.config
        samples = dados.get('amostras', [])
        errors = dados.get('erros', [])
        if not isinstance(samples, list) or not isinstance(errors, list):
            raise BadRequest('amostras e erros devem ser listas.')
        if len(samples) + len(errors) > cfg['COLLECTOR_MAX_BATCH']:
            raise BadRequest(f'Lote acima do limite de {cfg["COLLECTOR_MAX_BATCH"]} itens.')
        now = utcnow()
        allowed = {d.id: d for d in DispositivoRepository.listar_do_coletor(coletor.id, coletor.empresa_id)}
        interpretar = InterpretarAmostraService()
        results, parsed, seen = [], [], set()
        for item in samples:
            uid = item.get('id') if isinstance(item, dict) else None
            try:
                uid, device_id, observed, result = interpretar.executar(item, now)
            except (ValueError, TypeError) as error:
                results.append(dict(id=uid, resultado='REJEITADA', motivo=str(error)[:200]))
                continue
            if device_id not in allowed:
                results.append(dict(id=uid, resultado='REJEITADA', motivo='dispositivo não atribuído a este coletor'))
            elif uid in seen:
                results.append(dict(id=uid, resultado='DUPLICADA'))
            else:
                seen.add(uid)
                parsed.append((device_id, observed, uid, result))
        for item in errors:
            device_id = item.get('dispositivo_id') if isinstance(item, dict) else None
            if device_id is not None and device_id not in allowed:
                raise BadRequest('Erro informado para dispositivo não atribuído a este coletor.')
            RegistrarErroColetorService().executar(coletor, item, [allowed[device_id]] if device_id is not None else [])
        Transacao.confirmar()
        parsed.sort(key=lambda p: (p[0], p[1]))
        for device_id, group in groupby(parsed, key=lambda p: p[0]):
            results.extend(self._processar_dispositivo(coletor, device_id, list(group)))
        return dict(recebidas=len(samples), resultados=results, servidor_em=iso(utcnow()))

    def _processar_dispositivo(self, coletor, device_id, group):
        owner = ReservarDispositivoService().executar(device_id, coletor=coletor)
        if not owner:
            # Lease held by a concurrent request: the collector keeps the samples queued and retries.
            return [dict(id=uid, resultado='TENTAR_NOVAMENTE', motivo='dispositivo em processamento') for _, _, uid, _ in group]
        out = []
        try:
            existing = MetricaRepository.uids_existentes(coletor.id, [p[2] for p in group])
            device = Dispositivo.buscar_por_id(device_id)
            received = utcnow()
            registrar = RegistrarMedicaoService()
            for _, observed, uid, result in group:
                if uid in existing:
                    out.append(dict(id=uid, resultado='DUPLICADA'))
                    continue
                metric = registrar.executar(device, result, observed,
                                            dict(coletor_id=coletor.id, amostra_uid=uid, recebida_em=received))
                out.append(dict(id=uid, resultado='ATRASADA' if metric.fora_de_ordem else 'ACEITA'))
            device.atualizar(proxima_coleta=utcnow() + timedelta(seconds=current_app.config['MONITOR_INTERVAL']),
                             lease_owner=None, lease_until=None)
            return out
        except Exception:
            Transacao.desfazer()
            log.exception('Ingestão não concluída coletor=%s dispositivo=%s', coletor.id, device_id)
            DispositivoRepository.liberar_reserva(device_id, owner)
            Transacao.confirmar()
            return [dict(id=uid, resultado='TENTAR_NOVAMENTE', motivo='erro interno') for _, _, uid, _ in group]
