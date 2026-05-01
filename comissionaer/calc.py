"""Lógica de cálculo de comissionamento."""

from decimal import Decimal

from comissionaer.data.adicionais import ADICIONAL_DISPONIBILIDADE, ADICIONAL_MILITAR
from comissionaer.data.cidades import DESLOCAMENTO, valor_diaria
from comissionaer.data.habilitacoes import PERCENTUAIS
from comissionaer.data.soldos import SOLDOS_2026
from comissionaer.models import (
    BaseRemuneratoria,
    Calculo,
    Dependentes,
    DuracaoComissionamento,
    Militar,
    Missao,
    ResultadoMissao,
)

# Fator de ida (base abertura) por (duração, dependentes) — MP 2.215-10/2001 + Lei 13.954/2019
_FATOR_IDA: dict[tuple[DuracaoComissionamento, Dependentes], Decimal] = {
    (DuracaoComissionamento.CURTO, Dependentes.SIM): Decimal("1"),
    (DuracaoComissionamento.CURTO, Dependentes.NAO): Decimal("0.5"),
    (DuracaoComissionamento.LONGO, Dependentes.SIM): Decimal("2"),
    (DuracaoComissionamento.LONGO, Dependentes.NAO): Decimal("1"),
}

# Fator de volta (base encerramento) por (duração, dependentes)
_FATOR_VOLTA: dict[tuple[DuracaoComissionamento, Dependentes], Decimal] = {
    (DuracaoComissionamento.CURTO, Dependentes.SIM): Decimal("1"),
    (DuracaoComissionamento.CURTO, Dependentes.NAO): Decimal("0.5"),
    (DuracaoComissionamento.LONGO, Dependentes.SIM): Decimal("1"),
    (DuracaoComissionamento.LONGO, Dependentes.NAO): Decimal("0.5"),
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


def calcular_base_encerramento(militar: Militar) -> BaseRemuneratoria:
    """Base na data de encerramento, usando posto/hab/comp_org de encerramento se informados."""
    posto = militar.posto_encerramento or militar.posto
    hab = militar.habilitacao_encerramento or militar.habilitacao
    pct_comp = (
        militar.pct_compensacao_organica_encerramento
        if militar.pct_compensacao_organica_encerramento is not None
        else militar.pct_compensacao_organica
    )
    soldo = SOLDOS_2026[posto]
    adic_hab = soldo * PERCENTUAIS[hab]
    adic_mil = soldo * ADICIONAL_MILITAR[posto]
    adic_disp = soldo * ADICIONAL_DISPONIBILIDADE[posto]
    adic_comp = soldo * pct_comp
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
    base_enc = calcular_base_encerramento(militar)
    fator_ida = _FATOR_IDA[(militar.duracao, militar.dependentes)]
    fator_volta = _FATOR_VOLTA[(militar.duracao, militar.dependentes)]
    return Calculo(
        militar=militar,
        base=base,
        base_encerramento=base_enc,
        fator_ida=fator_ida,
        fator_volta=fator_volta,
        missoes=[calcular_missao(m) for m in missoes],
    )
