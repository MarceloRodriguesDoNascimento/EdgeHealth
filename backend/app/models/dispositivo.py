from app import db


class Dispositivo(db.Model):
    __tablename__ = 'dispositivos'

    id = db.Column(db.Integer, primary_key=True)
    empresa_id = db.Column(db.Integer, db.ForeignKey('empresas.id'), nullable=True)
    nome = db.Column(db.String(100), nullable=False)
    ip = db.Column(db.String(45), nullable=False)
    tipo = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(20), default='online')
    setor = db.Column(db.String(100))
    latencia = db.Column(db.Float, default=0.0)
    perda_pacotes = db.Column(db.Float, default=0.0)

    def __init__(self, nome, ip, tipo='desconhecido', setor='', empresa_id=None):
        self.nome = nome
        self.ip = ip
        self.tipo = tipo
        self.setor = setor
        self.empresa_id = empresa_id

    def to_dict(self):
        return {
            'id': self.id,
            'empresa_id': self.empresa_id,
            'nome': self.nome,
            'ip': self.ip,
            'tipo': self.tipo,
            'status': self.status,
            'setor': self.setor,
            'latencia': self.latencia,
            'perda_pacotes': self.perda_pacotes,
        }

    def __repr__(self):
        return f'<Dispositivo {self.nome}>'
