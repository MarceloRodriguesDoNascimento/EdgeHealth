# Funções de apoio para período e paginação
from sqlalchemy import func, select
from app.extensions import db


# Filtra pelo intervalo de datas
def filtrar_periodo(query, coluna, inicio, fim):
    if inicio:
        query = query.where(coluna >= inicio)
    if fim:
        query = query.where(coluna < fim)
    return query


# Devolve a página pedida e o total
def paginar(query, pagina, limite):
    total = db.session.scalar(select(func.count()).select_from(query.order_by(None).subquery()))
    linhas = db.session.scalars(query.offset((pagina - 1) * limite).limit(limite)).all()
    return linhas, total
