"""Financial loss estimate of incidents. Always an ESTIMATE based on costs informed by the company.

    loss = business hours inside the incident × (people × cost/hour × productivity loss % + revenue/hour)
           + direct costs

- cost/hour = average salary × charges factor ÷ hours per month (computed, never typed);
- only the part of the incident inside the company's working hours counts (nights and weekends add 0);
- an open incident is a partial estimate up to now ("em andamento");
- incidents of the same shared outage (COMPARTILHADA, same correlation window) do not count the same
  people twice: the group uses its largest group of people, not the sum;
- without the company's costs nothing is invented: the estimate says it is not configured.
Money is Decimal end to end and serialized as text ("1234.56").
"""
import re
import unicodedata
from datetime import datetime, time, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from zoneinfo import ZoneInfo
from flask import current_app
from sqlalchemy import select
from ..extensions import db
from ..models import Diagnostico, Dispositivo, Empresa, Falha, Impacto, utcnow

CENT = Decimal('0.01')
HOUR = Decimal(3600)
TODOS, SETOR = 'TODOS', 'SETOR'
NOT_CONFIGURED = 'Configure os custos da empresa para ver a estimativa.'
DISCLAIMER = 'Estimativa baseada nos custos informados pela empresa.'

# category, keywords (normalized, whole words), people (int, TODOS or SETOR), loss %, label, hint
CATEGORIES = [
    ('PDV', ('ponto de venda', 'pdv', 'maquina de cartao', 'maquininha', 'pos', 'caixa', 'tef'), 1, 100,
     'Ponto de venda / máquina de cartão', 'Informe a receita por hora que passa por este aparelho.'),
    ('REDE', ('roteador', 'router', 'firewall', 'link', 'internet', 'gateway', 'modem'), TODOS, 100,
     'Roteador / firewall / link de internet', 'Sem ele, normalmente toda a empresa para.'),
    ('SWITCH', ('switch',), SETOR, 100, 'Switch', 'Quantas pessoas do setor dependem deste switch?'),
    ('ACCESS_POINT', ('access point', 'ponto de acesso', 'ap', 'wifi', 'wi fi', 'wireless'), SETOR, 50,
     'Access Point (Wi-Fi)', 'Quantas pessoas do setor usam este Wi-Fi?'),
    ('SERVIDOR', ('servidor', 'server', 'nas', 'storage', 'armazenamento'), TODOS, 50,
     'Servidor / NAS', 'Sistemas e arquivos compartilhados por toda a empresa.'),
    ('IMPRESSORA', ('impressora', 'printer', 'multifuncional'), 10, 30, 'Impressora', ''),
    ('VOIP', ('voip', 'telefone', 'ramal', 'phone'), 1, 100, 'Telefone VoIP', ''),
    ('SEGURANCA', ('camera', 'cftv', 'sensor', 'iot'), 0, 0, 'Câmera IP / sensor IoT',
     'Risco de segurança, não de produtividade.'),
]
OTHER = ('OUTROS', (), 1, 50, 'Outros', '')


def normalize(text):
    plain = unicodedata.normalize('NFKD', text or '').encode('ascii', 'ignore').decode().lower()
    return ' ' + re.sub(r'[^a-z0-9]+', ' ', plain).strip() + ' '


def category(tipo):
    words = normalize(tipo)
    return next((c for c in CATEGORIES if any(f' {k} ' in words for k in c[1])), OTHER)


def defaults(tipo, company):
    """Pre-filled business impact for a device type (editable by the user)."""
    code, _, people, loss, label, hint = category(tipo)
    users = (company.total_funcionarios if people == TODOS else None if people == SETOR else people)
    return dict(categoria=code, rotulo=label, usuarios=users, regra_usuarios='FIXO' if isinstance(people, int) else people,
                perda_pct=loss, sugerir_receita=code == 'PDV', dica=hint)


def money(value):
    return None if value is None else str(Decimal(value).quantize(CENT, rounding=ROUND_HALF_UP))


def cost_per_hour(company):
    if company.salario_medio is None or not company.horas_mes:
        return None
    return company.salario_medio * company.fator_encargos / Decimal(company.horas_mes)


def company_costs(company):
    hourly = cost_per_hour(company)
    return dict(configurado=hourly is not None, salario_medio=money(company.salario_medio),
                fator_encargos=str(company.fator_encargos), horas_mes=company.horas_mes,
                total_funcionarios=company.total_funcionarios,
                expediente=dict(dias=[int(d) for d in company.expediente_dias], inicio=company.expediente_inicio,
                                fim=company.expediente_fim),
                fuso=company.fuso, custo_hora=money(hourly), assistente=company.assistente_custos)


