"""Tabela de soldos FAB 2026 — Lei nº 13.954/2019."""

from decimal import Decimal

from comissionaer.models import Posto

SOLDOS_2026: dict[Posto, Decimal] = {
    Posto.SEGUNDO_TENENTE: Decimal("8179.00"),
    Posto.PRIMEIRO_TENENTE: Decimal("9004.00"),
    Posto.CAPITAO: Decimal("9976.00"),
    Posto.MAJOR: Decimal("12108.00"),
    Posto.TENENTE_CORONEL: Decimal("12285.00"),
    Posto.CORONEL: Decimal("12505.00"),
    Posto.BRIGADEIRO: Decimal("13639.00"),
    Posto.MAJOR_BRIGADEIRO: Decimal("14100.00"),
    Posto.TENENTE_BRIGADEIRO: Decimal("14711.00"),
}
