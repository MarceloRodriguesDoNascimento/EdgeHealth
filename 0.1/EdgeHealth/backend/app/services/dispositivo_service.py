from app import db
from app.models.dispositivo import Dispositivo

class DispositivoService:

    @staticmethod
    def criar(dados):
        """Cria e salva um novo dispositivo no banco de dados."""
        novo_dispositivo = Dispositivo(
            nome=dados.get('nome'),
            ip=dados.get('ip'),
            tipo=dados.get('tipo'),
            setor=dados.get('setor')
        )
        db.session.add(novo_dispositivo)
        db.session.commit()
        return novo_dispositivo

    @staticmethod
    def listar_todos():
        """Retorna todos os dispositivos cadastrados."""
        return Dispositivo.query.all()

    @staticmethod
    def buscar_por_id(dispositivo_id):
        """Busca um dispositivo específico pelo ID."""
        return Dispositivo.query.get(dispositivo_id)

    @staticmethod
    def atualizar(dispositivo_id, dados):
        """Atualiza os dados de um dispositivo existente."""
        dispositivo = Dispositivo.query.get(dispositivo_id)
        if not dispositivo:
            return None
        
        dispositivo.nome = dados.get('nome', dispositivo.nome)
        dispositivo.ip = dados.get('ip', dispositivo.ip)
        dispositivo.tipo = dados.get('tipo', dispositivo.tipo)
        dispositivo.setor = dados.get('setor', dispositivo.setor)
        dispositivo.status = dados.get('status', dispositivo.status)
        
        db.session.commit()
        return dispositivo

    @staticmethod
    def deletar(dispositivo_id):
        """Remove um dispositivo do banco de dados."""
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
