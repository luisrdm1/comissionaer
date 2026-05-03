from datetime import date
from decimal import Decimal

from comissionaer.calc import calcular, calcular_missao, fatores_ajuda_custo
from comissionaer.models import (
    CategoriaDiaria,
    Dependentes,
    FaixaAjudaCusto,
    Habilitacao,
    Militar,
    Missao,
    Posto,
)


def _militar(
    dependentes: Dependentes = Dependentes.SIM,
    habilitacao_enc: Habilitacao | None = Habilitacao.ALTOS_II,
) -> Militar:
    return Militar(
        nome="Militar Teste",
        posto=Posto.CAPITAO,
        habilitacao=Habilitacao.APERFEICOAMENTO,
        dependentes=dependentes,
        pct_compensacao_organica=Decimal("0.20"),
        habilitacao_encerramento=habilitacao_enc,
    )


def _missao(
    inicio: date,
    termino: date,
    categoria: CategoriaDiaria = CategoriaDiaria.PADRAO,
    deslocamentos: int = 1,
) -> Missao:
    return Missao(
        descricao="Missao de teste",
        om_destino="TEST",
        cidade="Cidade",
        uf="UF",
        categoria_diaria=categoria,
        data_inicio=inicio,
        data_termino=termino,
        num_deslocamentos=deslocamentos,
    )


# ---------------------------------------------------------------------------
# Regra fundamental: ajuda de custo usa SOMA DE DIAS, não span do calendário
# ---------------------------------------------------------------------------


def test_36_dias_de_missao_nao_e_acima_de_3_meses_mesmo_com_gap_entre_missoes() -> None:
    """Caso real: maio (20d) + agosto (16d) = 36d. Span = 3,5 meses, mas faixa deve ser 1×+1×."""
    missoes = [
        _missao(date(2026, 5, 10), date(2026, 5, 29)),  # 20 dias
        _missao(date(2026, 8, 13), date(2026, 8, 28)),  # 16 dias
    ]

    calculo = calcular(_militar(), missoes)

    assert calculo.total_dias == 36
    # span = maio a agosto > 3 meses, mas classificação usa 36 dias → 1ª faixa
    assert calculo.fator_ida == Decimal("1")
    assert calculo.fator_volta == Decimal("1")


def test_20_dias_em_dois_meses_distantes_ainda_e_primeira_faixa() -> None:
    """Jan (10d) + ago (10d) = 20 dias. Span = 7 meses. Deve ser 1ª faixa, não 2ª."""
    missoes = [
        _missao(date(2026, 1, 1), date(2026, 1, 10)),
        _missao(date(2026, 8, 1), date(2026, 8, 10)),
    ]

    calculo = calcular(_militar(), missoes)

    assert calculo.total_dias == 20
    assert calculo.fator_ida == Decimal("1")
    assert calculo.fator_volta == Decimal("1")


def test_91_dias_totais_e_faixa_acima_de_3_meses() -> None:
    """Exatamente 91 dias de missão → 2ª faixa."""
    missoes = [_missao(date(2026, 1, 1), date(2026, 4, 1))]  # 91 dias

    calculo = calcular(_militar(), missoes)

    assert calculo.total_dias == 91
    assert calculo.fator_ida == Decimal("2")
    assert calculo.fator_volta == Decimal("1")


def test_90_dias_totais_ainda_e_primeira_faixa() -> None:
    """Exatamente 90 dias de missão → ainda 1ª faixa (≤ 90)."""
    missoes = [_missao(date(2026, 1, 1), date(2026, 3, 31))]  # 90 dias

    calculo = calcular(_militar(), missoes)

    assert calculo.total_dias == 90
    assert calculo.fator_ida == Decimal("1")
    assert calculo.fator_volta == Decimal("1")


# ---------------------------------------------------------------------------
# Todas as combinações de faixa × dependentes
# ---------------------------------------------------------------------------


def test_faixa_ate_15_dias_com_dependentes_fator_zero() -> None:
    fator_ida, fator_volta = fatores_ajuda_custo(
        FaixaAjudaCusto.SEM_DESLIGAMENTO_ATE_15_DIAS, Dependentes.SIM
    )

    assert fator_ida == Decimal("0")
    assert fator_volta == Decimal("0")


def test_faixa_ate_15_dias_sem_dependentes_fator_zero() -> None:
    fator_ida, fator_volta = fatores_ajuda_custo(
        FaixaAjudaCusto.SEM_DESLIGAMENTO_ATE_15_DIAS, Dependentes.NAO
    )

    assert fator_ida == Decimal("0")
    assert fator_volta == Decimal("0")


