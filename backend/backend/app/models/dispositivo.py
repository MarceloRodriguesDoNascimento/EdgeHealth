from app import db

class Dispositivo(db.Model):
    __tablename__ = 'dispositivos'

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    ip = db.Column(db.String(45), nullable=False)
    tipo = db.Column(db.String(50), nullable=False)  # Ex: Roteador, Switch
    status = db.Column(db.String(20), default='online') # Ex: online, instável, offline
    setor = db.Column(db.String(100))
    latencia = db.Column(db.Float, default=0.0)
    perda_pacotes = db.Column(db.Float, default=0.0)

    # Construtor opcional para facilitar a criação do objeto
    def __init__(self, nome, ip, tipo, setor):
        self.nome = nome
        self.ip = ip
        self.tipo = tipo
        self.setor = setor

    def to_dict(self):
        return {
            'id': self.id,
            'nome': self.nome,
            'ip': self.ip,
            'tipo': self.tipo,
            'status': self.status,
            'setor': self.setor,
            'latencia': self.latencia,
            'perda_pacotes': self.perda_pacotes,
        }

    # Método para representar o objeto (ajuda no debug)
    def __repr__(self):
        return f'<Dispositivo {self.nome}>'
