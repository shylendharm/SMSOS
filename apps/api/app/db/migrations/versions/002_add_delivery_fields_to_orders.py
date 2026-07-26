"""Add delivery fields to orders table

Revision ID: 002_add_delivery_fields
Revises: e48955c85206
Create Date: 2026-07-26
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '002_add_delivery_fields'
down_revision: Union[str, None] = 'e48955c85206'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    op.add_column('orders', sa.Column('delivery_location', sa.String(length=255), nullable=True))
    op.add_column('orders', sa.Column('order_type', sa.String(length=30), server_default='DELIVERY', nullable=False))
    op.add_column('orders', sa.Column('estimated_delivery_minutes', sa.Integer(), server_default='30', nullable=True))


def downgrade() -> None:
    op.drop_column('orders', 'estimated_delivery_minutes')
    op.drop_column('orders', 'order_type')
    op.drop_column('orders', 'delivery_location')
