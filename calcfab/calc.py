"""Lógica de cálculo de comissionamento."""

from decimal import Decimal

from calcfab.data.adicionais import ADICIONAL_DISPONIBILIDADE, ADICIONAL_MILITAR
from calcfab.data.cidades import DESLOCAMENTO, valor_diaria
from calcfab.data.habilitacoes import PERCENTUAIS
from calcfab.data.soldos import SOLDOS_2026
from calcfab.models import (
    BaseRemuneratoria,
    Calculo,
    Dependentes,
    DuracaoComissionamento,
    Militar,
    Missao,
    ResultadoMissao,
)

# Fator total (ida + volta) por (duração, dependentes) — MP 2.215-10/2001 + Lei 13.954/2019
_FATOR_AJUDA: dict[tuple[DuracaoComissionamento, Dependentes], Decimal] = {
    (DuracaoComissionamento.CURTO, Dependentes.SIM): Decimal("2"),    # 1 + 1
    (DuracaoComissionamento.CURTO, Dependentes.NAO): Decimal("1"),    # 0.5 + 0.5
    (DuracaoComissionamento.LONGO, Dependentes.SIM): Decimal("3"),    # 2 + 1
    (DuracaoComissionamento.LONGO, Dependentes.NAO): Decimal("1.5"),  # 1 + 0.5
}


def calcular_base(militar: Militar) -> BaseRemuneratoria:
    soldo = SOLDOS_2026[militar.posto]
    adic_hab = soldo * PERCENTUAIS[militar.habilitacao]
    adic_mil = soldo * ADICIONAL_MILITAR[militar.posto]
    adic_disp = soldo * ADICIONAL_DISPONIBILIDADE[militar.posto]
    adic_comp = soldo * militar.pct_compensacao_organica
    return BaseRemuneratoria(
        soldo=soldo,
        adicional_habilitacao=adic_hab,
        adicional_militar=adic_mil,
        adicional_disponibilidade=adic_disp,
        adicional_compensacao_organica=adic_comp,
    )


def calcular_missao(missao: Missao) -> ResultadoMissao:
    dias = (missao.data_termino - missao.data_inicio).days + 1
    diaria = valor_diaria(missao.categoria_diaria)
    total_diarias = (Decimal(dias) - Decimal("0.5")) * diaria
    total_deslocamento = DESLOCAMENTO * missao.num_deslocamentos
    return ResultadoMissao(
        missao=missao,
        dias=dias,
        valor_diaria_unitario=diaria,
        total_diarias=total_diarias,
        total_deslocamento=total_deslocamento,
    )


def calcular(militar: Militar, missoes: list[Missao]) -> Calculo:
    base = calcular_base(militar)
    fator = _FATOR_AJUDA[(militar.duracao, militar.dependentes)]
    return Calculo(
        militar=militar,
        base=base,
        fator_ajuda_custo=fator,
        missoes=[calcular_missao(m) for m in missoes],
    )
