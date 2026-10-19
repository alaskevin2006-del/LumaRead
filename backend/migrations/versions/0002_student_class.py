"""Student class for bulk administration."""
from alembic import op
import sqlalchemy as sa
revision='0002'
down_revision='0001'
branch_labels=None
depends_on=None
def upgrade():
    op.add_column('users',sa.Column('class_name',sa.String(60),nullable=False,server_default=''))
def downgrade():
    op.drop_column('users','class_name')
