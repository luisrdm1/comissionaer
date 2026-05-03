"""Lógica de cálculo de comissionamento."""

from decimal import Decimal

from comissionaer.data.adicionais import ADICIONAL_DISPONIBILIDADE, ADICIONAL_MILITAR
from comissionaer.data.cidades import DESLOCAMENTO, valor_diaria
from comissionaer.data.habilitacoes import PERCENTUAIS
from comissionaer.data.soldos import SOLDOS
from comissionaer.models import (
    BaseRemuneratoria,
    Calculo,
    Dependentes,
    FaixaAjudaCusto,
    Habilitacao,
    Militar,
    Missao,
    Posto,
    ResultadoMissao,
    classificar_ajuda_custo_por_dias,
    dias_missoes,
    periodo_missoes,
)

_FATORES_AJUDA_CUSTO: dict[tuple[FaixaAjudaCusto, Dependentes], tuple[Decimal, Decimal]] = {
    (FaixaAjudaCusto.SEM_DESLIGAMENTO_ATE_15_DIAS, Dependentes.SIM): (
        Decimal("0"),
        Decimal("0"),
    ),
    (FaixaAjudaCusto.SEM_DESLIGAMENTO_ATE_15_DIAS, Dependentes.NAO): (
        Decimal("0"),
        Decimal("0"),
    ),
    (FaixaAjudaCusto.SEM_DESLIGAMENTO_15_DIAS_A_3_MESES, Dependentes.SIM): (
        Decimal("1"),
        Decimal("1"),
    ),
    (FaixaAjudaCusto.SEM_DESLIGAMENTO_15_DIAS_A_3_MESES, Dependentes.NAO): (
        Decimal("0.5"),
        Decimal("0.5"),
    ),
    (FaixaAjudaCusto.SEM_DESLIGAMENTO_ACIMA_3_MESES, Dependentes.SIM): (
        Decimal("2"),
        Decimal("1"),
    ),
    (FaixaAjudaCusto.SEM_DESLIGAMENTO_ACIMA_3_MESES, Dependentes.NAO): (
        Decimal("1"),
        Decimal("0.5"),
    ),
}


def _calcular_base(posto: Posto, habilitacao: Habilitacao, pct_comp: Decimal) -> BaseRemuneratoria:
    soldo = SOLDOS[posto]
    adic_hab = soldo * PERCENTUAIS[habilitacao]
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


def calcular_base(militar: Militar) -> BaseRemuneratoria:
    return _calcular_base(
        militar.posto,
        militar.habilitacao,
        militar.pct_compensacao_organica,
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
    return _calcular_base(posto, hab, pct_comp)


def calcular_missao(missao: Missao, posto: Posto) -> ResultadoMissao:
    dias = (missao.data_termino - missao.data_inicio).days + 1
    diaria = valor_diaria(posto, missao.categoria_diaria)
    total_diarias = (Decimal(dias) - Decimal("0.5")) * diaria
    total_deslocamento = DESLOCAMENTO * missao.num_deslocamentos
    return ResultadoMissao(
        missao=missao,
        dias=dias,
        valor_diaria_unitario=diaria,
        total_diarias=total_diarias,
        total_deslocamento=total_deslocamento,
    )


def fatores_ajuda_custo(
    faixa: FaixaAjudaCusto,
    dependentes: Dependentes,
) -> tuple[Decimal, Decimal]:
    fatores = _FATORES_AJUDA_CUSTO.get((faixa, dependentes))
    if fatores is None:
        raise ValueError(f"Sem enquadramento automático de ajuda de custo para: {faixa.value}.")
    return fatores


def calcular(militar: Militar, missoes: list[Missao]) -> Calculo:
    inicio, termino = periodo_missoes(missoes)
    faixa = classificar_ajuda_custo_por_dias(dias_missoes(missoes))
    militar.data_inicio_comissionamento = inicio
    militar.data_termino_comissionamento = termino

    base = calcular_base(militar)
    base_enc = calcular_base_encerramento(militar)
    fator_ida, fator_volta = fatores_ajuda_custo(faixa, militar.dependentes)
    return Calculo(
        militar=militar,
        base=base,
        base_encerramento=base_enc,
        fator_ida=fator_ida,
        fator_volta=fator_volta,
        missoes=[calcular_missao(m, militar.posto) for m in missoes],
    )
