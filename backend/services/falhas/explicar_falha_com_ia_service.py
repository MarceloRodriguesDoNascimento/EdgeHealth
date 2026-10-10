from flask import current_app
from werkzeug.exceptions import ServiceUnavailable
from app import validation as v
from models import Dispositivo, iso, utcnow
from services.comum.serializador import Serializador
from services.falhas.obter_falha_service import ObterFalhaService
from services.ia.gemini_service import GeminiService
from services.ia.limite_uso_ia import LimiteUsoIa


class ExplicarFalhaComIaService:
    """Plain-language explanation of an incident for a non-technical manager, written by an LLM from
    what the system already computed. The AI explains; it never replaces or changes the rule-based
    diagnosis.

    Privacy (LGPD): the prompt is built from an ALLOW-list of technical fields only. Names of people
    or devices, e-mails, CNPJ, IP, company name and free-text notes are never sent."""

    INSTRUCAO = (
        'Você é um analista de redes que explica incidentes para um gestor sem conhecimento técnico, em português do Brasil. '
        'Use somente os dados fornecidos; não invente causas, valores ou fatos e não contradiga o diagnóstico do sistema. '
        'As causas do diagnóstico são hipóteses: apresente-as como prováveis. '
        'Responda em texto simples, sem markdown, sem listas com símbolos, com no máximo 180 palavras, '
        'em três parágrafos que começam exatamente com "O que aconteceu:", "Impacto provável:" e "Próximos passos:".')

    def __init__(self, gemini=None):
        self.gemini = gemini or GeminiService()

    def executar(self, empresa_id, id, dados):
        falha = ObterFalhaService().buscar(empresa_id, id)  # 404 of another company before payload errors
        v.json_object(dados, ())  # the request carries no fields: the prompt is never taken from the client
        if not GeminiService.disponivel():
            raise ServiceUnavailable(GeminiService.SEM_CHAVE)
        LimiteUsoIa.registrar(empresa_id, current_app.config['IA_EXPLICACOES_POR_HORA'])
        texto = self.gemini.executar(self.INSTRUCAO, self.prompt(falha))
        return dict(texto=texto, modelo=current_app.config['GEMINI_MODEL'], gerado_em=iso(utcnow()),
                    aviso='Texto gerado por IA a partir do diagnóstico do sistema; confira antes de agir.')

    @staticmethod
    def contexto(falha):
        """Only technical data (allow-list)."""
        dados = Serializador.falha(falha, True)
        dispositivo = Dispositivo.buscar_por_id(falha.dispositivo_id)
        diag = dados.get('diagnostico') or {}
        prejuizo = dados.get('prejuizo') or {}
        horas, resto = divmod(int(dados['duracao_segundos']), 3600)
        return dict(
            tipo_ocorrencia=dados['tipo'], situacao=dados['estado'], severidade=dados['severidade'],
            motivos_da_severidade=(dados.get('justificativa') or {}).get('motivos', []),
            inicio_utc=dados['inicio'], fim_utc=dados['fim'], duracao=f'{horas} h {resto // 60} min',
            tipo_do_dispositivo=dispositivo.tipo, localizacao_do_dispositivo=dispositivo.localizacao,
            usuarios_afetados_informados=(dados.get('impacto') or {}).get('usuarios_afetados'),
            diagnostico=dict(estado=diag.get('estado'), resumo=diag.get('descricao'),
                             causas_provaveis=[dict(regra=c.get('regra'), descricao=c.get('descricao')) for c in diag.get('causas') or []]),
            recomendacoes=[dict(titulo=r['titulo'], acao=r['acao']) for r in diag.get('recomendacoes') or []],
            prejuizo_estimado=(dict(valor_reais=prejuizo.get('valor'), em_andamento=prejuizo.get('em_andamento'),
                                    calculo=prejuizo.get('conta'),
                                    grupo_compartilhado=(prejuizo.get('grupo') or {}).get('valor'))
                               if prejuizo.get('configurado') else 'não configurado pela empresa'))

    @classmethod
    def prompt(cls, falha):
        c = cls.contexto(falha)
        linhas = [f'{chave.replace("_", " ")}: {valor}' for chave, valor in c.items()
                  if chave not in ('diagnostico', 'recomendacoes', 'motivos_da_severidade')]
        linhas.append('motivos da severidade: ' + ('; '.join(c['motivos_da_severidade']) or 'não informados'))
        d = c['diagnostico']
        linhas.append(f'diagnóstico do sistema ({d["estado"]}): {d["resumo"]}')
        linhas += [f'- causa provável {x["regra"]}: {x["descricao"]}' for x in d['causas_provaveis']] or ['- sem causa provável determinada']
        linhas.append('recomendações do sistema:')
        linhas += [f'- {r["titulo"]}: {r["acao"]}' for r in c['recomendacoes']] or ['- nenhuma recomendação associada']
        return 'Explique esta ocorrência de rede ao gestor.\n\n' + '\n'.join(linhas)
