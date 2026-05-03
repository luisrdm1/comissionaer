"""Geração e atualização de planilha ODS no formato IAOp."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from odfdo import Document, Table

from comissionaer.models import Calculo, Posto

_DIRECTOR_NOME = "DIRETOR_NOME_PRIVADO"
_DIRECTOR_CARGO = "Diretor do IAOp"

_POSTO_ABA: dict[Posto, str] = {
    Posto.SEGUNDO_TENENTE: "2T",
    Posto.PRIMEIRO_TENENTE: "1T",
    Posto.CAPITAO: "Cap",
    Posto.MAJOR: "Maj",
    Posto.TENENTE_CORONEL: "TC",
    Posto.CORONEL: "Cel",
    Posto.BRIGADEIRO: "Brig",
    Posto.MAJOR_BRIGADEIRO: "Maj Brig",
    Posto.TENENTE_BRIGADEIRO: "Ten Brig",
}

_POSTO_ODS: dict[Posto, str] = {
    Posto.SEGUNDO_TENENTE: "TEN",
    Posto.PRIMEIRO_TENENTE: "TEN",
    Posto.CAPITAO: "CAP",
    Posto.MAJOR: "MAJ",
    Posto.TENENTE_CORONEL: "TC",
    Posto.CORONEL: "CEL",
    Posto.BRIGADEIRO: "BRIG",
    Posto.MAJOR_BRIGADEIRO: "MAJ BRIG",
    Posto.TENENTE_BRIGADEIRO: "TEN BRIG",
}


def derivar_nome_aba(calculo: Calculo) -> str:
    m = calculo.militar
    ultimo = m.nome.strip().split()[-1].capitalize()
    return f"{_POSTO_ABA.get(m.posto, m.posto.name)} {ultimo}"


def _sv(table: Table, col: int, row: int, value: str | int | float | date) -> None:
    # odfdo annotates coord as bare `tuple` (no subscript), which pyright strict
    # treats as tuple[Unknown, ...] — one ignore here covers all call sites.
    table.set_value((col, row), value)  # pyright: ignore[reportUnknownMemberType]


def _build_table(nome: str, calculo: Calculo) -> Table:
    table = Table(nome)
    m = calculo.militar
    missoes_sorted = calculo.missoes
    dep = "SIM" if m.dependentes.value else "NÃO"
    fator = calculo.fator_ida + calculo.fator_volta
    fator_val: int | float = int(fator) if fator == int(fator) else float(fator)

    _sv(table, 0, 0, "COMANDO  DE PREPARO")
    _sv(table, 0, 1, "INSTITUTO DE APLICAÇÕES OPERACIONAIS")
    _sv(table, 0, 2, "Solicitação de Abertura de Comissionamento")

    _sv(table, 0, 4, "Nº")
    _sv(table, 1, 4, "POSTO/GRAD")
    _sv(table, 2, 4, "NOME COMPLETO")
    _sv(table, 3, 4, "POSSUI DEP")
    _sv(table, 4, 4, "MÓDULOS")
    _sv(table, 6, 4, "Nº DE DIAS")
    _sv(table, 7, 4, "TOTAL DE DIAS")
    _sv(table, 8, 4, "MISSÃO E LOCAL DE REALIZAÇÃO DO SERVIÇO")
    _sv(table, 9, 4, "QNT AJ CUSTO")
    _sv(table, 10, 4, "VLR AJUDA CUSTO IDA E VOLTA (R$)")
    _sv(table, 11, 4, "VLR TOTAL DIÁRIAS (R$)")
    _sv(table, 12, 4, "OM ADIDO")

    _sv(table, 3, 5, "(SIM/NÃO)")
    _sv(table, 4, 5, "INÍCIO")
    _sv(table, 5, 5, "TÉRMINO")

    for i, rm in enumerate(missoes_sorted):
        row = 6 + i
        miss = rm.missao
        _sv(table, 4, row, miss.data_inicio)
        _sv(table, 5, row, miss.data_termino)
        _sv(table, 6, row, rm.dias)
        _sv(table, 8, row, f"{miss.descricao} - {miss.cidade}/{miss.uf}")
        _sv(table, 11, row, float(rm.total_diarias))
        _sv(table, 12, row, miss.om_destino)
        if i == 0:
            _sv(table, 0, row, 1)
            _sv(table, 1, row, _POSTO_ODS.get(m.posto, m.posto.name))
            _sv(table, 2, row, m.nome.upper())
            _sv(table, 3, row, dep)
            _sv(table, 7, row, calculo.total_dias)
            _sv(table, 9, row, fator_val)
            _sv(table, 10, row, float(calculo.total_ajuda_custo))

    n = len(missoes_sorted)
    total_desloc_count = sum(rm.missao.num_deslocamentos for rm in missoes_sorted)

    row_desloc = 6 + n
    _sv(table, 0, row_desloc, f"Acréscimo de deslocamento (R$ 95,00):  {total_desloc_count}")
    _sv(table, 11, row_desloc, float(calculo.total_deslocamentos))

    row_comp = row_desloc + 1
    _sv(table, 0, row_comp, "COMPARATIVO ENTRE AJUDA DE CUSTO X DIÁRIA:")
    _sv(table, 10, row_comp, float(calculo.total_ajuda_custo))
    _sv(table, 11, row_comp, float(calculo.total_missoes))

    _sv(table, 8, row_comp + 4, _DIRECTOR_NOME)
    _sv(table, 8, row_comp + 5, _DIRECTOR_CARGO)

    return table


def atualizar_ods(caminho_ods: str, calculos_por_aba: dict[str, Calculo]) -> None:
    """Adiciona ou substitui abas no ODS preservando as demais na ordem original."""
    caminho = Path(caminho_ods)

    if caminho.exists():
        doc = Document(str(caminho))
        tabelas_originais = list(doc.body.get_tables())
    else:
        doc = Document("spreadsheet")
        doc.body.clear()
        tabelas_originais = []

    tabelas_por_nome: dict[str, Table] = {
        t.name: t for t in tabelas_originais if t.name is not None
    }
    nomes_originais = list(tabelas_por_nome)

    ordem: list[str] = list(nomes_originais)
    for nome in calculos_por_aba:
        if nome not in ordem:
            ordem.append(nome)

    for t in tabelas_originais:
        t.delete()

    for nome in ordem:
        if nome in calculos_por_aba:
            doc.body.append(_build_table(nome, calculos_por_aba[nome]))
        else:
            doc.body.append(tabelas_por_nome[nome])

    doc.save(str(caminho))
