"""Adicional de habilitação FAB — Lei nº 13.954/2019, Anexo III."""

from decimal import Decimal

from calcfab.models import Habilitacao

PERCENTUAIS: dict[Habilitacao, Decimal] = {
    Habilitacao.FORMACAO: Decimal("0.12"),
    Habilitacao.ESPECIALIZACAO: Decimal("0.27"),
    Habilitacao.APERFEICOAMENTO: Decimal("0.45"),
    Habilitacao.ALTOS_II: Decimal("0.68"),
    Habilitacao.ALTOS_I: Decimal("0.73"),
}
