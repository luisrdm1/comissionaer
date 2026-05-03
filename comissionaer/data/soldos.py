"""Tabela de soldos FAB vigente em 2026 — Lei nº 13.954/2019, Anexo I; Lei nº 15.167/2025."""

from decimal import Decimal

from comissionaer.models import Posto

SOLDOS: dict[Posto, Decimal] = {
    # Oficiais
    Posto.SEGUNDO_TENENTE: Decimal("8179.00"),
    Posto.PRIMEIRO_TENENTE: Decimal("9004.00"),
    Posto.CAPITAO: Decimal("9976.00"),
    Posto.MAJOR: Decimal("12108.00"),
    Posto.TENENTE_CORONEL: Decimal("12285.00"),
    Posto.CORONEL: Decimal("12505.00"),
    Posto.BRIGADEIRO: Decimal("13639.00"),
    Posto.MAJOR_BRIGADEIRO: Decimal("14100.00"),
    Posto.TENENTE_BRIGADEIRO: Decimal("14711.00"),
    # Praças — Lei 15.167/2025 (reajuste 4,5% em jan/2026)
    Posto.SUBOFICIAL: Decimal("6724.00"),
    Posto.PRIMEIRO_SARGENTO: Decimal("5976.00"),
    Posto.SEGUNDO_SARGENTO: Decimal("5199.00"),
    Posto.TERCEIRO_SARGENTO: Decimal("4169.00"),
    Posto.CABO: Decimal("2863.00"),
    Posto.SOLDADO_1_CLASSE: Decimal("1924.00"),
    Posto.SOLDADO_2_CLASSE: Decimal("1924.00"),
}
