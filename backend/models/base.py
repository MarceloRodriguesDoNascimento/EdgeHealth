"""Base of every entity: the five CRUD operations of the Model layer.

commit=False only adds/flushes the change, so a use case can group several writes in one
transaction and confirm them at the end (see repositories.transacao.Transacao).
"""
from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.types import String, TypeDecorator
from app.extensions import db


class DecimalText(TypeDecorator):
    """Exact decimal stored as canonical text ("3000.00"): SQLite has no native decimal and
    Numeric would round-trip through float. Money is never a float in this application."""
    impl = String(24)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        return None if value is None else str(Decimal(value))

    def process_result_value(self, value, dialect):
        return None if value is None else Decimal(value)


def utcnow():
    # SQLite stores naive UTC; all external dates explicitly include Z.
    return datetime.now(timezone.utc).replace(tzinfo=None)


def iso(value):
    return value.isoformat(timespec='milliseconds') + 'Z' if value else None


def _finalizar(commit):
    if commit:
        db.session.commit()
    else:
        db.session.flush()


class BaseModel(db.Model):
    __abstract__ = True

    def salvar(self, commit=True):
        db.session.add(self)
        _finalizar(commit)
        return self

    def atualizar(self, commit=True, **campos):
        for nome, valor in campos.items():
            setattr(self, nome, valor)
        _finalizar(commit)
        return self

    def deletar(self, commit=True):
        db.session.delete(self)
        _finalizar(commit)

    @classmethod
    def listar_todos(cls):
        return db.session.scalars(select(cls).order_by(*cls.__table__.primary_key.columns)).all()

    @classmethod
    def buscar_por_id(cls, id):
        return db.session.get(cls, id)

    @classmethod
    def buscar_um_por(cls, **filtros):
        """First record with these column values (simple lookup by a unique or foreign key)."""
        return db.session.scalar(select(cls).filter_by(**filtros))
