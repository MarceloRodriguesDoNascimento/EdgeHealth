"""Service layer: one class per use case (method executar) and the domain rules as classes.

Services receive the user/company as parameters: they never read flask.request or flask.g.
Database access goes through the models (CRUD) and the repositories (special queries).
"""
