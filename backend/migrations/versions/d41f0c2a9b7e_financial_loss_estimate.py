"""financial loss estimate: company costs, device business impact, direct costs

Revision ID: d41f0c2a9b7e
Revises: bc4dfbaec175
Create Date: 2026-10-07 13:00:00

Columns are only added (ALTER TABLE ... ADD COLUMN): no table is rebuilt, so the existing
history is untouched. Required columns carry server defaults for the rows already present.
Money is stored as exact decimal text (models.DecimalText).
"""
from alembic import op
import sqlalchemy as sa


revision = 'd41f0c2a9b7e'
down_revision = 'bc4dfbaec175'
branch_labels = None
depends_on = None

COMPANY = [
    sa.Column('salario_medio', sa.String(length=24), nullable=True),
    sa.Column('fator_encargos', sa.String(length=24), server_default='1.7', nullable=False),
    sa.Column('horas_mes', sa.Integer(), server_default='220', nullable=False),
    sa.Column('total_funcionarios', sa.Integer(), nullable=True),
    sa.Column('expediente_dias', sa.String(length=7), server_default='12345', nullable=False),
    sa.Column('expediente_inicio', sa.String(length=5), server_default='08:00', nullable=False),
    sa.Column('expediente_fim', sa.String(length=5), server_default='18:00', nullable=False),
    sa.Column('fuso', sa.String(length=50), server_default='America/Sao_Paulo', nullable=False),
    sa.Column('assistente_custos', sa.String(length=10), nullable=True),
]
DEVICE = [
    sa.Column('usuarios_dependentes', sa.Integer(), nullable=True),
    sa.Column('perda_produtividade_pct', sa.Integer(), nullable=True),
    sa.Column('receita_hora_dependente', sa.String(length=24), nullable=True),
]
IMPACT = [sa.Column('custos_diretos', sa.String(length=24), nullable=True)]


def upgrade():
    for table, columns in (('empresas', COMPANY), ('dispositivos', DEVICE), ('impactos', IMPACT)):
        for column in columns:
            op.add_column(table, column)


def downgrade():
    for table, columns in (('impactos', IMPACT), ('dispositivos', DEVICE), ('empresas', COMPANY)):
        with op.batch_alter_table(table) as batch:
            for column in reversed(columns):
                batch.drop_column(column.name)
