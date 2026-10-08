import re
import unicodedata

TODOS, SETOR = 'TODOS', 'SETOR'


class CategoriaDispositivo:
    """Default business impact of a device type (pre-filled and editable by the user)."""

    # category, keywords (normalized, whole words), people (int, TODOS or SETOR), loss %, label, hint
    CATEGORIAS = [
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
    OUTROS = ('OUTROS', (), 1, 50, 'Outros', '')

    @staticmethod
    def normalizar(texto):
        plain = unicodedata.normalize('NFKD', texto or '').encode('ascii', 'ignore').decode().lower()
        return ' ' + re.sub(r'[^a-z0-9]+', ' ', plain).strip() + ' '

    @classmethod
    def identificar(cls, tipo):
        words = cls.normalizar(tipo)
        return next((c for c in cls.CATEGORIAS if any(f' {k} ' in words for k in c[1])), cls.OUTROS)

    @classmethod
    def padroes(cls, tipo, empresa):
        code, _, people, loss, label, hint = cls.identificar(tipo)
        users = (empresa.total_funcionarios if people == TODOS else None if people == SETOR else people)
        return dict(categoria=code, rotulo=label, usuarios=users, regra_usuarios='FIXO' if isinstance(people, int) else people,
                    perda_pct=loss, sugerir_receita=code == 'PDV', dica=hint)
