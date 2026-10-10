from werkzeug.exceptions import BadRequest, Conflict
from werkzeug.security import generate_password_hash
from app import validation as v


class DadosUsuario:
    """Validates and applies the fields of the user form (shared by create and update)."""

    @staticmethod
    def aplicar(usuario, dados, id, solicitante_id):
        if 'nome' in dados: usuario.nome = v.string(dados['nome'], 'Nome', 100)
        if 'email' in dados: usuario.email = v.email(dados['email'])
        if 'senha' in dados: usuario.senha_hash = generate_password_hash(v.password(dados['senha']))
        if 'papel' in dados:
            if dados['papel'] not in ('ADMIN', 'TECNICO'): raise BadRequest('Papel inválido.')
            if id == solicitante_id and dados['papel'] != 'ADMIN': raise Conflict('Não é possível remover seu próprio acesso administrativo.')
            usuario.papel = dados['papel']
        if 'ativo' in dados:
            if not isinstance(dados['ativo'], bool): raise BadRequest('ativo deve ser booleano.')
            if id == solicitante_id and not dados['ativo']: raise Conflict('Não é possível desativar sua própria conta.')
            usuario.ativo = dados['ativo']