# --- Working hours -----------------------------------------------------------------------------
def business_seconds(intervals, company):
    """Seconds of the (UTC, naive) intervals that fall inside the working hours, without double
    counting overlaps. Uses the company's time zone, so DST and the local date are respected."""
    tz, utc = ZoneInfo(company.fuso), timezone.utc
    days = {int(d) for d in company.expediente_dias}
    start_t, end_t = time.fromisoformat(company.expediente_inicio), time.fromisoformat(company.expediente_fim)
    merged = []
    for s, e in sorted((s, e) for s, e in intervals if e > s):
        if merged and s <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], e)
        else:
            merged.append([s, e])
    total = 0.0
    for s, e in merged:
        s, e = s.replace(tzinfo=utc), e.replace(tzinfo=utc)
        day, last = s.astimezone(tz).date() - timedelta(days=1), e.astimezone(tz).date()
        while day <= last:
            if day.isoweekday() in days:
                ws = datetime.combine(day, start_t, tz).astimezone(utc)
                we = datetime.combine(day, end_t, tz).astimezone(utc)
                total += max(0.0, (min(e, we) - max(s, ws)).total_seconds())
            day += timedelta(days=1)
    return Decimal(round(total))


# --- One incident ----------------------------------------------------------------------------
def parameters(failure, company):
    device = db.session.get(Dispositivo, failure.dispositivo_id)
    impact = db.session.scalar(select(Impacto).where(Impacto.falha_id == failure.id))
    default = defaults(device.tipo, company)
    if impact and impact.usuarios_afetados is not None:
        users, users_source = impact.usuarios_afetados, 'informado na ocorrência'
    elif device.usuarios_dependentes is not None:
        users, users_source = device.usuarios_dependentes, 'cadastro do dispositivo'
    else:
        users, users_source = default['usuarios'] or 0, f'padrão para {default["rotulo"]}'
    loss = device.perda_produtividade_pct if device.perda_produtividade_pct is not None else default['perda_pct']
    return dict(device=device, users=users, users_source=users_source, loss=Decimal(loss),
                revenue=device.receita_hora_dependente or Decimal(0),
                direct=(impact.custos_diretos if impact and impact.custos_diretos is not None else Decimal(0)))


def brl(value):
    q = Decimal(value).quantize(CENT, rounding=ROUND_HALF_UP)
    whole, cents = f'{q:,.2f}'.split('.')
    return 'R$ ' + whole.replace(',', '.') + ',' + cents


def num(value, places=1):
    return f'{Decimal(value):.{places}f}'.replace('.', ',')


def estimate(failure, company=None, now=None):
    company = company or db.session.get(Empresa, db.session.get(Dispositivo, failure.dispositivo_id).empresa_id)
    hourly = cost_per_hour(company)
    if hourly is None:
        return dict(configurado=False, mensagem=NOT_CONFIGURED)
    now = now or utcnow()
    end = failure.fim or now
    p = parameters(failure, company)
    hours = business_seconds([(failure.inicio, end)], company) / HOUR
    productivity = hours * p['users'] * hourly * p['loss'] / 100
    revenue = hours * p['revenue']
    total = (productivity + revenue + p['direct']).quantize(CENT, rounding=ROUND_HALF_UP)
    parts = [f'{p["users"]} pessoa{"" if p["users"] == 1 else "s"} × {brl(hourly)}/h × {p["loss"]:.0f}% × {num(hours)} h de expediente']
    if p['revenue']:
        parts.append(f'{brl(p["revenue"])}/h de receita × {num(hours)} h')
    if p['direct']:
        parts.append(f'{brl(p["direct"])} de custos diretos')
    return dict(configurado=True, valor=money(total), em_andamento=failure.estado == 'ABERTA',
                conta=' + '.join(parts), aviso=DISCLAIMER,
                detalhe=dict(formula='horas de expediente × (pessoas × custo/hora × perda% + receita/hora) + custos diretos',
                             horas_expediente=str(hours.quantize(Decimal('0.01'))), pessoas=p['users'],
                             origem_pessoas=p['users_source'], custo_hora=money(hourly), perda_pct=int(p['loss']),
                             receita_hora=money(p['revenue']), custos_diretos=money(p['direct']),
                             produtividade=money(productivity), receita=money(revenue),
                             calculado_ate=end.isoformat(timespec='seconds') + 'Z'))


