from decimal import Decimal
from flask import current_app, g
from sqlalchemy import select, func
from werkzeug.exceptions import BadRequest, Conflict, NotFound
from werkzeug.security import generate_password_hash
from ..extensions import db
from ..models import Empresa, Usuario, Dispositivo, Falha, AuthSession, utcnow
from .. import validation as v


def scoped_device(id, include_archived=True):
    query=select(Dispositivo).where(Dispositivo.id==id,Dispositivo.empresa_id==g.user.empresa_id)
    if not include_archived:
        query=query.where(Dispositivo.arquivado_em.is_(None))
    d=db.session.scalar(query)
    if not d:
        raise NotFound('Dispositivo não encontrado.')
    return d


def scoped_failure(id):
    f=db.session.scalar(select(Falha).join(Dispositivo).where(Falha.id==id,Dispositivo.empresa_id==g.user.empresa_id))
    if not f:
        raise NotFound('Ocorrência não encontrada.')
    return f


def accept_terms(user):
    user.termos_versao=current_app.config['TERMS_VERSION']
    user.termos_aceitos_em=utcnow()


def create_company_account(data):
    if data.get('aceite_termos') is not True:
        raise BadRequest('Para criar a conta, aceite os Termos de Uso e declare ciência do Aviso de Privacidade.')
    company=Empresa(nome_fantasia=v.string(data['nome_fantasia'],'Empresa'),cnpj=v.cnpj(data['cnpj']))
    user_email=v.email(data['email'])
    if db.session.scalar(select(Empresa.id).where(Empresa.cnpj==company.cnpj)) or db.session.scalar(select(Usuario.id).where(Usuario.email==user_email)):
        raise Conflict('Empresa ou e-mail já cadastrado. Entre com a conta existente.')
    company.email=user_email
    company.telefone=v.string(data.get('telefone',''),'Telefone',30,0)
    db.session.add(company)
    db.session.flush()
    user=Usuario(empresa_id=company.id,nome=v.string(data['nome'],'Nome',100),email=user_email,
                 senha_hash=generate_password_hash(v.password(data['senha'])),papel='ADMIN')
    accept_terms(user)
    db.session.add(user)
    db.session.flush()
    return user


def update_company(data):
    company=db.session.get(Empresa,g.user.empresa_id)
    if 'nome_fantasia' in data: company.nome_fantasia=v.string(data['nome_fantasia'],'Empresa')
    if 'cnpj' in data: company.cnpj=v.cnpj(data['cnpj'])
    if 'email' in data: company.email=v.email(data['email']) if data['email'] else None
    if 'telefone' in data: company.telefone=v.string(data['telefone'],'Telefone',30,0)
    db.session.commit()
    return company


def save_user(data,id=None):
    user=db.session.scalar(select(Usuario).where(Usuario.id==id,Usuario.empresa_id==g.user.empresa_id)) if id else Usuario(empresa_id=g.user.empresa_id)
    if id and not user: raise NotFound('Usuário não encontrado.')
    if 'nome' in data: user.nome=v.string(data['nome'],'Nome',100)
    if 'email' in data: user.email=v.email(data['email'])
    if 'senha' in data: user.senha_hash=generate_password_hash(v.password(data['senha']))
    if 'papel' in data:
        if data['papel'] not in ('ADMIN','TECNICO'): raise BadRequest('Papel inválido.')
        if id==g.user.id and data['papel']!='ADMIN': raise Conflict('Não é possível remover seu próprio acesso administrativo.')
        user.papel=data['papel']
    if 'ativo' in data:
        if not isinstance(data['ativo'],bool): raise BadRequest('ativo deve ser booleano.')
        if id==g.user.id and not data['ativo']: raise Conflict('Não é possível desativar sua própria conta.')
        user.ativo=data['ativo']
    if not id:
        user.papel=user.papel or 'TECNICO'
        db.session.add(user)
    elif 'senha' in data or data.get('ativo') is False or 'papel' in data:
        AuthSession.query.filter_by(usuario_id=user.id).delete()
    db.session.commit()
    return user


def save_device(data,id=None):
    device=scoped_device(id,False) if id else Dispositivo(empresa_id=g.user.empresa_id)
    if device.lease_until and device.lease_until>utcnow():
        raise Conflict('Há uma coleta em andamento. Aguarde sua conclusão para editar.')
    old_ip=device.ip
    if 'nome' in data: device.nome=v.string(data['nome'],'Nome',100)
    if 'ip' in data: device.ip=v.ip(data['ip'])
    if 'tipo' in data: device.tipo=v.string(data['tipo'],'Tipo',50)
    if 'localizacao' in data: device.localizacao=v.string(data['localizacao'],'Localização',150)
    if 'coletor_id' in data:
        from .collectors import assignable_collector
        collector_id=assignable_collector(data['coletor_id'])
        if collector_id!=device.coletor_id:
            # A different measurement point: the next cycle collects from the new origin.
            device.coletor_id=collector_id
            device.erro_coleta=None
            device.proxima_coleta=utcnow()
    business_impact(device,data,creating=not id)
    if id and old_ip!=device.ip:
        current=db.session.scalar(select(Falha).where(Falha.dispositivo_id==id,Falha.estado=='ABERTA'))
        if current: raise Conflict('Encerre a ocorrência por recuperação ou arquive o dispositivo antes de alterar o IP.')
        device.status=None
        device.ultima_coleta=None
        device.latencia_ms=device.perda_pacotes_pct=None
        device.falhas_consecutivas=device.sucessos_consecutivos=0
        device.proxima_coleta=utcnow()
    if not id: db.session.add(device)
    db.session.commit()
    return device


