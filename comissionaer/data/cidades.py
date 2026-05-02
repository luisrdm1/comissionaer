"""Categorias de diária militar e valor de deslocamento — Decreto 4.307/2002, Anexo III."""

from decimal import Decimal

from comissionaer.models import TIER_DIARIA, CategoriaDiaria, Posto, TierDiaria

VALORES_DIARIA: dict[tuple[TierDiaria, CategoriaDiaria], Decimal] = {
    (TierDiaria.OFICIAL_GENERAL, CategoriaDiaria.ESPECIAL): Decimal("600.00"),
    (TierDiaria.OFICIAL_GENERAL, CategoriaDiaria.CAPITAL): Decimal("515.00"),
    (TierDiaria.OFICIAL_GENERAL, CategoriaDiaria.PADRAO): Decimal("455.00"),
    (TierDiaria.OFICIAL_SUPERIOR, CategoriaDiaria.ESPECIAL): Decimal("510.00"),
    (TierDiaria.OFICIAL_SUPERIOR, CategoriaDiaria.CAPITAL): Decimal("450.00"),
    (TierDiaria.OFICIAL_SUPERIOR, CategoriaDiaria.PADRAO): Decimal("395.00"),
    (TierDiaria.OFICIAL_SUBALTERNO, CategoriaDiaria.ESPECIAL): Decimal("425.00"),
    (TierDiaria.OFICIAL_SUBALTERNO, CategoriaDiaria.CAPITAL): Decimal("380.00"),
    (TierDiaria.OFICIAL_SUBALTERNO, CategoriaDiaria.PADRAO): Decimal("335.00"),
    (TierDiaria.PRACA_GRADUADA, CategoriaDiaria.ESPECIAL): Decimal("425.00"),
    (TierDiaria.PRACA_GRADUADA, CategoriaDiaria.CAPITAL): Decimal("380.00"),
    (TierDiaria.PRACA_GRADUADA, CategoriaDiaria.PADRAO): Decimal("335.00"),
    (TierDiaria.PRACA, CategoriaDiaria.ESPECIAL): Decimal("355.00"),
    (TierDiaria.PRACA, CategoriaDiaria.CAPITAL): Decimal("315.00"),
    (TierDiaria.PRACA, CategoriaDiaria.PADRAO): Decimal("280.00"),
}

DESLOCAMENTO = Decimal("95.00")


def valor_diaria(posto: Posto, categoria: CategoriaDiaria) -> Decimal:
    return VALORES_DIARIA[(TIER_DIARIA[posto], categoria)]
