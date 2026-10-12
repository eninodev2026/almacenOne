"""factura unica solo entre compras activas

Revision ID: dc1eeecf7e7f
Revises: 2477487ed413
Create Date: 2026-10-05 11:24:51.278171

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'dc1eeecf7e7f'
down_revision: Union[str, Sequence[str], None] = '2477487ed413'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint(
        "compra_proveedor_id_numero_factura_key", "compra", type_="unique"
    )
    op.create_index(
        "uq_compra_proveedor_factura_activa",
        "compra",
        ["proveedor_id", "numero_factura"],
        unique=True,
        postgresql_where=sa.text("estado = 'ACTIVO'"),
    )


def downgrade() -> None:
    op.drop_index("uq_compra_proveedor_factura_activa", table_name="compra")
    op.create_unique_constraint(
        "compra_proveedor_id_numero_factura_key",
        "compra",
        ["proveedor_id", "numero_factura"],
    )