def business_impact(device,data,creating):
    """People, productivity loss and direct revenue that depend on the device. A new device without
    these fields gets the defaults for its type (editable); explicit null clears a value."""
    if 'usuarios_dependentes' in data:
        device.usuarios_dependentes=v.optional(data['usuarios_dependentes'],v.integer,'Pessoas que usam o aparelho')
    if 'perda_produtividade_pct' in data:
        device.perda_produtividade_pct=v.optional(data['perda_produtividade_pct'],v.integer,'Perda de produtividade (%)',0,100)
    if 'receita_hora_dependente' in data:
        device.receita_hora_dependente=v.optional(data['receita_hora_dependente'],v.decimal_value,'Receita por hora')
    if creating:
        from .costs import defaults
        default=defaults(device.tipo,db.session.get(Empresa,device.empresa_id))
        if 'usuarios_dependentes' not in data: device.usuarios_dependentes=default['usuarios']
        if 'perda_produtividade_pct' not in data: device.perda_produtividade_pct=default['perda_pct']


def update_company_costs(data):
    company=db.session.get(Empresa,g.user.empresa_id)
    if 'salario_medio' in data: company.salario_medio=v.optional(data['salario_medio'],v.decimal_value,'Salário médio')
    if 'fator_encargos' in data: company.fator_encargos=v.decimal_value(data['fator_encargos'],'Fator de encargos',Decimal('1'),Decimal('5'))
    if 'horas_mes' in data: company.horas_mes=v.integer(data['horas_mes'],'Horas por mês',1,744)
    if 'total_funcionarios' in data: company.total_funcionarios=v.optional(data['total_funcionarios'],v.integer,'Total de funcionários')
    if 'expediente' in data:
        shift=data['expediente']
        if not isinstance(shift,dict) or set(shift)-{'dias','inicio','fim'}:
            raise BadRequest('Expediente: informe dias, inicio e fim.')
        days=v.weekdays(shift.get('dias',[int(d) for d in company.expediente_dias]))
        start=v.clock(shift.get('inicio',company.expediente_inicio),'Início do expediente')
        end=v.clock(shift.get('fim',company.expediente_fim),'Fim do expediente')
        if start>=end: raise BadRequest('O fim do expediente deve ser depois do início.')
        company.expediente_dias,company.expediente_inicio,company.expediente_fim=days,start,end
    if 'fuso' in data: company.fuso=v.timezone_name(data['fuso'])
    company.assistente_custos='CONCLUIDO'
    db.session.commit()
    return company


def skip_cost_assistant():
    company=db.session.get(Empresa,g.user.empresa_id)
    if company.assistente_custos is None:
        company.assistente_custos='PULADO'
        db.session.commit()
    return company


def restore_device(id):
    device=scoped_device(id)
    if not device.arquivado_em:
        raise Conflict('O dispositivo não está arquivado.')
    duplicate=db.session.scalar(select(Dispositivo.id).where(Dispositivo.empresa_id==device.empresa_id,
        Dispositivo.ip==device.ip,Dispositivo.arquivado_em.is_(None)))
    if duplicate:
        raise Conflict('Já existe um dispositivo ativo com este IP. Arquive-o ou altere o IP antes de desarquivar.')
    device.arquivado_em=None
    # History is preserved; the current state restarts from a fresh measurement instead of showing stale data.
    device.status=None
    device.ultima_coleta=None
    device.latencia_ms=device.perda_pacotes_pct=None
    device.falhas_consecutivas=device.sucessos_consecutivos=0
    device.erro_coleta=None
    device.lease_owner=device.lease_until=None
    device.proxima_coleta=utcnow()
    db.session.commit()
    return device


def archive_device(id):
    device=scoped_device(id,False)
    if device.lease_until and device.lease_until>utcnow():
        raise Conflict('Há uma coleta em andamento. Aguarde sua conclusão para arquivar.')
    now=utcnow()
    device.arquivado_em=now
    current=db.session.scalar(select(Falha).where(Falha.dispositivo_id==id,Falha.estado=='ABERTA'))
    if current:
        current.estado='ENCERRADA'
        current.fim=now
        current.ultima_observacao=now
        current.encerramento='ARQUIVAMENTO'
        from .diagnostics import refresh_company
        refresh_company(device.empresa_id,now,extra_failure=current)
    db.session.commit()
