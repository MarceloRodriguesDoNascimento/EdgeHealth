import csv
import io
import json
import zipfile
from flask import g, request
from sqlalchemy import select
from werkzeug.exceptions import UnprocessableEntity
from ..extensions import db
from ..models import Dispositivo, Metrica, Falha, Diagnostico, Empresa, iso, utcnow
from ..validation import period, query_int
from .management import scoped_device
from .queries import date_filter
from .serialization import device_dict,metric_dict,failure_dict,diagnostic_dict

LIMIT=50000

def csv_bytes(rows,fields):
    out=io.StringIO(newline='')
    writer=csv.writer(out,delimiter=';')
    writer.writerow(fields)
    for row in rows:
        values=[]
        for field in fields:
            value=row.get(field)
            if isinstance(value,(dict,list)): value=json.dumps(value,ensure_ascii=False)
            if value is None: value=''
            if isinstance(value,str) and value.lstrip().startswith(('=','+','-','@')):
                value="'"+value  # Prevent spreadsheet formula injection on export.
            values.append(value)
        writer.writerow(values)
    return ('\ufeff'+out.getvalue()).encode('utf-8')


def bounded(query):
    rows=db.session.scalars(query.limit(LIMIT+1)).all()
    if len(rows)>LIMIT:
        raise UnprocessableEntity('O período contém mais de 50.000 registros. Reduza o intervalo.')
    return rows


def export_report():
    start,end=period(30)
    device_id=query_int('dispositivo_id')
    if device_id: scoped_device(device_id)
    dq=select(Dispositivo).where(Dispositivo.empresa_id==g.user.empresa_id)
    if device_id: dq=dq.where(Dispositivo.id==device_id)
    devices=bounded(dq.order_by(Dispositivo.id))
    device_ids=[d.id for d in devices]
    metrics=bounded(date_filter(select(Metrica).where(Metrica.dispositivo_id.in_(device_ids)),Metrica.coletada_em,start,end).order_by(Metrica.coletada_em,Metrica.id))
    # Include incidents overlapping the selected interval, not only newly opened ones.
    fq=select(Falha).where(Falha.dispositivo_id.in_(device_ids))
    if start: fq=fq.where((Falha.fim.is_(None)) | (Falha.fim>=start))
    if end: fq=fq.where(Falha.inicio<end)
    failures=bounded(fq.order_by(Falha.inicio,Falha.id))
    diagnoses=bounded(select(Diagnostico).where(Diagnostico.falha_id.in_([f.id for f in failures])).order_by(Diagnostico.id))
    company=db.session.get(Empresa,g.user.empresa_id)
    metadata=dict(empresa=company.nome_fantasia,cnpj=company.cnpj,inicio=iso(start),fim_exclusivo=iso(end),
                  gerado_em=iso(utcnow()),contagens=dict(dispositivos=len(devices),metricas=len(metrics),falhas=len(failures),diagnosticos=len(diagnoses)),
                  observacao='Dispositivos: inventário atual, incluindo arquivados. Falhas: ocorrências sobrepostas ao período. Diagnósticos: última análise disponível das falhas selecionadas. Datas em UTC.')
    output=io.BytesIO()
    with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED) as z:
        z.writestr('dispositivos.csv',csv_bytes([device_dict(d) for d in devices],['id','nome','ip','tipo','localizacao','status','ultima_coleta','arquivado_em']))
        z.writestr('metricas.csv',csv_bytes([metric_dict(m) for m in metrics],['id','dispositivo_id','coletada_em','respondeu','latencia_ms','pacotes_enviados','pacotes_recebidos','perda_pacotes_pct','status']))
        z.writestr('falhas.csv',csv_bytes([failure_dict(f) for f in failures],['id','dispositivo_id','dispositivo','tipo','estado','inicio','fim','duracao_segundos','severidade','justificativa','impacto','encerramento']))
        z.writestr('diagnosticos.csv',csv_bytes([diagnostic_dict(d) for d in diagnoses],['id','falha_id','estado','descricao','causas','evidencias','recomendacoes','analisado_em','versao_regras']))
        z.writestr('leia-me.json',json.dumps(metadata,ensure_ascii=False,indent=2))
    output.seek(0)
    return output
