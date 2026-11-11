# Migration da tabela de registros do protótipo antigo
from alembic import op
import sqlalchemy as sa


revision = '7c7ba005affc'
down_revision = '55463d3f0b18'
branch_labels = None
depends_on = None


# Cria a tabela de registros legados
def upgrade():
    op.create_table('registros_legados',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('fonte_sha256', sa.String(length=64), nullable=False),
    sa.Column('tabela', sa.String(length=100), nullable=False),
    sa.Column('chave_original', sa.String(length=100), nullable=False),
    sa.Column('empresa_id', sa.Integer(), nullable=True),
    sa.Column('dados', sa.JSON(), nullable=False),
    sa.Column('resultado', sa.String(length=30), nullable=False),
    sa.Column('motivo', sa.String(length=500), nullable=False),
    sa.Column('importado_em', sa.DateTime(), nullable=False),
    sa.CheckConstraint("resultado IN ('IMPORTADO','QUARENTENA')", name=op.f('ck_registros_legados_resultado')),
    sa.ForeignKeyConstraint(['empresa_id'], ['empresas.id'], name=op.f('fk_registros_legados_empresa_id_empresas'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_registros_legados')),
    sa.UniqueConstraint('fonte_sha256', 'tabela', 'chave_original', name='uq_registro_legado_origem')
    )
    with op.batch_alter_table('registros_legados', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_registros_legados_empresa_id'), ['empresa_id'], unique=False)


# Remove a tabela de registros legados
def downgrade():
    with op.batch_alter_table('registros_legados', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_registros_legados_empresa_id'))

    op.drop_table('registros_legados')
