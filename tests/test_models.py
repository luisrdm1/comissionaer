from datetime import date

import pytest

from comissionaer.models import (
    CategoriaDiaria,
    FaixaAjudaCusto,
    Missao,
    Posto,
    classificar_ajuda_custo,
    classificar_ajuda_custo_por_dias,
    dias_missoes,
    dias_periodo,
    periodo_missoes,
    proximo_posto,
)

# ---------------------------------------------------------------------------
# classificar_ajuda_custo_por_dias — função canônica do sistema
# ---------------------------------------------------------------------------


def test_ate_15_dias_nao_gera_ajuda_custo() -> None:
    assert classificar_ajuda_custo_por_dias(1) == FaixaAjudaCusto.SEM_DESLIGAMENTO_ATE_15_DIAS
    assert classificar_ajuda_custo_por_dias(15) == FaixaAjudaCusto.SEM_DESLIGAMENTO_ATE_15_DIAS


def test_fronteira_15_16_dias() -> None:
    assert classificar_ajuda_custo_por_dias(15) == FaixaAjudaCusto.SEM_DESLIGAMENTO_ATE_15_DIAS
    assert (
        classificar_ajuda_custo_por_dias(16) == FaixaAjudaCusto.SEM_DESLIGAMENTO_15_DIAS_A_3_MESES
    )


def test_90_dias_ainda_e_primeira_faixa() -> None:
    assert (
        classificar_ajuda_custo_por_dias(90) == FaixaAjudaCusto.SEM_DESLIGAMENTO_15_DIAS_A_3_MESES
    )


def test_fronteira_90_91_dias() -> None:
    assert (
        classificar_ajuda_custo_por_dias(90) == FaixaAjudaCusto.SEM_DESLIGAMENTO_15_DIAS_A_3_MESES
    )
    assert classificar_ajuda_custo_por_dias(91) == FaixaAjudaCusto.SEM_DESLIGAMENTO_ACIMA_3_MESES


def test_acima_de_90_dias_segunda_faixa() -> None:
    assert classificar_ajuda_custo_por_dias(91) == FaixaAjudaCusto.SEM_DESLIGAMENTO_ACIMA_3_MESES
    assert classificar_ajuda_custo_por_dias(365) == FaixaAjudaCusto.SEM_DESLIGAMENTO_ACIMA_3_MESES


def test_36_dias_e_primeira_faixa_nao_acima_de_3_meses() -> None:
    """Caso concreto reportado: maio+agosto = 36 dias de missão não é > 3 meses."""
    assert (
        classificar_ajuda_custo_por_dias(36) == FaixaAjudaCusto.SEM_DESLIGAMENTO_15_DIAS_A_3_MESES
    )


# ---------------------------------------------------------------------------
# classificar_ajuda_custo (por período calendário) — mantida para referência
# ---------------------------------------------------------------------------


def test_calendario_ate_15_dias() -> None:
    faixa = classificar_ajuda_custo(date(2026, 1, 1), date(2026, 1, 15))

    assert dias_periodo(date(2026, 1, 1), date(2026, 1, 15)) == 15
    assert faixa == FaixaAjudaCusto.SEM_DESLIGAMENTO_ATE_15_DIAS


def test_calendario_tres_meses_exatos_primeira_faixa() -> None:
    faixa = classificar_ajuda_custo(date(2026, 1, 1), date(2026, 3, 31))

    assert faixa == FaixaAjudaCusto.SEM_DESLIGAMENTO_15_DIAS_A_3_MESES


def test_calendario_acima_tres_meses_segunda_faixa() -> None:
    faixa = classificar_ajuda_custo(date(2026, 1, 1), date(2026, 4, 1))

    assert faixa == FaixaAjudaCusto.SEM_DESLIGAMENTO_ACIMA_3_MESES


# ---------------------------------------------------------------------------
# dias_missoes — soma de dias, não span do calendário
# ---------------------------------------------------------------------------


def _missao(inicio: date, termino: date) -> Missao:
    return Missao(
        descricao="Missão teste",
        om_destino="TST",
        cidade="Cidade",
        uf="UF",
        categoria_diaria=CategoriaDiaria.PADRAO,
        data_inicio=inicio,
        data_termino=termino,
    )


def test_dias_missoes_soma_cada_missao_individualmente() -> None:
    missoes = [
        _missao(date(2026, 5, 10), date(2026, 5, 29)),  # 20 dias
        _missao(date(2026, 8, 13), date(2026, 8, 28)),  # 16 dias
    ]

    assert dias_missoes(missoes) == 36


def test_dias_missoes_ignora_lacuna_entre_missoes() -> None:
    """Missões em jan e ago: soma = 20, span calendário = 7+ meses."""
    missoes = [
        _missao(date(2026, 1, 1), date(2026, 1, 10)),  # 10 dias
        _missao(date(2026, 8, 1), date(2026, 8, 10)),  # 10 dias
    ]

    assert dias_missoes(missoes) == 20


def test_periodo_missoes_retorna_extremidades_nao_soma() -> None:
    missoes = [
        _missao(date(2026, 5, 10), date(2026, 5, 30)),
        _missao(date(2027, 3, 1), date(2027, 3, 17)),
    ]

    inicio, termino = periodo_missoes(missoes)

    assert inicio == date(2026, 5, 10)
    assert termino == date(2027, 3, 17)
    assert dias_periodo(inicio, termino) == 312  # span muito maior que a soma de dias


# ---------------------------------------------------------------------------
# Promoções
# ---------------------------------------------------------------------------


def test_promocao_fica_restrita_ao_proximo_posto() -> None:
    assert proximo_posto(Posto.CAPITAO) == Posto.MAJOR
    assert proximo_posto(Posto.CORONEL) == Posto.BRIGADEIRO
    assert proximo_posto(Posto.TENENTE_BRIGADEIRO) is None


# ---------------------------------------------------------------------------
# Erros esperados
# ---------------------------------------------------------------------------


def test_classificar_ajuda_custo_rejeita_termino_antes_do_inicio() -> None:
    with pytest.raises(ValueError):
        classificar_ajuda_custo(date(2026, 5, 10), date(2026, 5, 9))


def test_periodo_missoes_rejeita_termino_antes_do_inicio() -> None:
    with pytest.raises(ValueError):
        periodo_missoes([_missao(date(2026, 5, 10), date(2026, 5, 9))])
