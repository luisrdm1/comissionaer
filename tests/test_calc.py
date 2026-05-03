from datetime import date
from decimal import Decimal

from comissionaer.calc import calcular, calcular_missao
from comissionaer.models import (
    CategoriaDiaria,
    Dependentes,
    Habilitacao,
    Militar,
    Missao,
    Posto,
)


def _militar_teste() -> Militar:
    return Militar(
        nome="Militar Teste",
        posto=Posto.CAPITAO,
        habilitacao=Habilitacao.APERFEICOAMENTO,
        dependentes=Dependentes.SIM,
        pct_compensacao_organica=Decimal("0.20"),
        habilitacao_encerramento=Habilitacao.ALTOS_II,
    )


def _missao_teste(
    inicio: date,
    termino: date,
    categoria: CategoriaDiaria,
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


def test_ajuda_de_custo_usa_abertura_e_encerramento_separados() -> None:
    missao = _missao_teste(date(2026, 1, 1), date(2026, 12, 31), CategoriaDiaria.PADRAO)

    calculo = calcular(_militar_teste(), [missao])

    assert calculo.base.total == Decimal("19852.24")
    assert calculo.base_encerramento.total == Decimal("22146.72")
    assert calculo.fator_ida == Decimal("2")
    assert calculo.fator_volta == Decimal("1")
    assert calculo.total_ajuda_custo == Decimal("61851.20")
    assert calculo.militar.data_inicio_comissionamento == date(2026, 1, 1)
    assert calculo.militar.data_termino_comissionamento == date(2026, 12, 31)


def test_ajuda_de_custo_usa_periodo_continuo_das_missoes_nao_soma_de_dias() -> None:
    missoes = [
        _missao_teste(date(2026, 1, 1), date(2026, 1, 10), CategoriaDiaria.PADRAO),
        _missao_teste(date(2026, 5, 1), date(2026, 5, 10), CategoriaDiaria.PADRAO),
    ]

    calculo = calcular(_militar_teste(), missoes)

    assert calculo.total_dias == 20
    assert calculo.militar.data_inicio_comissionamento == date(2026, 1, 1)
    assert calculo.militar.data_termino_comissionamento == date(2026, 5, 10)
    assert calculo.fator_ida == Decimal("2")
    assert calculo.fator_volta == Decimal("1")


def test_ajuda_de_custo_ate_15_dias_sem_desligamento_fica_zerada() -> None:
    missao = _missao_teste(date(2026, 1, 1), date(2026, 1, 15), CategoriaDiaria.PADRAO)

    calculo = calcular(_militar_teste(), [missao])

    assert calculo.fator_ida == Decimal("0")
    assert calculo.fator_volta == Decimal("0")
    assert calculo.total_ajuda_custo == Decimal("0.00")


def test_diaria_usa_meia_diaria_a_menos_e_deslocamento_separado() -> None:
    missao = _missao_teste(
        date(2026, 5, 10),
        date(2026, 5, 30),
        CategoriaDiaria.PADRAO,
        deslocamentos=2,
    )

    resultado = calcular_missao(missao, Posto.CAPITAO)

    assert resultado.dias == 21
    assert resultado.valor_diaria_unitario == Decimal("335.00")
    assert resultado.total_diarias == Decimal("6867.500")
    assert resultado.total_deslocamento == Decimal("190.00")
    assert resultado.total == Decimal("7057.500")


def test_totais_de_missoes_somam_diarias_e_deslocamentos() -> None:
    missoes = [
        _missao_teste(date(2027, 3, 1), date(2027, 3, 17), CategoriaDiaria.PADRAO),
        _missao_teste(date(2027, 4, 26), date(2027, 5, 9), CategoriaDiaria.CAPITAL),
        _missao_teste(date(2026, 5, 10), date(2026, 5, 30), CategoriaDiaria.PADRAO),
        _missao_teste(date(2027, 8, 1), date(2027, 8, 7), CategoriaDiaria.CAPITAL),
        _missao_teste(date(2027, 8, 13), date(2027, 8, 29), CategoriaDiaria.CAPITAL),
        _missao_teste(date(2027, 10, 3), date(2027, 10, 23), CategoriaDiaria.CAPITAL),
    ]

    calculo = calcular(_militar_teste(), missoes)

    assert calculo.total_dias == 97
    assert calculo.total_diarias == Decimal("34055.000")
    assert calculo.total_deslocamentos == Decimal("570.00")
    assert calculo.total_missoes == Decimal("34625.000")
