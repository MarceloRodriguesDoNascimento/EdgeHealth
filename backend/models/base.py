# Classe-mãe dos Models com o CRUD e utilidades de data
from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.types import String, TypeDecorator
from app.extensions import db


# Coluna de dinheiro guardada como texto exato
class DecimalText(TypeDecorator):
    impl = String(24)
    cache_ok = True

    # Converte Decimal em texto ao gravar
    def process_bind_param(self, value, dialect):
        return None if value is None else str(Decimal(value))

    # Converte texto em Decimal ao ler
    def process_result_value(self, value, dialect):
        return None if value is None else Decimal(value)


# Data e hora atual em UTC
def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


# Formata data no padrão ISO usado no JSON
def iso(value):
    return value.isoformat(timespec='milliseconds') + 'Z' if value else None


# Confirma (commit) ou só envia (flush) as alterações
def _finalizar(commit):
    if commit:
        db.session.commit()
    else:
        db.session.flush()


# Base de todas as tabelas, com o CRUD
class BaseModel(db.Model):
    __abstract__ = True

    # CREATE: insere o objeto no banco
    def salvar(self, commit=True):
        db.session.add(self)
        _finalizar(commit)
        return self

    # UPDATE: altera campos e grava
    def atualizar(self, commit=True, **campos):
        for nome, valor in campos.items():
            setattr(self, nome, valor)
        _finalizar(commit)
        return self

    # DELETE: remove a linha do banco
    def deletar(self, commit=True):
        db.session.delete(self)
        _finalizar(commit)

    # READ: todas as linhas da tabela
    @classmethod
    def listar_todos(cls):
        return db.session.scalars(select(cls).order_by(*cls.__table__.primary_key.columns)).all()

    # READ: uma linha pela chave primária
    @classmethod
    def buscar_por_id(cls, id):
        return db.session.get(cls, id)

    # READ: primeira linha com os valores informados
    @classmethod
    def buscar_um_por(cls, **filtros):
        return db.session.scalar(select(cls).filter_by(**filtros))
