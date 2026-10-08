from werkzeug.exceptions import BadRequest, Conflict
from werkzeug.security import generate_password_hash
from app import validation as v
from models import Empresa, Usuario
from services.autenticacao.aceitar_termos_service import AceitarTermosService
from services.autenticacao.criar_sessao_service import CriarSessaoService, SessaoIniciada
from services.autenticacao.obter_perfil_service import ObterPerfilService


class RegistrarEmpresaService:
    """Self-service sign-up: new company, its first administrator and an open session."""

    def executar(self, dados):
        if dados.get('aceite_termos') is not True:
            raise BadRequest('Para criar a conta, aceite os Termos de Uso e declare ciência do Aviso de Privacidade.')
        company = Empresa(nome_fantasia=v.string(dados['nome_fantasia'], 'Empresa'), cnpj=v.cnpj(dados['cnpj']))
        user_email = v.email(dados['email'])
        if Empresa.buscar_um_por(cnpj=company.cnpj) or Usuario.buscar_um_por(email=user_email):
            raise Conflict('Empresa ou e-mail já cadastrado. Entre com a conta existente.')
        company.email = user_email
        company.telefone = v.string(dados.get('telefone', ''), 'Telefone', 30, 0)
        company.salvar(commit=False)
        user = Usuario(empresa_id=company.id, nome=v.string(dados['nome'], 'Nome', 100), email=user_email,
                       senha_hash=generate_password_hash(v.password(dados['senha'])), papel='ADMIN')
        AceitarTermosService.registrar_aceite(user)
        user.salvar(commit=False)
        corpo = ObterPerfilService().executar(user)
        token, csrf = CriarSessaoService().executar(user)  # confirms company, user and session together
        return SessaoIniciada(corpo, token, csrf)
