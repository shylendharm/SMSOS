"""Add geo fields to businesses table

Revision ID: 003_add_business_geo_fields
Revises: 002_add_delivery_fields
Create Date: 2026-08-01
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '003_add_business_geo_fields'
down_revision: Union[str, None] = '002_add_delivery_fields'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    op.add_column('businesses', sa.Column('latitude', sa.Float(), nullable=True))
    op.add_column('businesses', sa.Column('longitude', sa.Float(), nullable=True))
    op.add_column('businesses', sa.Column('default_prep_time_minutes', sa.Integer(), server_default='15', nullable=False))
    op.add_column('businesses', sa.Column('delivery_radius_km', sa.Float(), server_default='10.0', nullable=False))


def downgrade() -> None:
    op.drop_column('businesses', 'delivery_radius_km')
    op.drop_column('businesses', 'default_prep_time_minutes')
    op.drop_column('businesses', 'longitude')
    op.drop_column('businesses', 'latitude')
