# Migration dos coletores remotos
from alembic import op
import sqlalchemy as sa


revision = 'bc4dfbaec175'
down_revision = '7c7ba005affc'
branch_labels = None
depends_on = None


# Cria a tabela de coletores e os campos de reserva e amostra
def upgrade():
    op.create_table('coletores',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('empresa_id', sa.Integer(), nullable=False),
    sa.Column('nome', sa.String(length=100), nullable=False),
    sa.Column('token_hash', sa.String(length=64), nullable=False),
    sa.Column('token_prefixo', sa.String(length=12), nullable=False),
    sa.Column('criado_em', sa.DateTime(), nullable=False),
    sa.Column('rotacionado_em', sa.DateTime(), nullable=True),
    sa.Column('revogado_em', sa.DateTime(), nullable=True),
    sa.Column('ultimo_contato', sa.DateTime(), nullable=True),
    sa.Column('versao', sa.String(length=30), nullable=True),
    sa.Column('fila_pendente', sa.Integer(), nullable=True),
    sa.Column('ultimo_erro', sa.String(length=500), nullable=True),
    sa.Column('ultimo_erro_em', sa.DateTime(), nullable=True),
    sa.Column('janela_inicio', sa.DateTime(), nullable=True),
    sa.Column('janela_requisicoes', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['empresa_id'], ['empresas.id'], name=op.f('fk_coletores_empresa_id_empresas'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_coletores')),
    sa.UniqueConstraint('token_hash', name=op.f('uq_coletores_token_hash'))
    )
    with op.batch_alter_table('coletores', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_coletores_empresa_id'), ['empresa_id'], unique=False)

    for table in ('dispositivos', 'metricas'):
        fk = f'fk_{table}_coletor_id_coletores'
        if op.get_bind().dialect.name == 'sqlite':
            op.execute(f'ALTER TABLE {table} ADD COLUMN coletor_id INTEGER '
                       f'CONSTRAINT {fk} REFERENCES coletores (id)')
        else:
            op.add_column(table, sa.Column('coletor_id', sa.Integer(), nullable=True))
            op.create_foreign_key(fk, table, 'coletores', ['coletor_id'], ['id'])
    op.create_index(op.f('ix_dispositivos_coletor_id'), 'dispositivos', ['coletor_id'], unique=False)

    op.add_column('metricas', sa.Column('amostra_uid', sa.String(length=36), nullable=True))
    op.add_column('metricas', sa.Column('recebida_em', sa.DateTime(), nullable=True))
    op.add_column('metricas', sa.Column('fora_de_ordem', sa.Boolean(), server_default=sa.text('0'), nullable=False))
    op.create_index('uq_metrica_coletor_amostra', 'metricas', ['coletor_id', 'amostra_uid'], unique=True)

    op.add_column('usuarios', sa.Column('termos_versao', sa.String(length=20), nullable=True))
    op.add_column('usuarios', sa.Column('termos_aceitos_em', sa.DateTime(), nullable=True))
    op.add_column('usuarios', sa.Column('anonimizado_em', sa.DateTime(), nullable=True))


# Remove os coletores e esses campos
def downgrade():
    if op.get_bind().dialect.name == 'sqlite':
        has_rows = op.get_bind().exec_driver_sql('SELECT 1 FROM dispositivos LIMIT 1').first()
        if has_rows:
            raise RuntimeError('Downgrade em SQLite com dados não é suportado; restaure o backup anterior à atualização.')
    with op.batch_alter_table('usuarios', schema=None) as batch_op:
        batch_op.drop_column('anonimizado_em')
        batch_op.drop_column('termos_aceitos_em')
        batch_op.drop_column('termos_versao')

    with op.batch_alter_table('metricas', schema=None) as batch_op:
        batch_op.drop_index('uq_metrica_coletor_amostra')
        batch_op.drop_column('fora_de_ordem')
        batch_op.drop_column('recebida_em')
        batch_op.drop_column('amostra_uid')
        batch_op.drop_column('coletor_id')

    with op.batch_alter_table('dispositivos', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_dispositivos_coletor_id'))
        batch_op.drop_column('coletor_id')

    with op.batch_alter_table('coletores', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_coletores_empresa_id'))

    op.drop_table('coletores')
