from flask import current_app
from models import Coletor, Diagnostico, Dispositivo, Impacto, iso, utcnow
from repositories import DiagnosticoRepository, DispositivoRepository
from services.coletores.estado_coletor import EstadoColetor
from services.custos.calculadora_prejuizo import CalculadoraPrejuizo
from services.custos.estimar_prejuizo_falha_service import EstimarPrejuizoFalhaService


class Serializador:
    """JSON representation of each entity returned by the API (the public contract)."""

    @staticmethod
    def empresa(e):
        result = {k: getattr(e, k) for k in ('id', 'nome_fantasia', 'cnpj', 'email', 'telefone')}
        result['custos'] = CalculadoraPrejuizo.resumo_empresa(e)
        return result

    @staticmethod
    def usuario(u):
        result = {k: getattr(u, k) for k in ('id', 'nome', 'email', 'empresa_id', 'papel', 'ativo', 'termos_versao')}
        result['termos_pendentes'] = u.termos_versao != current_app.config['TERMS_VERSION']
        return result

    @staticmethod
    def dispositivo(d):
        result = {k: getattr(d, k) for k in ('id', 'empresa_id', 'nome', 'ip', 'tipo', 'localizacao', 'status', 'latencia_ms', 'perda_pacotes_pct', 'erro_coleta', 'coletor_id',
                                             'usuarios_dependentes', 'perda_produtividade_pct')}
        result['receita_hora_dependente'] = CalculadoraPrejuizo.dinheiro(d.receita_hora_dependente)
        result.update(ultima_coleta=iso(d.ultima_coleta), arquivado_em=iso(d.arquivado_em),
                      desatualizado=not d.ultima_coleta or (utcnow() - d.ultima_coleta).total_seconds() > current_app.config['STALE_AFTER_SECONDS'])
        if d.coletor_id:
            coletor = Coletor.buscar_por_id(d.coletor_id)
            result.update(coletor=coletor.nome, coletor_estado=EstadoColetor.calcular(coletor))
        else:
            result.update(coletor=None, coletor_estado=None)
        return result

    @staticmethod
    def metrica(m):
        result = {k: getattr(m, k) for k in ('id', 'dispositivo_id', 'respondeu', 'latencia_ms', 'pacotes_enviados', 'pacotes_recebidos', 'perda_pacotes_pct', 'status', 'coletor_id', 'fora_de_ordem')}
        result.update(coletada_em=iso(m.coletada_em), recebida_em=iso(m.recebida_em))
        return result

    @staticmethod
    def recomendacao(r):
        return {k: getattr(r, k) for k in ('id', 'regra', 'codigo', 'titulo', 'acao')}

    @classmethod
    def diagnostico(cls, diag):
        if not diag:
            return None
        recs = DiagnosticoRepository.recomendacoes_do_diagnostico(diag.id)
        return dict(id=diag.id, falha_id=diag.falha_id, descricao=diag.descricao, causas=diag.causas,
                    evidencias=diag.evidencias, estado=diag.estado, analisado_em=iso(diag.analisado_em),
                    versao_regras=diag.versao_regras, recomendacoes=[cls.recomendacao(r) for r in recs])

    @classmethod
    def falha(cls, f, detalhe=False):
        device = Dispositivo.buscar_por_id(f.dispositivo_id)
        impact = Impacto.buscar_um_por(falha_id=f.id)
        duration = max(0, ((f.fim or utcnow()) - f.inicio).total_seconds())
        result = dict(id=f.id, dispositivo_id=f.dispositivo_id, dispositivo=device.nome, ip=device.ip,
                      localizacao=device.localizacao, tipo=f.tipo, estado=f.estado, inicio=iso(f.inicio), fim=iso(f.fim),
                      ultima_observacao=iso(f.ultima_observacao), descricao=f.descricao, severidade=f.severidade,
                      justificativa=f.justificativa, duracao_segundos=round(duration, 1), encerramento=f.encerramento,
                      impacto=dict(usuarios_afetados=impact.usuarios_afetados, origem=impact.origem,
                                   observacao=impact.observacao, atualizado_em=iso(impact.atualizado_em),
                                   custos_diretos=None if impact.custos_diretos is None else str(impact.custos_diretos)) if impact else None)
        if detalhe:
            result['diagnostico'] = cls.diagnostico(Diagnostico.buscar_um_por(falha_id=f.id))
            result['prejuizo'] = EstimarPrejuizoFalhaService().executar(f)
        return result

    @staticmethod
    def coletor(c):
        return dict(id=c.id, nome=c.nome, token_prefixo=c.token_prefixo, estado=EstadoColetor.calcular(c),
                    criado_em=iso(c.criado_em), rotacionado_em=iso(c.rotacionado_em), revogado_em=iso(c.revogado_em),
                    ultimo_contato=iso(c.ultimo_contato), versao=c.versao, fila_pendente=c.fila_pendente,
                    ultimo_erro=c.ultimo_erro, ultimo_erro_em=iso(c.ultimo_erro_em),
                    dispositivos=DispositivoRepository.contar_ativos_do_coletor(c.id))
