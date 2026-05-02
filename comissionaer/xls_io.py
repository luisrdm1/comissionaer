"""Geração e atualização de planilha XLS no formato IAOp."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import xlrd
import xlwt

from comissionaer.models import Calculo, Posto

_DIRECTOR_NOME = "ALEXANDRE DIAS IRIGON Cel Av"
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

_POSTO_XLS: dict[Posto, str] = {
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
    """Fallback: posto_abbrev + último sobrenome do nome completo."""
    m = calculo.militar
    ultimo = m.nome.strip().split()[-1].capitalize()
    return f"{_POSTO_ABA.get(m.posto, m.posto.name)} {ultimo}"


def _date_serial(d: date) -> int:
    return (d - date(1899, 12, 30)).days


def _escrever_aba(ws: xlwt.Worksheet, calculo: Calculo) -> None:
    col_widths = {0: 5, 1: 10, 2: 42, 3: 10, 4: 12, 5: 12,
                  6: 8, 7: 10, 8: 58, 9: 8, 10: 22, 11: 22, 12: 10}
    for col, chars in col_widths.items():
        ws.col(col).width = 256 * chars

    ws.write(0, 0, "COMANDO  DE PREPARO")
    ws.write(1, 0, "INSTITUTO DE APLICAÇÕES OPERACIONAIS")
    ws.write(2, 0, "Solicitação de Abertura de Comissionamento")

    for col, header in [
        (0, "Nº"), (1, "POSTO/GRAD"), (2, "NOME COMPLETO"), (3, "POSSUI DEP"),
        (4, "MÓDULOS"), (6, "Nº DE DIAS"), (7, "TOTAL DE DIAS"),
        (8, "MISSÃO E LOCAL DE REALIZAÇÃO DO SERVIÇO"),
        (9, "QNT AJ CUSTO"), (10, "VLR AJUDA CUSTO IDA E VOLTA (R$)"),
        (11, "VLR TOTAL DIÁRIAS (R$)"), (12, "OM ADIDO"),
    ]:
        ws.write(4, col, header)
    ws.write(5, 3, "(SIM/NÃO)")
    ws.write(5, 4, "INÍCIO")
    ws.write(5, 5, "TÉRMINO")

    m = calculo.militar
    missoes_sorted = sorted(calculo.missoes, key=lambda r: r.missao.data_inicio)
    dep = "SIM" if m.dependentes.value else "NÃO"
    fator = calculo.fator_ida + calculo.fator_volta
    fator_val = int(fator) if fator == int(fator) else float(fator)

    date_fmt = xlwt.easyxf(num_format_str="DD/MM/YYYY")

    for i, rm in enumerate(missoes_sorted):
        row = 6 + i
        miss = rm.missao
        descr = f"{miss.descricao} - {miss.cidade}/{miss.uf}"

        ws.write(row, 4, _date_serial(miss.data_inicio), date_fmt)
        ws.write(row, 5, _date_serial(miss.data_termino), date_fmt)
        ws.write(row, 6, rm.dias)
        ws.write(row, 8, descr)
        ws.write(row, 11, float(rm.total_diarias))
        ws.write(row, 12, miss.om_destino)

        if i == 0:
            ws.write(row, 0, 1)
            ws.write(row, 1, _POSTO_XLS.get(m.posto, m.posto.name))
            ws.write(row, 2, m.nome.upper())
            ws.write(row, 3, dep)
            ws.write(row, 7, calculo.total_dias)
            ws.write(row, 9, fator_val)
            ws.write(row, 10, float(calculo.total_ajuda_custo))

    n = len(missoes_sorted)
    total_desloc_count = sum(rm.missao.num_deslocamentos for rm in missoes_sorted)

    row_desloc = 6 + n
    ws.write(row_desloc, 0, f"Acréscimo de deslocamento (R$ 95,00):  {total_desloc_count}")
    ws.write(row_desloc, 11, float(calculo.total_deslocamentos))

    row_comp = row_desloc + 1
    ws.write(row_comp, 0, "COMPARATIVO ENTRE AJUDA DE CUSTO X DIÁRIA:")
    ws.write(row_comp, 10, float(calculo.total_ajuda_custo))
    ws.write(row_comp, 11, float(calculo.total_missoes))

    ws.write(row_comp + 4, 8, _DIRECTOR_NOME)
    ws.write(row_comp + 5, 8, _DIRECTOR_CARGO)


def atualizar_xls(caminho_xls: str, calculos_por_aba: dict[str, Calculo]) -> None:
    """Adiciona ou substitui abas no XLS preservando as demais na ordem original."""
    caminho = Path(caminho_xls)
    wb_novo = xlwt.Workbook(encoding="utf-8")

    ordem: list[str] = []
    rb: xlrd.Book | None = None

    if caminho.exists():
        rb = xlrd.open_workbook(str(caminho))
        ordem = list(rb.sheet_names())

    for nome in calculos_por_aba:
        if nome not in ordem:
            ordem.append(nome)

    date_fmt = xlwt.easyxf(num_format_str="DD/MM/YYYY")

    for nome in ordem:
        ws = wb_novo.add_sheet(nome)
        if nome in calculos_por_aba:
            _escrever_aba(ws, calculos_por_aba[nome])
        elif rb is not None:
            sh = rb.sheet_by_name(nome)
            for r in range(sh.nrows):
                for c in range(sh.ncols):
                    cell = sh.cell(r, c)
                    if cell.ctype == xlrd.XL_CELL_DATE:
                        ws.write(r, c, cell.value, date_fmt)
                    elif cell.ctype not in (xlrd.XL_CELL_EMPTY, xlrd.XL_CELL_ERROR):
                        ws.write(r, c, cell.value)

    wb_novo.save(str(caminho))
