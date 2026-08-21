from app import db
from app.models.dispositivo import Dispositivo


class DispositivoService:

    @staticmethod
    def criar(dados):
        dados = dados or {}
        novo_dispositivo = Dispositivo(
            nome=dados.get('nome'),
            ip=dados.get('ip'),
            tipo=dados.get('tipo', 'desconhecido'),
            setor=dados.get('setor', ''),
            empresa_id=dados.get('empresa_id')
        )
        db.session.add(novo_dispositivo)
        db.session.commit()
        return novo_dispositivo

    @staticmethod
    def listar_todos():
        return Dispositivo.query.order_by(Dispositivo.id.asc()).all()

    @staticmethod
    def buscar_por_id(dispositivo_id):
        return Dispositivo.query.get(dispositivo_id)

    @staticmethod
    def atualizar(dispositivo_id, dados):
        dados = dados or {}
        dispositivo = Dispositivo.query.get(dispositivo_id)
        if not dispositivo:
            return None

        dispositivo.nome = dados.get('nome', dispositivo.nome)
        dispositivo.ip = dados.get('ip', dispositivo.ip)
        dispositivo.tipo = dados.get('tipo', dispositivo.tipo)
        dispositivo.setor = dados.get('setor', dispositivo.setor)
        dispositivo.status = dados.get('status', dispositivo.status)
        dispositivo.empresa_id = dados.get('empresa_id', dispositivo.empresa_id)

        db.session.commit()
        return dispositivo

    @staticmethod
    def deletar(dispositivo_id):
        dispositivo = Dispositivo.query.get(dispositivo_id)
        if not dispositivo:
            return False

        db.session.delete(dispositivo)
        db.session.commit()
        return True


def listar_dispositivos():
    return DispositivoService.listar_todos()


def criar_dispositivo(dados):
    return DispositivoService.criar(dados)


def atualizar_dispositivo(dispositivo_id, dados):
    return DispositivoService.atualizar(dispositivo_id, dados)


def excluir_dispositivo(dispositivo_id):
    return DispositivoService.deletar(dispositivo_id)
