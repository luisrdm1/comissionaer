from datetime import date

from comissionaer.models import (
    CategoriaDiaria,
    FaixaAjudaCusto,
    Missao,
    Posto,
    classificar_ajuda_custo,
    dias_periodo,
    periodo_missoes,
    proximo_posto,
)


def test_comissao_sem_desligamento_ate_15_dias_nao_enquadra_ajuda_custo() -> None:
    faixa = classificar_ajuda_custo(date(2026, 1, 1), date(2026, 1, 15))

    assert dias_periodo(date(2026, 1, 1), date(2026, 1, 15)) == 15
    assert faixa == FaixaAjudaCusto.SEM_DESLIGAMENTO_ATE_15_DIAS


def test_comissao_sem_desligamento_16_dias_enquadra_primeira_faixa() -> None:
    faixa = classificar_ajuda_custo(date(2026, 1, 1), date(2026, 1, 16))

    assert faixa == FaixaAjudaCusto.SEM_DESLIGAMENTO_15_DIAS_A_3_MESES


def test_comissao_sem_desligamento_tres_meses_inclusivos_fica_na_primeira_faixa() -> None:
    faixa = classificar_ajuda_custo(date(2026, 1, 1), date(2026, 3, 31))

    assert faixa == FaixaAjudaCusto.SEM_DESLIGAMENTO_15_DIAS_A_3_MESES


def test_comissao_sem_desligamento_acima_de_tres_meses_fica_na_segunda_faixa() -> None:
    faixa = classificar_ajuda_custo(date(2026, 1, 1), date(2026, 4, 1))

    assert faixa == FaixaAjudaCusto.SEM_DESLIGAMENTO_ACIMA_3_MESES


def test_comissao_sem_desligamento_doze_meses_inclusivos_fica_na_segunda_faixa() -> None:
    faixa = classificar_ajuda_custo(date(2026, 1, 1), date(2026, 12, 31))

    assert faixa == FaixaAjudaCusto.SEM_DESLIGAMENTO_ACIMA_3_MESES


def test_comissao_sem_desligamento_acima_de_doze_meses_permanece_na_faixa_acima_de_tres() -> None:
    faixa = classificar_ajuda_custo(date(2026, 1, 1), date(2027, 1, 1))

    assert faixa == FaixaAjudaCusto.SEM_DESLIGAMENTO_ACIMA_3_MESES


def test_periodo_do_comissionamento_e_derivado_das_extremidades_das_missoes() -> None:
    missoes = [
        Missao(
            descricao="Missao 1",
            om_destino="TST1",
            cidade="Cidade",
            uf="UF",
            categoria_diaria=CategoriaDiaria.PADRAO,
            data_inicio=date(2026, 5, 10),
            data_termino=date(2026, 5, 30),
        ),
        Missao(
            descricao="Missao 2",
            om_destino="TST2",
            cidade="Cidade",
            uf="UF",
            categoria_diaria=CategoriaDiaria.PADRAO,
            data_inicio=date(2027, 3, 1),
            data_termino=date(2027, 3, 17),
        ),
    ]

    inicio, termino = periodo_missoes(missoes)

    assert inicio == date(2026, 5, 10)
    assert termino == date(2027, 3, 17)
    assert dias_periodo(inicio, termino) == 312


def test_promocao_fica_restrita_ao_proximo_posto() -> None:
    assert proximo_posto(Posto.CAPITAO) == Posto.MAJOR
    assert proximo_posto(Posto.CORONEL) == Posto.BRIGADEIRO
    assert proximo_posto(Posto.TENENTE_BRIGADEIRO) is None