# --- Shared outage group ---------------------------------------------------------------------
def shared_group(failure):
    """Incidents of the same shared outage: this one has COMPARTILHADA and the others are
    unavailability incidents of the company that started within the correlation window."""
    diag = db.session.scalar(select(Diagnostico).where(Diagnostico.falha_id == failure.id))
    if not diag or 'COMPARTILHADA' not in {c.get('regra') for c in diag.causas or []}:
        return [failure]
    window = timedelta(seconds=current_app.config['DIAGNOSTIC_WINDOW_SECONDS'])
    company_id = db.session.get(Dispositivo, failure.dispositivo_id).empresa_id
    members = db.session.scalars(select(Falha).join(Dispositivo).where(
        Dispositivo.empresa_id == company_id, Falha.tipo == 'INDISPONIBILIDADE',
        Falha.inicio >= failure.inicio - window, Falha.inicio <= failure.inicio + window).order_by(Falha.id)).all()
    return members if failure in members and len(members) > 1 else [failure]


def group_estimate(members, company, now=None):
    hourly = cost_per_hour(company)
    now = now or utcnow()
    params = {f.id: parameters(f, company) for f in members}
    largest = max(members, key=lambda f: (params[f.id]['users'] * params[f.id]['loss'], params[f.id]['users']))
    lp = params[largest.id]
    hours = business_seconds([(f.inicio, f.fim or now) for f in members], company) / HOUR  # union of the outages
    productivity = hours * lp['users'] * hourly * lp['loss'] / 100
    revenue = sum((business_seconds([(f.inicio, f.fim or now)], company) / HOUR * params[f.id]['revenue'] for f in members), Decimal(0))
    direct = sum((params[f.id]['direct'] for f in members), Decimal(0))
    total = (productivity + revenue + direct).quantize(CENT, rounding=ROUND_HALF_UP)
    summed = sum(params[f.id]['users'] for f in members)
    return dict(valor=money(total), falhas=[f.id for f in members], dispositivos=len({f.dispositivo_id for f in members}),
                pessoas_consideradas=lp['users'], pessoas_somadas=summed, horas_expediente=str(hours.quantize(CENT)),
                explicacao=(f'Falha compartilhada por {len(members)} dispositivos na mesma janela. No total do grupo '
                            f'contamos o maior grupo de pessoas afetadas ({lp["users"]}), e não a soma ({summed}), '
                            'para não contar as mesmas pessoas duas vezes. Receitas e custos diretos de cada '
                            'dispositivo são somados.'))


def full_estimate(failure, now=None):
    """Estimate of one incident plus, for a shared outage, the de-duplicated group total."""
    company = db.session.get(Empresa, db.session.get(Dispositivo, failure.dispositivo_id).empresa_id)
    result = estimate(failure, company, now)
    if result['configurado']:
        members = shared_group(failure)
        result['grupo'] = group_estimate(members, company, now) if len(members) > 1 else None
    return result


def total_for(failures, company, now=None):
    """Company total without double counting shared outages, and the per-device ranking."""
    if cost_per_hour(company) is None:
        return dict(configurado=False, mensagem=NOT_CONFIGURED)
    now = now or utcnow()
    individual = {f.id: Decimal(estimate(f, company, now)['valor']) for f in failures}
    seen, total = set(), Decimal(0)
    for f in failures:
        if f.id in seen:
            continue
        members = [m for m in shared_group(f) if m.id in individual]
        if len(members) > 1:
            total += Decimal(group_estimate(members, company, now)['valor'])
            seen.update(m.id for m in members)
        else:
            total += individual[f.id]
            seen.add(f.id)
    by_device = {}
    for f in failures:
        by_device[f.dispositivo_id] = by_device.get(f.dispositivo_id, Decimal(0)) + individual[f.id]
    names = {d.id: d.nome for d in db.session.scalars(select(Dispositivo).where(Dispositivo.id.in_(by_device)))}
    top = sorted(((v, k) for k, v in by_device.items() if v > 0), reverse=True)[:5]
    return dict(configurado=True, total=money(total), falhas=len(failures), em_andamento=any(f.estado == 'ABERTA' for f in failures),
                individual={k: money(v) for k, v in individual.items()},
                top_dispositivos=[dict(dispositivo_id=k, nome=names.get(k), valor=money(v)) for v, k in top], aviso=DISCLAIMER)
