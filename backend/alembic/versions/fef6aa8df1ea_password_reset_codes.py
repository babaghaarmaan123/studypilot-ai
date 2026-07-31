"""password reset codes

Adds the table behind "forgot my password": a hashed one-time code per request,
with an expiry, an attempt counter and a used-at stamp.

Autogenerate also proposed dropping the server default on `past_papers.scored`.
That was a false positive from reflecting SQLite, where the stored default is
rendered differently from the model's, and applying it would rewrite an
unrelated table with a different outcome on PostgreSQL. Removed by hand.

Revision ID: fef6aa8df1ea
Revises: d1dcd0daeaf9
Create Date: 2026-07-31 11:35:12.916570

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fef6aa8df1ea'
down_revision: Union[str, Sequence[str], None] = 'd1dcd0daeaf9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'password_reset_codes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('code_hash', sa.String(length=255), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('attempts', sa.Integer(), nullable=False),
        sa.Column('used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('(CURRENT_TIMESTAMP)'),
            nullable=False,
        ),
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('(CURRENT_TIMESTAMP)'),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('password_reset_codes', schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f('ix_password_reset_codes_user_id'), ['user_id'], unique=False
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('password_reset_codes', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_password_reset_codes_user_id'))

    op.drop_table('password_reset_codes')
