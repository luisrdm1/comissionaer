from datetime import date
from decimal import Decimal
from pathlib import Path

import pdfplumber

from comissionaer.calc import calcular
from comissionaer.models import (
    CategoriaDiaria,
    Dependentes,
    DuracaoComissionamento,
    Habilitacao,
    Militar,
    Missao,
    Posto,
)
from comissionaer.report import gerar_pdf


def _missao_teste(
    descricao: str,
    om: str,
    categoria: CategoriaDiaria,
    inicio: date,
    termino: date,
) -> Missao:
    return Missao(descricao, om, "Cidade", "UF", categoria, inicio, termino)


def test_pdf_com_abertura_e_encerramento_cabe_em_uma_pagina(tmp_path: Path) -> None:
    militar = Militar(
        nome="Militar Teste",
        posto=Posto.CAPITAO,
        habilitacao=Habilitacao.APERFEICOAMENTO,
        dependentes=Dependentes.SIM,
        pct_compensacao_organica=Decimal("0.20"),
        duracao=DuracaoComissionamento.LONGO,
        habilitacao_encerramento=Habilitacao.ALTOS_II,
    )
    missoes = [
        _missao_teste(
            "Missao Teste 1", "TST1", CategoriaDiaria.PADRAO, date(2027, 3, 1), date(2027, 3, 17)
        ),
        _missao_teste(
            "Missao Teste 2", "TST2", CategoriaDiaria.CAPITAL, date(2027, 4, 26), date(2027, 5, 9)
        ),
        _missao_teste(
            "Missao Teste 3", "TST3", CategoriaDiaria.PADRAO, date(2026, 5, 10), date(2026, 5, 30)
        ),
        _missao_teste(
            "Missao Teste 4", "TST4", CategoriaDiaria.CAPITAL, date(2027, 8, 1), date(2027, 8, 7)
        ),
        _missao_teste(
            "Missao Teste 5", "TST5", CategoriaDiaria.CAPITAL, date(2027, 8, 13), date(2027, 8, 29)
        ),
        _missao_teste(
            "Missao Teste 6",
            "TST6",
            CategoriaDiaria.CAPITAL,
            date(2027, 10, 3),
            date(2027, 10, 23),
        ),
    ]
    caminho_pdf: Path = tmp_path / "relatorio.pdf"

    gerar_pdf(calcular(militar, missoes), str(caminho_pdf))

    with pdfplumber.open(str(caminho_pdf)) as pdf:
        assert len(pdf.pages) == 1
        text = pdf.pages[0].extract_text() or ""

    assert "MINISTÉRIO DA DEFESA" in text
    assert "Assunto: Solicitação de Abertura de Comissionamento" in text
    assert "DADOS DO MILITAR" in text
    assert "ANÁLISE DE ECONOMICIDADE" not in text
    assert "Aperfeiçoamento (45%) (45%)" not in text
    assert "COMPARATIVO FINANCEIRO" in text
    assert "DÉFICIT" not in text
    assert "TOTAIS" in text
    assert "10 cotas (20%)" in text
    assert "Missão e local de realização do serviço" in text
    assert "TST1" in text
    assert "DIRETOR_NOME_PRIVADO" in text
    assert "Diretor do IAOp" in text
