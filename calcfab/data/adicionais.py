"""Adicionais por posto — MP nº 2.215-10/2001 e Lei nº 13.954/2019."""

from decimal import Decimal

from calcfab.models import Posto

# Adicional Militar — percentual sobre o soldo
ADICIONAL_MILITAR: dict[Posto, Decimal] = {
    Posto.SEGUNDO_TENENTE: Decimal("0.19"),
    Posto.PRIMEIRO_TENENTE: Decimal("0.19"),
    Posto.CAPITAO: Decimal("0.22"),
    Posto.MAJOR: Decimal("0.25"),
    Posto.TENENTE_CORONEL: Decimal("0.25"),
    Posto.CORONEL: Decimal("0.25"),
    Posto.BRIGADEIRO: Decimal("0.28"),
    Posto.MAJOR_BRIGADEIRO: Decimal("0.28"),
    Posto.TENENTE_BRIGADEIRO: Decimal("0.28"),
}

# Adicional de Disponibilidade Militar — percentual sobre o soldo
ADICIONAL_DISPONIBILIDADE: dict[Posto, Decimal] = {
    Posto.SEGUNDO_TENENTE: Decimal("0.05"),
    Posto.PRIMEIRO_TENENTE: Decimal("0.06"),
    Posto.CAPITAO: Decimal("0.12"),
    Posto.MAJOR: Decimal("0.20"),
    Posto.TENENTE_CORONEL: Decimal("0.26"),
    Posto.CORONEL: Decimal("0.32"),
    Posto.BRIGADEIRO: Decimal("0.35"),
    Posto.MAJOR_BRIGADEIRO: Decimal("0.38"),
    Posto.TENENTE_BRIGADEIRO: Decimal("0.41"),
}
