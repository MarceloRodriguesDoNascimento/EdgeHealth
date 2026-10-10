from app import validation as v
from models import Empresa
from services.comum.serializador import Serializador


class AtualizarEmpresaService:
    def executar(self, empresa_id, dados):
        company = Empresa.buscar_por_id(empresa_id)
        if 'nome_fantasia' in dados: company.nome_fantasia = v.string(dados['nome_fantasia'], 'Empresa')
        if 'cnpj' in dados: company.cnpj = v.cnpj(dados['cnpj'])
        if 'email' in dados: company.email = v.email(dados['email']) if dados['email'] else None
        if 'telefone' in dados: company.telefone = v.string(dados['telefone'], 'Telefone', 30, 0)
        company.atualizar()
        return Serializador.empresa(company)
