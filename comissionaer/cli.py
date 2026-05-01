"""Interface interativa de linha de comando."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

import questionary

from comissionaer.models import (
    CategoriaDiaria,
    Dependentes,
    DuracaoComissionamento,
    Habilitacao,
    Militar,
    Missao,
    Posto,
)

# ---------------------------------------------------------------------------
# Helpers tipados sobre questionary (ask() retorna Any)
# ---------------------------------------------------------------------------


def _ask_select(message: str, choices: list[str]) -> str:
    result: Any = questionary.select(message, choices=choices).ask()
    if result is None:
        raise SystemExit(0)
    return str(result)


def _ask_text(message: str, default: str = "") -> str:
    result: Any = questionary.text(message, default=default).ask()
    if result is None:
        raise SystemExit(0)
    return str(result).strip()


def _ask_confirm(message: str, default: bool = True) -> bool:
    result: Any = questionary.confirm(message, default=default).ask()
    if result is None:
        raise SystemExit(0)
    return bool(result)


def _ask_date(message: str) -> date:
    while True:
        raw = _ask_text(f"{message} (DD/MM/AAAA)")
        try:
            return datetime.strptime(raw, "%d/%m/%Y").date()
        except ValueError:
            questionary.print("  Data inválida. Use o formato DD/MM/AAAA.", style="bold fg:red")


def _ask_decimal(message: str, default: str = "0") -> Decimal:
    while True:
        raw = _ask_text(message, default=default)
        raw = raw.replace(",", ".")
        try:
            value = Decimal(raw)
            if value < 0:
                raise ValueError
            return value
        except InvalidOperation, ValueError:
            msg = "  Valor inválido. Use ponto ou vírgula como separador decimal."
            questionary.print(msg, style="bold fg:red")


def _ask_int(message: str, default: int = 1) -> int:
    while True:
        raw = _ask_text(message, default=str(default))
        try:
            value = int(raw)
            if value < 1:
                raise ValueError
            return value
        except ValueError:
            questionary.print("  Informe um número inteiro positivo.", style="bold fg:red")


# ---------------------------------------------------------------------------
# Seções do fluxo
# ---------------------------------------------------------------------------


def _coletar_militar() -> Militar:
    questionary.print("\n=== DADOS DO MILITAR ===", style="bold")

    posto_label = _ask_select("Posto:", choices=[p.value for p in Posto])
    posto = next(p for p in Posto if p.value == posto_label)

    nome = _ask_text("Nome completo (sem abreviações):")
    while not nome:
        questionary.print("  Nome não pode ser vazio.", style="bold fg:red")
        nome = _ask_text("Nome completo:")

    hab_label = _ask_select(
        "Habilitação (curso mais alto concluído):",
        choices=[h.value for h in Habilitacao],
    )
    habilitacao = next(h for h in Habilitacao if h.value == hab_label)

    dependentes = Dependentes.SIM if _ask_confirm("Possui dependentes?") else Dependentes.NAO

    dur_label = _ask_select(
        "Duração do comissionamento:",
        choices=[d.value for d in DuracaoComissionamento],
    )
    duracao = next(d for d in DuracaoComissionamento if d.value == dur_label)

    pct_comp = Decimal("0")
    if _ask_confirm("Possui Adicional de Compensação Orgânica?", default=False):
        pct_comp = _ask_decimal("Percentual do adicional de compensação orgânica (ex: 20):") / 100

    # Encerramento — promoção ou nova habilitação (Decreto 4.307/2002 art. 56)
    posto_enc: Posto | None = None
    hab_enc: Habilitacao | None = None
    pct_comp_enc: Decimal | None = None

    if _ask_confirm(
        "\nHaverá promoção ou conclusão de nova habilitação até o encerramento?",
        default=False,
    ):
        questionary.print("  — Situação no ENCERRAMENTO —", style="bold fg:yellow")

        if _ask_confirm("  Mudará de posto no encerramento?", default=False):
            posto_enc_label = _ask_select(
                "  Posto no encerramento:", choices=[p.value for p in Posto]
            )
            posto_enc = next(p for p in Posto if p.value == posto_enc_label)

        if _ask_confirm("  Concluirá nova habilitação no encerramento?", default=False):
            hab_enc_label = _ask_select(
                "  Habilitação no encerramento:", choices=[h.value for h in Habilitacao]
            )
            hab_enc = next(h for h in Habilitacao if h.value == hab_enc_label)

        if _ask_confirm(
            "  O adicional de compensação orgânica mudará no encerramento?", default=False
        ):
            pct_comp_enc = (
                _ask_decimal("  Percentual de comp. orgânica no encerramento (ex: 25):") / 100
            )

    return Militar(
        nome=nome,
        posto=posto,
        habilitacao=habilitacao,
        dependentes=dependentes,
        pct_compensacao_organica=pct_comp,
        duracao=duracao,
        posto_encerramento=posto_enc,
        habilitacao_encerramento=hab_enc,
        pct_compensacao_organica_encerramento=pct_comp_enc,
    )


def _coletar_missoes() -> list[Missao]:
    questionary.print("\n=== MISSÕES ===", style="bold")
    missoes: list[Missao] = []

    while True:
        if missoes and not _ask_confirm("Adicionar mais uma missão?"):
            break
        if not missoes and not _ask_confirm("Adicionar missão?"):
            break

        questionary.print(f"\n  — Missão {len(missoes) + 1} —", style="bold fg:cyan")

        descricao = _ask_text("  Descrição (ex: EXCON IVR 2027 — Santa Maria/RS):")
        om_destino = _ask_text("  OM de destino (sigla):")
        cidade = _ask_text("  Município de destino:")
        uf = _ask_text("  UF (sigla, ex: RS):").upper()[:2]

        cat_label = _ask_select(
            "  Categoria da diária:",
            choices=[c.value for c in CategoriaDiaria],
        )
        categoria = next(c for c in CategoriaDiaria if c.value == cat_label)

        inicio = _ask_date("  Data de início")
        termino = _ask_date("  Data de término")

        while termino < inicio:
            questionary.print("  Data de término anterior ao início.", style="bold fg:red")
            termino = _ask_date("  Data de término")

        num_desloc = _ask_int("  Número de deslocamentos:", default=1)

        missoes.append(
            Missao(
                descricao=descricao,
                om_destino=om_destino,
                cidade=cidade,
                uf=uf,
                categoria_diaria=categoria,
                data_inicio=inicio,
                data_termino=termino,
                num_deslocamentos=num_desloc,
            )
        )

    return missoes


def _pedir_nome_arquivo(nome_militar: str, posto: Posto) -> str:
    slug = nome_militar.split()[0].lower()
    default = f"comissionamento_{posto.name.lower()}_{slug}.pdf"
    nome = _ask_text("\nNome do arquivo PDF:", default=default)
    if not nome.endswith(".pdf"):
        nome += ".pdf"
    return nome


def coletar_dados() -> tuple[Militar, list[Missao], str]:
    """Ponto de entrada do fluxo interativo. Retorna (militar, missoes, caminho_pdf)."""
    militar = _coletar_militar()
    missoes = _coletar_missoes()
    caminho = _pedir_nome_arquivo(militar.nome, militar.posto)
    return militar, missoes, caminho
