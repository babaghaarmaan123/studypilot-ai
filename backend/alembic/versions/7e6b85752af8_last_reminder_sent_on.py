"""last reminder sent on

Records the day a student was last sent their daily plan email, so a scheduler
that fires twice does not email them twice. Nullable, and null means "never",
which is what every existing row should be.

Autogenerate again proposed dropping the server default on `past_papers.scored`.
That is a false positive from reflecting SQLite, where the stored default renders
differently from the model's; applying it would rewrite an unrelated table with a
different outcome on PostgreSQL. Removed by hand.

Revision ID: 7e6b85752af8
Revises: fef6aa8df1ea
Create Date: 2026-07-31 15:12:51.726947

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7e6b85752af8'
down_revision: Union[str, Sequence[str], None] = 'fef6aa8df1ea'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('user_settings', schema=None) as batch_op:
        batch_op.add_column(sa.Column('last_reminder_sent_on', sa.Date(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('user_settings', schema=None) as batch_op:
        batch_op.drop_column('last_reminder_sent_on')