def test_faixa_15_a_3_meses_com_dependentes_fator_1_mais_1() -> None:
    fator_ida, fator_volta = fatores_ajuda_custo(
        FaixaAjudaCusto.SEM_DESLIGAMENTO_15_DIAS_A_3_MESES, Dependentes.SIM
    )

    assert fator_ida == Decimal("1")
    assert fator_volta == Decimal("1")


def test_faixa_15_a_3_meses_sem_dependentes_fator_meio_mais_meio() -> None:
    fator_ida, fator_volta = fatores_ajuda_custo(
        FaixaAjudaCusto.SEM_DESLIGAMENTO_15_DIAS_A_3_MESES, Dependentes.NAO
    )

    assert fator_ida == Decimal("0.5")
    assert fator_volta == Decimal("0.5")


def test_faixa_acima_3_meses_com_dependentes_fator_2_mais_1() -> None:
    fator_ida, fator_volta = fatores_ajuda_custo(
        FaixaAjudaCusto.SEM_DESLIGAMENTO_ACIMA_3_MESES, Dependentes.SIM
    )

    assert fator_ida == Decimal("2")
    assert fator_volta == Decimal("1")


def test_faixa_acima_3_meses_sem_dependentes_fator_1_mais_meio() -> None:
    fator_ida, fator_volta = fatores_ajuda_custo(
        FaixaAjudaCusto.SEM_DESLIGAMENTO_ACIMA_3_MESES, Dependentes.NAO
    )

    assert fator_ida == Decimal("1")
    assert fator_volta == Decimal("0.5")


# ---------------------------------------------------------------------------
# calcular — integração completa com cada faixa
# ---------------------------------------------------------------------------


def test_calcular_ate_15_dias_ajuda_custo_zero() -> None:
    missao = _missao(date(2026, 1, 1), date(2026, 1, 15))  # 15 dias

    calculo = calcular(_militar(), [missao])

    assert calculo.total_dias == 15
    assert calculo.fator_ida == Decimal("0")
    assert calculo.fator_volta == Decimal("0")
    assert calculo.total_ajuda_custo == Decimal("0")


def test_calcular_usa_base_abertura_e_encerramento_separados() -> None:
    missao = _missao(date(2026, 1, 1), date(2026, 12, 31))

    calculo = calcular(_militar(), [missao])

    assert calculo.base.total == Decimal("19852.24")
    assert calculo.base_encerramento.total == Decimal("22146.72")
    assert calculo.fator_ida == Decimal("2")
    assert calculo.fator_volta == Decimal("1")
    assert calculo.total_ajuda_custo == Decimal("61851.20")
    assert calculo.militar.data_inicio_comissionamento == date(2026, 1, 1)
    assert calculo.militar.data_termino_comissionamento == date(2026, 12, 31)


# ---------------------------------------------------------------------------
# calcular_missao — diárias e deslocamentos
# ---------------------------------------------------------------------------


def test_diaria_usa_meia_diaria_a_menos_e_deslocamento_separado() -> None:
    missao = _missao(date(2026, 5, 10), date(2026, 5, 30), deslocamentos=2)

    resultado = calcular_missao(missao, Posto.CAPITAO)

    assert resultado.dias == 21
    assert resultado.valor_diaria_unitario == Decimal("335.00")
    assert resultado.total_diarias == Decimal("6867.500")
    assert resultado.total_deslocamento == Decimal("190.00")
    assert resultado.total == Decimal("7057.500")


def test_totais_de_missoes_somam_diarias_e_deslocamentos() -> None:
    missoes = [
        _missao(date(2027, 3, 1), date(2027, 3, 17)),
        _missao(date(2027, 4, 26), date(2027, 5, 9), CategoriaDiaria.CAPITAL),
        _missao(date(2026, 5, 10), date(2026, 5, 30)),
        _missao(date(2027, 8, 1), date(2027, 8, 7), CategoriaDiaria.CAPITAL),
        _missao(date(2027, 8, 13), date(2027, 8, 29), CategoriaDiaria.CAPITAL),
        _missao(date(2027, 10, 3), date(2027, 10, 23), CategoriaDiaria.CAPITAL),
    ]

    calculo = calcular(_militar(), missoes)

    assert calculo.total_dias == 97
    assert calculo.total_diarias == Decimal("34055.000")
    assert calculo.total_deslocamentos == Decimal("570.00")
    assert calculo.total_missoes == Decimal("34625.000")
