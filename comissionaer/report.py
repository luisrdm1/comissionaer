"""Geração de relatório PDF com fpdf2."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from fpdf import FPDF

from comissionaer.data.habilitacoes import PERCENTUAIS
from comissionaer.models import BaseRemuneratoria, Calculo, ResultadoMissao

_FONT_PATH = Path("C:/Windows/Fonts/arial.ttf")
_FONT_BOLD_PATH = Path("C:/Windows/Fonts/arialbd.ttf")

# Larguras das colunas da tabela de missões (mm) — paisagem A4 = 281 mm úteis
# Colunas fixas (Nº, OM, Início, Término, Dias, Diárias, Desloc., Total); descrição pega o restante.
_PAGE_W = 281.0
_COL_FIXED = (8.0, 18.0, 22.0, 22.0, 12.0, 32.0, 28.0, 34.0)
_COL_DESCR = _PAGE_W - sum(_COL_FIXED)  # 105 mm
_COL_W = (_COL_FIXED[0], _COL_DESCR, *_COL_FIXED[1:])


def _brl(value: Decimal) -> str:
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _percent(value: Decimal) -> str:
    pct = value * 100
    return f"{pct:.0f}%" if pct == pct.to_integral() else f"{pct:.1f}%"


def _cotas(value: Decimal) -> str:
    cotas = value / Decimal("0.02")
    cotas_text = f"{cotas:.0f}" if cotas == cotas.to_integral() else f"{cotas:.1f}"
    return f"{cotas_text} cotas ({_percent(value)})"


class _RelatorioPDF(FPDF):
    def __init__(self) -> None:
        super().__init__(orientation="L", unit="mm", format="A4")
        self.set_auto_page_break(auto=False, margin=8)
        self.set_margins(8, 8, 8)
        self._arial = _FONT_PATH.exists() and _FONT_BOLD_PATH.exists()
        if self._arial:
            self.add_font("Arial", fname=str(_FONT_PATH))
            self.add_font("Arial", style="B", fname=str(_FONT_BOLD_PATH))

    # ------------------------------------------------------------------
    # Helpers internos
    # ------------------------------------------------------------------

    def apply_font(self, size: int, bold: bool = False, underline: bool = False) -> None:
        style = ("B" if bold else "") + ("U" if underline else "")
        if self._arial:
            self.set_font("Arial", style=style, size=size)
        else:
            self.set_font("Helvetica", style=style, size=size)

    def section_header(self, title: str) -> None:
        self.apply_font(9, bold=True)
        self.set_fill_color(220, 230, 242)
        self.cell(0, 5, f"  {title}", fill=True)
        self.ln(5.5)

    def kv_row(self, label: str, value: str, label_w: float = 80.0) -> None:
        self.apply_font(9, bold=True)
        self.cell(label_w, 5, label)
        self.apply_font(9)
        self.cell(0, 5, value)
        self.ln(5)

    def kv_row_right(self, label: str, value: str, label_w: float = 120.0) -> None:
        self.apply_font(9)
        self.cell(label_w, 5, label)
        self.cell(0, 5, value, align="R")
        self.ln(5)

    def info_pair(self, label: str, value: str, label_w: float, value_w: float) -> None:
        self.apply_font(8, bold=True)
        self.cell(label_w, 4.6, label)
        self.apply_font(8)
        self.cell(value_w, 4.6, value)

    def separator(self) -> None:
        self.set_draw_color(100, 100, 100)
        self.line(self.get_x(), self.get_y(), self.get_x() + _PAGE_W, self.get_y())
        self.ln(1.5)

    # ------------------------------------------------------------------
    # Seções
    # ------------------------------------------------------------------

    def _habilitacao_curta(self, calculo: Calculo, encerramento: bool = False) -> str:
        habilitacao = calculo.militar.habilitacao
        if encerramento:
            habilitacao = calculo.militar.habilitacao_encerramento or habilitacao
        nome = habilitacao.value.split("—", maxsplit=1)[0].strip()
        if "%" in nome:
            return nome
        return f"{nome} ({_percent(PERCENTUAIS[habilitacao])})"

    def _pct_comp_encerramento(self, calculo: Calculo) -> Decimal:
        return (
            calculo.militar.pct_compensacao_organica_encerramento
            if calculo.militar.pct_compensacao_organica_encerramento is not None
            else calculo.militar.pct_compensacao_organica
        )

    def render_identificacao(self, calculo: Calculo) -> None:
        self.section_header("DADOS DO MILITAR")

        dep = "Sim" if calculo.militar.dependentes.value else "Não"
        comp_abertura = _cotas(calculo.militar.pct_compensacao_organica)
        comp_encerramento = _cotas(self._pct_comp_encerramento(calculo))

        line_h = 4.8
        rows = [
            (
                ("Militar:", f"{calculo.militar.posto.value} {calculo.militar.nome}", 21, 160),
                ("Dependentes:", dep, 25, 75),
            ),
            (
                ("Hab. abertura:", self._habilitacao_curta(calculo), 29, 111),
                (
                    "Hab. encerramento:",
                    self._habilitacao_curta(calculo, encerramento=True),
                    36,
                    105,
                ),
            ),
            (
                ("Comp. org. abertura:", comp_abertura, 42, 98),
                ("Comp. org. encerramento:", comp_encerramento, 49, 92),
            ),
        ]
        for row in rows:
            for label, value, label_w, value_w in row:
                self.apply_font(8, bold=True)
                self.cell(label_w, line_h, label, border=1)
                self.apply_font(8)
                self.cell(value_w, line_h, value, border=1)
            self.ln(line_h)
        self.ln(1.5)

    def _base_linhas(self, base: BaseRemuneratoria) -> list[tuple[str, Decimal]]:
        linhas: list[tuple[str, Decimal]] = [
            ("Soldo militar da ativa", base.soldo),
            ("Adicional de habilitação", base.adicional_habilitacao),
            ("Adicional militar", base.adicional_militar),
            ("Adicional de disponibilidade militar", base.adicional_disponibilidade),
        ]
        if base.adicional_compensacao_organica > 0:
            linhas.append(
                (
                    "Adicional de compensação orgânica (cotas de voo)",
                    base.adicional_compensacao_organica,
                )
            )
        return linhas

    def render_base(self, base: BaseRemuneratoria, fator: Decimal, label: str = "") -> None:
        header = "BASE REMUNERATÓRIA" + (f" — {label}" if label else "")
        self.section_header(header)

        line_h = 4.6
        descr_w = 195.0
        valor_w = _PAGE_W - descr_w
        self.set_fill_color(180, 200, 225)
        self.apply_font(8, bold=True)
        self.cell(descr_w, line_h, "Rubrica", border=1, fill=True, align="C")
        self.cell(valor_w, line_h, "Valor", border=1, fill=True, align="C")
        self.ln()

        for descr, valor in self._base_linhas(base):
            self.apply_font(8)
            self.cell(descr_w, line_h, descr, border=1)
            self.cell(valor_w, line_h, _brl(valor), border=1, align="R")
            self.ln()

        self.apply_font(8, bold=True)
        self.cell(descr_w, line_h, "Total da base remuneratória", border=1)
        self.cell(valor_w, line_h, _brl(base.total), border=1, align="R")
        self.ln()

        self.cell(descr_w, line_h, f"Ajuda de custo ({fator}× base)", border=1)
        self.cell(valor_w, line_h, _brl(base.total * fator), border=1, align="R")
        self.ln(6)

    def render_bases(self, calculo: Calculo) -> None:
        if not calculo.mudanca_encerramento:
            self.render_base(calculo.base, calculo.fator_ida + calculo.fator_volta)
            return

        self.section_header("BASE REMUNERATÓRIA — ABERTURA X ENCERRAMENTO")
        line_h = 4.6
        descr_w = 117.0
        abertura_w = 82.0
        encerramento_w = _PAGE_W - descr_w - abertura_w
        self.set_fill_color(180, 200, 225)
        self.apply_font(8, bold=True)
        self.cell(descr_w, line_h, "Rubrica", border=1, fill=True, align="C")
        self.cell(
            abertura_w,
            line_h,
            f"Abertura ({calculo.fator_ida}x)",
            border=1,
            fill=True,
            align="C",
        )
        self.cell(
            encerramento_w,
            line_h,
            f"Encerramento ({calculo.fator_volta}x)",
            border=1,
            fill=True,
            align="C",
        )
        self.ln()

        linhas_abertura = self._base_linhas(calculo.base)
        linhas_encerramento = self._base_linhas(calculo.base_encerramento)
        for (descr, valor_abertura), (_, valor_encerramento) in zip(
            linhas_abertura, linhas_encerramento, strict=True
        ):
            self.apply_font(8)
            self.cell(descr_w, line_h, descr, border=1)
            self.cell(abertura_w, line_h, _brl(valor_abertura), border=1, align="R")
            self.cell(encerramento_w, line_h, _brl(valor_encerramento), border=1, align="R")
            self.ln()

        self.apply_font(8, bold=True)
        self.cell(descr_w, line_h, "Compensação orgânica (cotas de voo)", border=1)
        self.cell(
            abertura_w,
            line_h,
            _cotas(calculo.militar.pct_compensacao_organica),
            border=1,
            align="R",
        )
        self.cell(
            encerramento_w,
            line_h,
            _cotas(self._pct_comp_encerramento(calculo)),
            border=1,
            align="R",
        )
        self.ln()

        self.apply_font(8, bold=True)
        self.cell(descr_w, line_h, "Total da base remuneratória", border=1)
        self.cell(abertura_w, line_h, _brl(calculo.base.total), border=1, align="R")
        self.cell(
            encerramento_w,
            line_h,
            _brl(calculo.base_encerramento.total),
            border=1,
            align="R",
        )
        self.ln()

        ajuda_ida = calculo.base.total * calculo.fator_ida
        ajuda_volta = calculo.base_encerramento.total * calculo.fator_volta
        self.cell(descr_w, line_h, "Ajuda de custo", border=1)
        self.cell(
            abertura_w,
            line_h,
            f"{calculo.fator_ida}x = {_brl(ajuda_ida)}",
            border=1,
            align="R",
        )
        self.cell(
            encerramento_w,
            line_h,
            f"{calculo.fator_volta}x = {_brl(ajuda_volta)}",
            border=1,
            align="R",
        )
        self.ln()

        self.ln(1.5)

    def _fit_text(self, text: str, width: float) -> str:
        """Trunca o texto para caber em `width` mm na fonte atual."""
        if self.get_string_width(text) <= width:
            return text
        while text and self.get_string_width(text + "…") > width:
            text = text[:-1]
        return text + "…"

    def render_missoes(self, missoes: list[ResultadoMissao]) -> None:
        self.section_header("MISSÕES")

        line_h = 4.7
        headers = [
            "Nº",
            "Missão e local de realização do serviço",
            "OM",
            "Início",
            "Término",
            "Dias",
            "Diárias",
            "Desloc.",
            "Total",
        ]
        self.set_fill_color(180, 200, 225)
        for i, h in enumerate(headers):
            self.apply_font(7, bold=True)
            self.cell(_COL_W[i], line_h, h, border=1, fill=True, align="C")
        self.ln()

        for idx, rm in enumerate(missoes, start=1):
            self.apply_font(7)
            descr_full = f"{rm.missao.descricao} - {rm.missao.cidade}/{rm.missao.uf}"
            descr = self._fit_text(descr_full, _COL_W[1] - 2)
            row: list[tuple[float, str, str]] = [
                (_COL_W[0], str(idx), "C"),
                (_COL_W[1], descr, "L"),
                (_COL_W[2], rm.missao.om_destino, "C"),
                (_COL_W[3], rm.missao.data_inicio.strftime("%d/%m/%Y"), "C"),
                (_COL_W[4], rm.missao.data_termino.strftime("%d/%m/%Y"), "C"),
                (_COL_W[5], str(rm.dias), "C"),
                (_COL_W[6], _brl(rm.total_diarias), "R"),
                (_COL_W[7], _brl(rm.total_deslocamento), "R"),
                (_COL_W[8], _brl(rm.total), "R"),
            ]
            fill = idx % 2 == 0
            self.set_fill_color(240, 245, 252)
            for w, txt, align in row:
                self.apply_font(7)
                self.cell(w, line_h, txt, border=1, fill=fill, align=align)  # type: ignore[arg-type]
            self.ln()

        self.apply_font(7, bold=True)
        self.cell(
            _COL_W[0] + _COL_W[1] + _COL_W[2] + _COL_W[3] + _COL_W[4],
            line_h,
            "TOTAIS",
            border=1,
            align="R",
        )
        self.cell(_COL_W[5], line_h, str(sum((rm.dias for rm in missoes), 0)), border=1, align="C")
        self.cell(
            _COL_W[6],
            line_h,
            _brl(sum((rm.total_diarias for rm in missoes), Decimal("0"))),
            border=1,
            align="R",
        )
        self.cell(
            _COL_W[7],
            line_h,
            _brl(sum((rm.total_deslocamento for rm in missoes), Decimal("0"))),
            border=1,
            align="R",
        )
        self.cell(
            _COL_W[8],
            line_h,
            _brl(sum((rm.total for rm in missoes), Decimal("0"))),
            border=1,
            align="R",
        )
        self.ln()
        self.ln(3)

    def render_comparativo(self, calculo: Calculo) -> None:
        self.section_header("COMPARATIVO FINANCEIRO")

        line_h = 5.0
        label_w = 95.0
        value_w = (_PAGE_W - label_w) / 3
        diferenca = abs(calculo.total_ajuda_custo - calculo.total_missoes)
        self.set_fill_color(180, 200, 225)
        self.apply_font(8, bold=True)
        for title in ("Item", "Ajuda de custo", "Diárias + desloc.", "Comparativo"):
            w = label_w if title == "Item" else value_w
            self.cell(w, line_h, title, border=1, fill=True, align="C")
        self.ln()

        self.apply_font(8)
        self.cell(label_w, line_h, "Valores apurados", border=1)
        self.cell(value_w, line_h, _brl(calculo.total_ajuda_custo), border=1, align="R")
        self.cell(value_w, line_h, _brl(calculo.total_missoes), border=1, align="R")
        self.cell(value_w, line_h, _brl(diferenca), border=1, align="R")
        self.ln(6)

    def render_assinatura(self) -> None:
        self.set_xy(183, 174)
        self.apply_font(9)
        self.cell(95, 5, "____________________________", align="C")
        self.ln(5)
        self.set_x(183)
        self.apply_font(9)
        self.cell(95, 5, "DIRETOR_NOME_PRIVADO", align="C")
        self.ln(5)
        self.set_x(183)
        self.apply_font(9)
        self.cell(95, 5, "Diretor do IAOp", align="C")

    # ------------------------------------------------------------------
    # Cabeçalho e rodapé de página
    # ------------------------------------------------------------------

    def header(self) -> None:
        self.apply_font(10, bold=True)
        self.cell(0, 4.5, "MINISTÉRIO DA DEFESA", align="C")
        self.ln(4.5)
        self.apply_font(10)
        self.cell(0, 4.5, "COMANDO DA AERONÁUTICA", align="C")
        self.ln(4.5)
        self.cell(0, 4.5, "INSTITUTO DE APLICAÇÕES OPERACIONAIS", align="C")
        self.ln(4.5)
        self.apply_font(9, underline=True)
        self.cell(0, 4.5, "Assunto: Solicitação de Abertura de Comissionamento", align="C")
        self.ln(7)
        self.set_text_color(0, 0, 0)

    def footer(self) -> None:
        self.set_y(-8)
        self.apply_font(7)
        self.set_text_color(140, 140, 140)
        self.cell(0, 4, f"Página {self.page_no()} / {{nb}}", align="C")
        self.set_text_color(0, 0, 0)


def gerar_pdf(calculo: Calculo, caminho: str) -> None:
    pdf = _RelatorioPDF()
    pdf.alias_nb_pages()
    pdf.add_page()

    pdf.render_identificacao(calculo)
    pdf.render_bases(calculo)
    pdf.render_missoes(calculo.missoes)
    pdf.render_comparativo(calculo)
    pdf.render_assinatura()

    pdf.output(caminho)
