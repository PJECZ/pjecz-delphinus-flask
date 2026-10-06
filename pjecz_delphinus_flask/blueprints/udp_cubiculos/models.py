"""
UDP Cubículos, modelos
"""

from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pjecz_delphinus_flask.config.extensions import database
from pjecz_delphinus_flask.lib.universal_mixin import UniversalMixin

if TYPE_CHECKING:
    from pjecz_delphinus_flask.blueprints.udp_atenciones.models import UdpAtencion


class UdpCubiculo(database.Model, UniversalMixin):
    """UdpCubiculo"""

    # Nombre de la tabla
    __tablename__ = "udp_cubiculos"
    __table_args__ = (
        CheckConstraint("estado IN ('disponible', 'ocupado')", name="ck_udp_cubiculos_estado"),
        Index("uq_udp_cubiculos_nombre", "nombre", unique=True),
    )

    # Clave primaria
    id: Mapped[int] = mapped_column(primary_key=True)

    # Columnas
    nombre: Mapped[str] = mapped_column(String(64))
    estado: Mapped[str] = mapped_column(String(16), default="disponible", server_default="disponible")

    # Hijos
    udp_atenciones: Mapped[list["UdpAtencion"]] = relationship(back_populates="cubiculo")

    def __repr__(self):
        """Representación"""
        return f"<UdpCubiculo {self.nombre}>"
