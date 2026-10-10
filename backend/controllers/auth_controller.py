from flask import current_app, g, jsonify, request
from app.security import clear_session_cookies, set_session_cookies
from services.autenticacao.aceitar_termos_service import AceitarTermosService
from services.autenticacao.autenticar_usuario_service import AutenticarUsuarioService
from services.autenticacao.consultar_termos_service import ConsultarTermosService
from services.autenticacao.encerrar_sessao_service import EncerrarSessaoService
from services.autenticacao.obter_perfil_service import ObterPerfilService
from services.empresas.registrar_empresa_service import RegistrarEmpresaService
from .base_controller import BaseController


class AuthController(BaseController):
    """Sign-up, login, logout, signed-in profile and Terms of Use."""

    @staticmethod
    def _com_sessao(sessao, status=200):
        response = jsonify(sessao.corpo)
        response.status_code = status
        return set_session_cookies(response, sessao.token, sessao.csrf)

    def versao_termos(self):
        return self.resposta(ConsultarTermosService().executar())

    def registrar(self):
        dados = self.payload(['nome_fantasia', 'cnpj', 'telefone', 'nome', 'email', 'senha', 'aceite_termos'],
                             ['nome_fantasia', 'cnpj', 'nome', 'email', 'senha'])
        return self._com_sessao(RegistrarEmpresaService().executar(dados), 201)

    def login(self):
        dados = self.payload(['email', 'senha'], ['email', 'senha'])
        return self._com_sessao(AutenticarUsuarioService().executar(dados['email'], dados['senha'], request.remote_addr))

    def perfil(self):
        return self.resposta(ObterPerfilService().executar(self.usuario()))

    def aceitar_termos(self):
        dados = self.payload(['aceite_termos'], ['aceite_termos'])
        return self.resposta(AceitarTermosService().executar(self.usuario(), dados['aceite_termos']))

    def logout(self):
        EncerrarSessaoService().executar(g.auth_session)
        return clear_session_cookies(current_app.response_class(status=204))
