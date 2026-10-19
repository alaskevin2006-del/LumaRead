"""Keep reading eligibility stable when the comparison provider changes."""
from alembic import op
import sqlalchemy as sa
revision='0003'
down_revision='0002'
branch_labels=None
depends_on=None

def upgrade():
    op.add_column('reading_sessions',sa.Column('scoring_mode',sa.String(32),nullable=True))
    op.add_column('reading_sessions',sa.Column('required_page_ids',sa.JSON(),nullable=True))

def downgrade():
    op.drop_column('reading_sessions','required_page_ids')
    op.drop_column('reading_sessions','scoring_mode')
