"""Geração de relatório PDF com fpdf2."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from fpdf import FPDF

from comissionaer.models import BaseRemuneratoria, Calculo, ResultadoMissao

_FONT_PATH = Path("C:/Windows/Fonts/arial.ttf")
_FONT_BOLD_PATH = Path("C:/Windows/Fonts/arialbd.ttf")

# Larguras das colunas da tabela de missões (mm) — paisagem A4 = 267 mm úteis
_COL_W = (10.0, 82.0, 20.0, 20.0, 14.0, 32.0, 32.0)


def _brl(value: Decimal) -> str:
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


class _RelatorioPDF(FPDF):
    def __init__(self) -> None:
        super().__init__(orientation="L", unit="mm", format="A4")
        self.set_auto_page_break(auto=True, margin=15)
        self.set_margins(15, 15, 15)
        self._arial = _FONT_PATH.exists() and _FONT_BOLD_PATH.exists()
        if self._arial:
            self.add_font("Arial", fname=str(_FONT_PATH))
            self.add_font("Arial", style="B", fname=str(_FONT_BOLD_PATH))

    # ------------------------------------------------------------------
    # Helpers internos
    # ------------------------------------------------------------------

    def apply_font(self, size: int, bold: bool = False) -> None:
        if self._arial:
            self.set_font("Arial", style="B" if bold else "", size=size)
        else:
            self.set_font("Helvetica", style="B" if bold else "", size=size)

    def section_header(self, title: str) -> None:
        self.apply_font(11, bold=True)
        self.set_fill_color(220, 230, 242)
        self.cell(0, 7, f"  {title}", fill=True)
        self.ln(8)

    def kv_row(self, label: str, value: str, label_w: float = 80.0) -> None:
        self.apply_font(10, bold=True)
        self.cell(label_w, 6, label)
        self.apply_font(10)
        self.cell(0, 6, value)
        self.ln(6)

    def kv_row_right(self, label: str, value: str, label_w: float = 120.0) -> None:
        self.apply_font(10)
        self.cell(label_w, 6, label)
        self.cell(0, 6, value, align="R")
        self.ln(6)

    def separator(self) -> None:
        self.set_draw_color(100, 100, 100)
        self.line(self.get_x(), self.get_y(), self.get_x() + 267, self.get_y())
        self.ln(2)

    # ------------------------------------------------------------------
    # Seções
    # ------------------------------------------------------------------

    def render_identificacao(self, calculo: Calculo) -> None:
        self.apply_font(13, bold=True)
        self.cell(0, 8, "ANÁLISE DE ECONOMICIDADE — COMISSIONAMENTO", align="C")
        self.ln(10)

        self.kv_row("Militar:", f"{calculo.militar.posto.value}  {calculo.militar.nome}")

        if calculo.mudanca_encerramento:
            self.kv_row("Habilitação (abertura):", calculo.militar.habilitacao.value)
            hab_enc = calculo.militar.habilitacao_encerramento or calculo.militar.habilitacao
            posto_enc = calculo.militar.posto_encerramento
            enc_value = hab_enc.value
            if posto_enc is not None:
                enc_value = f"{enc_value}  [{posto_enc.value}]"
            self.kv_row("Habilitação (encerramento):", enc_value)
        else:
            self.kv_row("Habilitação:", calculo.militar.habilitacao.value)

        dep = "Sim" if calculo.militar.dependentes.value else "Não"
        fator_total = calculo.fator_ida + calculo.fator_volta
        self.apply_font(10, bold=True)
        self.cell(80, 6, "Dependentes:")
        self.apply_font(10)
        self.cell(60, 6, dep)
        self.apply_font(10, bold=True)
        self.cell(50, 6, "Fator ajuda de custo:")
        self.apply_font(10)
        self.cell(0, 6, f"{fator_total}× ({calculo.fator_ida}× ida + {calculo.fator_volta}× volta)")
        self.ln(10)

    def render_base(self, base: BaseRemuneratoria, fator: Decimal, label: str = "") -> None:
        header = "BASE REMUNERATÓRIA" + (f" — {label}" if label else "")
        self.section_header(header)

        linhas: list[tuple[str, Decimal]] = [
            ("Soldo militar da ativa", base.soldo),
            ("Adicional de habilitação", base.adicional_habilitacao),
            ("Adicional militar", base.adicional_militar),
            ("Adicional de disponibilidade militar", base.adicional_disponibilidade),
        ]
        if base.adicional_compensacao_organica > 0:
            linhas.append(
                ("Adicional de compensação orgânica", base.adicional_compensacao_organica)
            )

        for descr, valor in linhas:
            self.kv_row_right(descr, _brl(valor))

        self.separator()

        self.apply_font(10, bold=True)
        self.cell(120, 6, "Total da base remuneratória")
        self.cell(0, 6, _brl(base.total), align="R")
        self.ln(6)

        self.apply_font(10, bold=True)
        self.cell(120, 6, f"Ajuda de custo ({fator}× base)")
        self.cell(0, 6, _brl(base.total * fator), align="R")
        self.ln(10)

    def render_missoes(self, missoes: list[ResultadoMissao]) -> None:
        self.section_header("MISSÕES")

        headers = ["Nº", "Descrição / OM", "Início", "Término", "Dias", "Diárias", "Total"]
        self.set_fill_color(180, 200, 225)
        for i, h in enumerate(headers):
            self.apply_font(8, bold=True)
            self.cell(_COL_W[i], 6, h, border=1, fill=True, align="C")
        self.ln()

        for idx, rm in enumerate(missoes, start=1):
            descr = f"{rm.missao.descricao[:55]}  [{rm.missao.om_destino}]"
            row: list[tuple[float, str, str]] = [
                (_COL_W[0], str(idx), "C"),
                (_COL_W[1], descr, "L"),
                (_COL_W[2], rm.missao.data_inicio.strftime("%d/%m/%Y"), "C"),
                (_COL_W[3], rm.missao.data_termino.strftime("%d/%m/%Y"), "C"),
                (_COL_W[4], str(rm.dias), "C"),
                (_COL_W[5], _brl(rm.total_diarias), "R"),
                (_COL_W[6], _brl(rm.total), "R"),
            ]
            fill = idx % 2 == 0
            self.set_fill_color(240, 245, 252)
            for w, txt, align in row:
                self.apply_font(8)
                self.cell(w, 5.5, txt, border=1, fill=fill, align=align)  # type: ignore[arg-type]
            self.ln()

        self.ln(4)

    def render_resumo(self, calculo: Calculo) -> None:
        self.section_header("RESUMO")

        linhas: list[tuple[str, str]] = [
            ("Total de dias fora de sede", f"{calculo.total_dias} dias"),
            ("Total de diárias", _brl(calculo.total_diarias)),
            ("Total de deslocamentos", _brl(calculo.total_deslocamentos)),
            ("Total de custo em missões", _brl(calculo.total_missoes)),
        ]
        if calculo.mudanca_encerramento:
            linhas += [
                (
                    f"  Ajuda de custo ida ({calculo.fator_ida}× base abertura)",
                    _brl(calculo.base.total * calculo.fator_ida),
                ),
                (
                    f"  Ajuda de custo volta ({calculo.fator_volta}× base encerramento)",
                    _brl(calculo.base_encerramento.total * calculo.fator_volta),
                ),
            ]
        linhas.append(("Ajuda de custo (comparativo)", _brl(calculo.total_ajuda_custo)))

        for descr, valor in linhas:
            self.kv_row_right(descr, valor)

        self.ln(2)
        self.separator()

        econ = calculo.economicidade
        cor: tuple[int, int, int] = (0, 120, 0) if econ >= 0 else (180, 0, 0)
        self.set_text_color(*cor)
        self.apply_font(12, bold=True)
        label = (
            "ECONOMICIDADE (comissionamento justificado)"
            if econ >= 0
            else "DÉFICIT (missões insuficientes)"
        )
        self.cell(160, 8, label)
        self.cell(0, 8, _brl(abs(econ)), align="R")
        self.set_text_color(0, 0, 0)
        self.ln(10)

        if calculo.total_ajuda_custo > 0:
            pct = calculo.total_missoes / calculo.total_ajuda_custo * 100
            self.apply_font(9)
            self.set_text_color(80, 80, 80)
            if econ >= 0:
                self.cell(
                    0,
                    6,
                    f"O custo das missões ({pct:.1f}% da ajuda de custo) supera o comparativo, "
                    f"justificando o comissionamento.",
                )
            else:
                self.cell(
                    0,
                    6,
                    f"O custo das missões representa apenas {pct:.1f}% da ajuda de custo. "
                    f"São necessárias mais missões para justificar o comissionamento.",
                )
            self.set_text_color(0, 0, 0)

    # ------------------------------------------------------------------
    # Cabeçalho e rodapé de página
    # ------------------------------------------------------------------

    def header(self) -> None:
        self.apply_font(9)
        self.set_text_color(130, 130, 130)
        self.cell(0, 6, "COMANDO DA AERONÁUTICA — Análise de Comissionamento", align="C")
        self.ln(8)
        self.set_text_color(0, 0, 0)

    def footer(self) -> None:
        self.set_y(-12)
        self.apply_font(8)
        self.set_text_color(140, 140, 140)
        self.cell(0, 6, f"Página {self.page_no()} / {{nb}}", align="C")
        self.set_text_color(0, 0, 0)


def gerar_pdf(calculo: Calculo, caminho: str) -> None:
    pdf = _RelatorioPDF()
    pdf.alias_nb_pages()
    pdf.add_page()

    pdf.render_identificacao(calculo)
    if calculo.mudanca_encerramento:
        pdf.render_base(calculo.base, calculo.fator_ida, "ABERTURA")
        pdf.render_base(calculo.base_encerramento, calculo.fator_volta, "ENCERRAMENTO")
    else:
        pdf.render_base(calculo.base, calculo.fator_ida + calculo.fator_volta)
    pdf.render_missoes(calculo.missoes)
    pdf.render_resumo(calculo)

    pdf.output(caminho)
