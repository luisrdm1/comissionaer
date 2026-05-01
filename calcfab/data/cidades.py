"""Categorias de diária militar e valor de deslocamento."""

from decimal import Decimal

from calcfab.models import CategoriaDiaria

VALORES_DIARIA: dict[CategoriaDiaria, Decimal] = {
    CategoriaDiaria.ESPECIAL: Decimal("425.00"),
    CategoriaDiaria.CAPITAL: Decimal("380.00"),
    CategoriaDiaria.PADRAO: Decimal("335.00"),
}

DESLOCAMENTO = Decimal("95.00")


def valor_diaria(categoria: CategoriaDiaria) -> Decimal:
    return VALORES_DIARIA[categoria]
