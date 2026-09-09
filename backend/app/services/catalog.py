from sqlalchemy import select
from ..extensions import db
from ..models import Recomendacao

# These are corrective-action catalog entries, never fabricated network observations.
CATALOG = [
    ('LOCALIZADA', 'local-cabo', 'Verificar conexão e alimentação', 'Verifique alimentação, cabo e porta do dispositivo. Compare com um equipamento que esteja respondendo.'),
    ('LOCALIZADA', 'local-config', 'Validar configuração', 'Confira IP, máscara e políticas de resposta ICMP do equipamento antes de concluir que há defeito físico.'),
    ('COMPARTILHADA', 'shared-link', 'Inspecionar infraestrutura compartilhada', 'Verifique os enlaces e equipamentos compartilhados pelos dispositivos afetados. A topologia não é conhecida automaticamente.'),
    ('COMPARTILHADA', 'shared-gateway', 'Comparar pontos de conectividade', 'Teste pontos intermediários autorizados e o gateway conhecido pela equipe para delimitar a interrupção.'),
    ('CONGESTIONAMENTO', 'loss-traffic', 'Verificar tráfego e interfaces', 'Analise utilização e erros das interfaces e procure tráfego intenso no intervalo da falha.'),
    ('CONGESTIONAMENTO', 'loss-link', 'Verificar enlaces', 'Compare perda e latência em pontos intermediários e inspecione os enlaces envolvidos.'),
    ('LATENCIA', 'latency-path', 'Investigar atraso', 'Compare a latência com o histórico e verifique utilização do equipamento e do caminho de rede.'),
    ('RECORRENTE', 'recurring-check', 'Investigar recorrência', 'Compare horários das ocorrências anteriores, conexões físicas e mudanças de configuração.'),
]


def seed_catalog():
    existing = set(db.session.scalars(select(Recomendacao.codigo)))
    for rule, code, title, action in CATALOG:
        if code not in existing:
            db.session.add(Recomendacao(regra=rule, codigo=code, titulo=title, acao=action))
    db.session.flush()
