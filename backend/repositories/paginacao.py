from sqlalchemy import func, select
from app.extensions import db


def filtrar_periodo(query, coluna, inicio, fim):
    """Half-open interval [inicio, fim) on a date column; None leaves that side open."""
    if inicio:
        query = query.where(coluna >= inicio)
    if fim:
        query = query.where(coluna < fim)
    return query


def paginar(query, pagina, limite):
    """Returns (rows of the page, total of rows matched by the query)."""
    total = db.session.scalar(select(func.count()).select_from(query.order_by(None).subquery()))
    linhas = db.session.scalars(query.offset((pagina - 1) * limite).limit(limite)).all()
    return linhas, total
