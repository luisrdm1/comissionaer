"""Interface interativa de linha de comando."""

from __future__ import annotations

import contextlib
from collections.abc import Iterator
from datetime import date, datetime
from decimal import Decimal
from typing import Any
from unicodedata import normalize as _unicode_normalize

import questionary
from prompt_toolkit.completion import CompleteEvent, Completer, Completion
from prompt_toolkit.document import Document as PromptDocument
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from comissionaer import calc
from comissionaer.catalogo_ica import (
    MissaoCatalogoICA,
    carregar_catalogo_ica_55_87_2026,
    missao_planejamento_from_catalogo,
)
from comissionaer.models import (
    CategoriaDiaria,
    Dependentes,
    Habilitacao,
    Militar,
    Missao,
    Posto,
    ResultadoMissao,
    classificar_ajuda_custo_por_dias,
    dias_missoes,
    dias_periodo,
    periodo_missoes,
    proximo_posto,
)

console = Console()


class _Cancelado(Exception):
    """Usuário pressionou ESC — sobe um nível em vez de sair do programa."""


# ---------------------------------------------------------------------------
# Helpers tipados sobre questionary
# ---------------------------------------------------------------------------


def _ask_select(message: str, choices: list[str]) -> str:
    result: Any = questionary.select(message, choices=choices).ask()
    if result is None:
        raise _Cancelado
    return str(result)


def _ask_text(message: str, default: str = "") -> str:
    result: Any = questionary.text(message, default=default).ask()
    if result is None:
        raise _Cancelado
    return str(result).strip()


def _ask_confirm(message: str, default: bool = True) -> bool:
    result: Any = questionary.confirm(message, default=default).ask()
    if result is None:
        raise _Cancelado
    return bool(result)


def _ask_date(message: str, default: date | None = None) -> date:
    while True:
        default_text = default.strftime("%d/%m/%Y") if default else ""
        raw = _ask_text(f"{message} (DD/MM/AAAA)", default=default_text)
        if not raw and default is not None:
            return default
        try:
            return datetime.strptime(raw, "%d/%m/%Y").date()
        except ValueError:
            console.print("  Data inválida. Use o formato DD/MM/AAAA.", style="bold red")


def _ask_cotas_voo(message: str, default: int = 0) -> Decimal:
    while True:
        raw = _ask_text(
            f"{message} (0 a 10 cotas, cada cota = 2%):",
            default=str(default),
        )
        try:
            value = int(raw)
            if value < 0 or value > 10:
                raise ValueError
            return Decimal(value * 2) / 100
        except ValueError:
            console.print("  Valor inválido. Informe um inteiro de 0 a 10.", style="bold red")


def _pct_to_cotas(pct: Decimal) -> int:
    return int(pct * 50)


def _fmt_brl(v: Decimal) -> str:
    formatted = f"{v:,.2f}"
    return "R$ " + formatted.replace(",", "X").replace(".", ",").replace("X", ".")


def _fmt_fator(v: Decimal) -> str:
    return f"{v:g}".replace(".", ",")


# ---------------------------------------------------------------------------
# Tabelas de revisão (Rich)
# ---------------------------------------------------------------------------

_CONFIRMAR = "✓ Confirmar"
_SIM = "Sim"
_NAO = "Não"


def _tabela_militar(m: Militar) -> None:
    t = Table(title="Dados do Militar", show_header=False, box=None, padding=(0, 2))
    t.add_column("Campo", style="bold cyan")
    t.add_column("Valor")
    t.add_row("Posto", m.posto.value)
    t.add_row("Nome", m.nome)
    t.add_row("Habilitação", m.habilitacao.value)
    t.add_row("Dependentes", _SIM if m.dependentes == Dependentes.SIM else _NAO)
    t.add_row("Comp. Orgânica (abertura)", f"{_pct_to_cotas(m.pct_compensacao_organica)} cotas")
    tem_enc = (
        m.posto_encerramento
        or m.habilitacao_encerramento
        or m.pct_compensacao_organica_encerramento is not None
    )
    if tem_enc:
        t.add_row("— Encerramento —", "")
        if m.posto_encerramento:
            t.add_row("  Posto no encerramento", m.posto_encerramento.value)
        if m.habilitacao_encerramento:
            t.add_row("  Habilitação no encerramento", m.habilitacao_encerramento.value)
        if m.pct_compensacao_organica_encerramento is not None:
            t.add_row(
                "  Comp. Orgânica (encerramento)",
                f"{_pct_to_cotas(m.pct_compensacao_organica_encerramento)} cotas",
            )
    else:
        t.add_row("Encerramento", "Igual à abertura")
    console.print()
    console.print(t)


def _tabela_missao(m: Missao, titulo: str = "Missão") -> None:
    dias = (m.data_termino - m.data_inicio).days + 1
    t = Table(title=titulo, show_header=False, box=None, padding=(0, 2))
    t.add_column("Campo", style="bold cyan")
    t.add_column("Valor")
    t.add_row("Descrição", m.descricao)
    t.add_row("OM de destino", m.om_destino)
    t.add_row("Município/UF", f"{m.cidade}/{m.uf}")
    t.add_row("Categoria da diária", m.categoria_diaria.value)
    t.add_row("Início", m.data_inicio.strftime("%d/%m/%Y"))
    t.add_row("Término", m.data_termino.strftime("%d/%m/%Y"))
    t.add_row("Dias", str(dias))
    console.print()
    console.print(t)


def _missoes_concomitantes(missoes: list[Missao]) -> list[tuple[int, int]]:
    pares: list[tuple[int, int]] = []
    for i in range(len(missoes)):
        for j in range(i + 1, len(missoes)):
            a, b = missoes[i], missoes[j]
            if a.data_inicio <= b.data_termino and b.data_inicio <= a.data_termino:
                pares.append((i, j))
    return pares


def _tabela_lista_missoes(missoes: list[Missao], militar: Militar | None = None) -> None:
    conflitos = _missoes_concomitantes(missoes)
    idxs_conflito: set[int] = {i for par in conflitos for i in par}

    resultados: list[ResultadoMissao] | None = None
    if militar is not None:
        resultados = [calc.calcular_missao(m, militar.posto) for m in missoes]

    t = Table(title=f"Missões ({len(missoes)})", show_header=True, padding=(0, 1))
    t.add_column("#", style="bold", justify="right")
    t.add_column("Descrição", max_width=42, no_wrap=False)
    t.add_column("OM")
    t.add_column("Local")
    t.add_column("Início")
    t.add_column("Término")
    t.add_column("Dias", justify="right")
    if resultados is not None:
        t.add_column("Diária unit.", justify="right")
        t.add_column("Total diárias", justify="right")
        t.add_column("Deslocamento", justify="right")
        t.add_column("Total missão", justify="right")

    for i, m in enumerate(missoes):
        dias = str((m.data_termino - m.data_inicio).days + 1)
        row_style = "bold red" if i in idxs_conflito else ""
        row: list[str] = [
            str(i + 1),
            m.descricao,
            m.om_destino,
            f"{m.cidade}/{m.uf}",
            m.data_inicio.strftime("%d/%m/%Y"),
            m.data_termino.strftime("%d/%m/%Y"),
            dias,
        ]
        if resultados is not None:
            r = resultados[i]
            row += [
                _fmt_brl(r.valor_diaria_unitario),
                _fmt_brl(r.total_diarias),
                _fmt_brl(r.total_deslocamento),
                _fmt_brl(r.total),
            ]
        t.add_row(*row, style=row_style)

    console.print()
    console.print(t)

    if conflitos:
        pares_str = ", ".join(f"#{a + 1}+#{b + 1}" for a, b in conflitos)
        console.print(
            f"  [bold red]Aviso:[/bold red] missões com períodos sobrepostos: {pares_str}.",
        )

    if militar is not None and resultados is not None:
        total_dias = dias_missoes(missoes)
        regime = "LONGO (> 90 dias)" if total_dias > 90 else "CURTO (≤ 90 dias)"
        faixa = classificar_ajuda_custo_por_dias(total_dias)
        total_diarias_v = sum((r.total_diarias for r in resultados), Decimal("0"))
        total_deslocamentos_v = sum((r.total_deslocamento for r in resultados), Decimal("0"))
        total_geral = total_diarias_v + total_deslocamentos_v

        base = calc.calcular_base(militar)
        base_enc = calc.calcular_base_encerramento(militar)
        fator_ida, fator_volta = calc.fatores_ajuda_custo(faixa, militar.dependentes)
        ajuda_ida = base.total * fator_ida
        ajuda_volta = base_enc.total * fator_volta
        ajuda_total = ajuda_ida + ajuda_volta

        linhas = "\n".join(
            [
                f"Total de dias de missões:  [bold]{total_dias}[/bold]  —  {regime}",
                f"Enquadramento:  {faixa.value}",
                f"Total diárias:  [bold]{_fmt_brl(total_diarias_v)}[/bold]",
                f"Total deslocamentos:  [bold]{_fmt_brl(total_deslocamentos_v)}[/bold]",
                f"Total geral:  [bold]{_fmt_brl(total_geral)}[/bold]",
                f"Ajuda de custo — ida ({_fmt_fator(fator_ida)}×):  {_fmt_brl(ajuda_ida)}",
                f"Ajuda de custo — volta ({_fmt_fator(fator_volta)}×):  {_fmt_brl(ajuda_volta)}",
                f"Total ajuda de custo:  [bold]{_fmt_brl(ajuda_total)}[/bold]",
            ]
        )
        console.print(Panel(linhas, title="Resumo do comissionamento", border_style="cyan"))


# ---------------------------------------------------------------------------
# Coleta e revisão do militar
# ---------------------------------------------------------------------------

_CAMPO_POSTO = "Posto"
_CAMPO_NOME = "Nome"
_CAMPO_HABILITACAO = "Habilitação"
_CAMPO_DEPENDENTES = "Dependentes"
_CAMPO_COMP_ORG = "Comp. Orgânica (abertura)"
_CAMPO_ENCERRAMENTO = "Situação no encerramento"


_ORDEM_HABILITACAO = list(Habilitacao)


def _habilitacoes_superiores(atual: Habilitacao) -> list[Habilitacao]:
    idx = _ORDEM_HABILITACAO.index(atual)
    return _ORDEM_HABILITACAO[idx + 1 :]


def _coletar_encerramento(
    posto: Posto, habilitacao: Habilitacao
) -> tuple[Posto | None, Habilitacao | None, Decimal | None]:
    posto_enc: Posto | None = None
    hab_enc: Habilitacao | None = None
    pct_comp_enc: Decimal | None = None
    console.print("  — Situação no ENCERRAMENTO —", style="bold yellow")
    prox = proximo_posto(posto)
    if prox is None:
        console.print("  Posto atual não possui promoção superior no cadastro.")
    elif _ask_confirm(f"  Mudará de posto no encerramento? (se sim: {prox.value})", default=False):
        posto_enc = prox
    superiores = _habilitacoes_superiores(habilitacao)
    if superiores and _ask_confirm("  Concluirá nova habilitação no encerramento?", default=False):
        hab_enc_label = _ask_select(
            "  Habilitação no encerramento:", choices=[h.value for h in superiores]
        )
        hab_enc = next(h for h in superiores if h.value == hab_enc_label)
    if _ask_confirm("  O adicional de compensação orgânica mudará no encerramento?", default=False):
        pct_comp_enc = _ask_cotas_voo("  Cotas de voo no encerramento")
    return posto_enc, hab_enc, pct_comp_enc


def _coletar_militar() -> Militar:
    console.print("\n[bold]=== DADOS DO MILITAR ===[/bold]")

    posto_label = _ask_select("Posto:", choices=[p.value for p in Posto])
    posto = next(p for p in Posto if p.value == posto_label)

    nome = _ask_text("Nome completo (sem abreviações):")
    while not nome:
        console.print("  Nome não pode ser vazio.", style="bold red")
        nome = _ask_text("Nome completo (sem abreviações):")

    hab_label = _ask_select(
        "Habilitação (curso mais alto concluído):", choices=[h.value for h in Habilitacao]
    )
    habilitacao = next(h for h in Habilitacao if h.value == hab_label)

    dependentes = Dependentes.SIM if _ask_confirm("Possui dependentes?") else Dependentes.NAO
    pct_comp = _ask_cotas_voo("Cotas de voo (Comp. Orgânica) na abertura")

    posto_enc: Posto | None = None
    hab_enc: Habilitacao | None = None
    pct_comp_enc: Decimal | None = None
    pergunta_enc = "\nHaverá promoção ou conclusão de nova habilitação até o encerramento?"
    if _ask_confirm(pergunta_enc, default=False):
        posto_enc, hab_enc, pct_comp_enc = _coletar_encerramento(posto, habilitacao)

    militar = Militar(
        nome=nome,
        posto=posto,
        habilitacao=habilitacao,
        dependentes=dependentes,
        pct_compensacao_organica=pct_comp,
        posto_encerramento=posto_enc,
        habilitacao_encerramento=hab_enc,
        pct_compensacao_organica_encerramento=pct_comp_enc,
    )

    # revisão com edição campo a campo; ESC no menu do campo = cancelar edição
    while True:
        _tabela_militar(militar)
        try:
            acao = _ask_select(
                "Dados do militar:",
                choices=[
                    _CONFIRMAR,
                    _CAMPO_POSTO,
                    _CAMPO_NOME,
                    _CAMPO_HABILITACAO,
                    _CAMPO_DEPENDENTES,
                    _CAMPO_COMP_ORG,
                    _CAMPO_ENCERRAMENTO,
                ],
            )
        except _Cancelado:
            return militar  # ESC no menu de revisão = confirmar como está

        if acao == _CONFIRMAR:
            return militar

        try:
            if acao == _CAMPO_POSTO:
                label = _ask_select("Posto:", choices=[p.value for p in Posto])
                militar.posto = next(p for p in Posto if p.value == label)
            elif acao == _CAMPO_NOME:
                novo = _ask_text("Nome completo:", default=militar.nome)
                while not novo:
                    console.print("  Nome não pode ser vazio.", style="bold red")
                    novo = _ask_text("Nome completo:", default=militar.nome)
                militar.nome = novo
            elif acao == _CAMPO_HABILITACAO:
                label = _ask_select("Habilitação:", choices=[h.value for h in Habilitacao])
                militar.habilitacao = next(h for h in Habilitacao if h.value == label)
            elif acao == _CAMPO_DEPENDENTES:
                militar.dependentes = (
                    Dependentes.SIM if _ask_confirm("Possui dependentes?") else Dependentes.NAO
                )
            elif acao == _CAMPO_COMP_ORG:
                militar.pct_compensacao_organica = _ask_cotas_voo(
                    "Cotas de voo (abertura)",
                    default=_pct_to_cotas(militar.pct_compensacao_organica),
                )
            elif acao == _CAMPO_ENCERRAMENTO:
                if _ask_confirm("Haverá mudança no encerramento?", default=False):
                    pe, he, pc = _coletar_encerramento(militar.posto, militar.habilitacao)
                    militar.posto_encerramento = pe
                    militar.habilitacao_encerramento = he
                    militar.pct_compensacao_organica_encerramento = pc
                else:
                    militar.posto_encerramento = None
                    militar.habilitacao_encerramento = None
                    militar.pct_compensacao_organica_encerramento = None
        except _Cancelado:
            continue  # ESC durante edição = descartar, volta ao menu


# ---------------------------------------------------------------------------
# Catálogo ICA — busca FZF
# ---------------------------------------------------------------------------

_FZF_MAX = 6
_FZF_STYLE = questionary.Style(
    [
        ("answer", "fg:#2ecc71 bold"),
        ("completion-menu.completion", "bg:#1a2233 fg:#d8d8d8"),
        ("completion-menu.completion.current", "bg:#0055aa fg:#ffffff bold"),
        ("completion-menu.border", "fg:#444466"),
    ]
)


def _norm(s: str) -> str:
    return _unicode_normalize("NFKD", s).encode("ascii", "ignore").decode().casefold()


class _MissaoCompleter(Completer):
    def __init__(self, items: list[str]) -> None:
        self._items = items
        self._normed = [_norm(i) for i in items]

    def get_completions(
        self, document: PromptDocument, complete_event: CompleteEvent
    ) -> Iterator[Completion]:
        query = _norm(document.text)
        count = 0
        for item, normed in zip(self._items, self._normed, strict=True):
            if query in normed:
                if count >= _FZF_MAX:
                    break
                yield Completion(item, start_position=-len(document.text))
                count += 1


def _linha_missao_catalogo(m: MissaoCatalogoICA) -> str:
    inicio = m.data_inicio_planejamento.strftime("%d/%m")
    termino = m.data_termino_planejamento.strftime("%d/%m/%Y")
    local = f"{m.cidade}/{m.uf}" if m.cidade and m.uf else "?"
    om = m.om_destino[0] if m.om_destino else "?"
    return f"{m.descricao}  [{inicio}–{termino}  {local}  {om}]"


def _selecionar_missao_catalogo() -> MissaoCatalogoICA:
    """ESC propaga _Cancelado para o chamador."""
    catalogo = carregar_catalogo_ica_55_87_2026()

    missoes_map: dict[str, MissaoCatalogoICA] = {}
    for m in catalogo.missoes:
        missoes_map[_linha_missao_catalogo(m)] = m

    completer = _MissaoCompleter(list(missoes_map.keys()))
    console.print(
        "\n  Catálogo ICA 55-87/2026 — digite para filtrar (nome, OM, cidade, ICAO):",
        style="bold cyan",
    )

    while True:
        result: Any = questionary.autocomplete(
            "  Missão:",
            choices=[],
            completer=completer,
            style=_FZF_STYLE,
        ).ask()
        if result is None:
            raise _Cancelado
        if result in missoes_map:
            return missoes_map[result]
        console.print("  Selecione uma das opções da lista.", style="bold red")


# ---------------------------------------------------------------------------
# Coleta e revisão de missão
# ---------------------------------------------------------------------------

_CAMPO_DESCRICAO = "Descrição"
_CAMPO_OM = "OM de destino"
_CAMPO_CIDADE = "Município"
_CAMPO_UF = "UF"
_CAMPO_CATEGORIA = "Categoria da diária"
_CAMPO_INICIO = "Data de início"
_CAMPO_TERMINO = "Data de término"

_CAMPOS_MISSAO = [
    _CONFIRMAR,
    _CAMPO_DESCRICAO,
    _CAMPO_OM,
    _CAMPO_CIDADE,
    _CAMPO_UF,
    _CAMPO_CATEGORIA,
    _CAMPO_INICIO,
    _CAMPO_TERMINO,
]


def _revisar_missao(missao: Missao) -> Missao:
    while True:
        _tabela_missao(missao)
        try:
            acao = _ask_select("Dados da missão:", choices=_CAMPOS_MISSAO)
        except _Cancelado:
            return missao  # ESC no menu de revisão = confirmar como está

        if acao == _CONFIRMAR:
            return missao

        try:
            if acao == _CAMPO_DESCRICAO:
                missao.descricao = _ask_text("  Descrição:", default=missao.descricao)
            elif acao == _CAMPO_OM:
                missao.om_destino = _ask_text("  OM de destino:", default=missao.om_destino).upper()
            elif acao == _CAMPO_CIDADE:
                missao.cidade = _ask_text("  Município:", default=missao.cidade)
            elif acao == _CAMPO_UF:
                missao.uf = _ask_text("  UF:", default=missao.uf).upper()[:2]
            elif acao == _CAMPO_CATEGORIA:
                label = _ask_select(
                    "  Categoria da diária:", choices=[c.value for c in CategoriaDiaria]
                )
                missao.categoria_diaria = next(c for c in CategoriaDiaria if c.value == label)
            elif acao == _CAMPO_INICIO:
                missao.data_inicio = _ask_date("  Data de início", default=missao.data_inicio)
                if missao.data_termino < missao.data_inicio:
                    console.print("  Término ajustado para igual ao início.", style="bold yellow")
                    missao.data_termino = missao.data_inicio
            elif acao == _CAMPO_TERMINO:
                while True:
                    missao.data_termino = _ask_date(
                        "  Data de término", default=missao.data_termino
                    )
                    if missao.data_termino >= missao.data_inicio:
                        break
                    console.print("  Data de término anterior ao início.", style="bold red")
        except _Cancelado:
            continue  # ESC durante edição = descartar, volta ao menu


def _coletar_missao_catalogo() -> Missao:
    """_Cancelado propaga caso ESC seja pressionado no campo de busca."""
    item = _selecionar_missao_catalogo()
    console.print(f"\n  Selecionada: {item.descricao}", style="bold green")

    om_destino = item.om_destino[0] if item.om_destino else ""
    if len(item.om_destino) > 1:
        try:
            escolha_om = _ask_select(
                "  OM de destino:", choices=[*item.om_destino, "Informar manualmente"]
            )
            om_destino = (
                _ask_text("  OM de destino:").upper()
                if escolha_om == "Informar manualmente"
                else escolha_om
            )
        except _Cancelado:
            pass  # usa o primeiro OM do catálogo
    elif not om_destino:
        with contextlib.suppress(_Cancelado):
            om_destino = _ask_text("  OM de destino:").upper()

    categoria = item.categoria_diaria
    if categoria is None:
        cat_label = _ask_select(
            "  Categoria da diária:", choices=[c.value for c in CategoriaDiaria]
        )
        categoria = next(c for c in CategoriaDiaria if c.value == cat_label)

    missao = missao_planejamento_from_catalogo(
        item,
        om_destino=om_destino,
        categoria_diaria=categoria,
        data_inicio=item.data_inicio_planejamento,
        data_termino=item.data_termino_planejamento,
        num_deslocamentos=1,
    )
    return _revisar_missao(missao)


def _coletar_missao_manual() -> Missao:
    descricao = _ask_text("  Descrição (ex: EXCON IVR 2027 — Santa Maria/RS):")
    om_destino = _ask_text("  OM de destino (sigla):")
    cidade = _ask_text("  Município de destino:")
    uf = _ask_text("  UF (sigla, ex: RS):").upper()[:2]

    cat_label = _ask_select("  Categoria da diária:", choices=[c.value for c in CategoriaDiaria])
    categoria = next(c for c in CategoriaDiaria if c.value == cat_label)

    inicio = _ask_date("  Data de início")
    termino = _ask_date("  Data de término")
    while termino < inicio:
        console.print("  Data de término anterior ao início.", style="bold red")
        termino = _ask_date("  Data de término")

    missao = Missao(
        descricao=descricao,
        om_destino=om_destino,
        cidade=cidade,
        uf=uf,
        categoria_diaria=categoria,
        data_inicio=inicio,
        data_termino=termino,
        num_deslocamentos=1,
    )
    return _revisar_missao(missao)


# ---------------------------------------------------------------------------
# Gerenciamento da lista de missões
# ---------------------------------------------------------------------------

_ACAO_CONFIRMAR_LISTA = "✓ Confirmar lista de missões"
_ACAO_ADICIONAR = "Adicionar missão"
_ACAO_EDITAR = "Editar missão"
_ACAO_REMOVER = "Remover missão"


def _coletar_nova_missao() -> Missao:
    origem = _ask_select(
        "  Origem dos dados da missão:",
        choices=["Catálogo ICA 55-87/2026", "Informar manualmente"],
    )
    return _coletar_missao_catalogo() if origem.startswith("Catálogo") else _coletar_missao_manual()


def _coletar_missoes(militar: Militar) -> list[Missao]:
    console.print("\n[bold]=== MISSÕES ===[/bold]")
    missoes: list[Missao] = []

    while not missoes:
        console.print("\n  — Missão 1 —", style="bold cyan")
        try:
            missoes.append(_coletar_nova_missao())
        except _Cancelado:
            console.print("  Informe pelo menos uma missão.", style="bold red")

    while True:
        _tabela_lista_missoes(missoes, militar)

        try:
            acao = _ask_select(
                "O que deseja fazer?",
                choices=[_ACAO_CONFIRMAR_LISTA, _ACAO_ADICIONAR, _ACAO_EDITAR, _ACAO_REMOVER],
            )
        except _Cancelado:
            return missoes  # ESC no menu da lista = confirmar como está

        if acao == _ACAO_CONFIRMAR_LISTA:
            return missoes

        if acao == _ACAO_ADICIONAR:
            console.print(f"\n  — Missão {len(missoes) + 1} —", style="bold cyan")
            try:
                missoes.append(_coletar_nova_missao())
            except _Cancelado:
                console.print("  Adição cancelada.", style="yellow")
            continue

        if acao == _ACAO_EDITAR:
            try:
                nomes = [m.descricao[:60] for m in missoes]
                escolha = _ask_select("  Editar qual missão?", choices=nomes)
                idx = nomes.index(escolha)
                missoes[idx] = _revisar_missao(missoes[idx])
            except _Cancelado:
                pass
            continue

        if acao == _ACAO_REMOVER:
            try:
                nomes = [m.descricao[:60] for m in missoes]
                escolha = _ask_select("  Remover qual missão?", choices=nomes)
                idx = nomes.index(escolha)
                removida = missoes.pop(idx)
                console.print(f"  Missão '{removida.descricao}' removida.", style="bold yellow")
                if not missoes:
                    console.print("  Informe pelo menos uma missão.", style="bold red")
                    while not missoes:
                        try:
                            missoes.append(_coletar_nova_missao())
                        except _Cancelado:
                            console.print("  Informe pelo menos uma missão.", style="bold red")
            except _Cancelado:
                pass
            continue


# ---------------------------------------------------------------------------
# Período e arquivo
# ---------------------------------------------------------------------------


def _aplicar_periodo_comissionamento(militar: Militar, missoes: list[Missao]) -> None:
    console.print("\n[bold]=== ENQUADRAMENTO DO COMISSIONAMENTO ===[/bold]")
    inicio, termino = periodo_missoes(missoes)
    faixa = classificar_ajuda_custo_por_dias(dias_missoes(missoes))
    dias_corridos = dias_periodo(inicio, termino)
    militar.data_inicio_comissionamento = inicio
    militar.data_termino_comissionamento = termino
    console.print(
        f"  Período derivado das missões: "
        f"{inicio.strftime('%d/%m/%Y')} a {termino.strftime('%d/%m/%Y')} "
        f"({dias_corridos} dias corridos).",
        style="bold green",
    )
    console.print(f"  Enquadramento de ajuda de custo: {faixa.value}.", style="bold green")


def _pedir_nome_arquivo(nome_militar: str, posto: Posto) -> str:
    slug = nome_militar.split()[0].lower()
    default = f"comissionamento_{posto.name.lower()}_{slug}.pdf"
    nome = _ask_text("\nNome do arquivo PDF:", default=default)
    if not nome.endswith(".pdf"):
        nome += ".pdf"
    return nome


# ---------------------------------------------------------------------------
# Ponto de entrada
# ---------------------------------------------------------------------------


def coletar_dados() -> tuple[Militar, list[Missao], str]:
    """Ponto de entrada do fluxo interativo. Retorna (militar, missoes, caminho_pdf)."""
    try:
        militar = _coletar_militar()
        missoes = _coletar_missoes(militar)
        _aplicar_periodo_comissionamento(militar, missoes)
        console.print(
            f"\nTotal de dias em missões planejadas: {dias_missoes(missoes)}.",
            style="bold green",
        )
        caminho = _pedir_nome_arquivo(militar.nome, militar.posto)
        return militar, missoes, caminho
    except _Cancelado:
        raise SystemExit(0) from None


def perguntar_salvar_yaml(caminho_pdf: str) -> str | None:
    """Pergunta se deseja salvar o planejamento como YAML. Retorna o caminho ou None."""
    if not _ask_confirm("\nDeseja salvar o planejamento como YAML?", default=True):
        return None
    default_yaml = caminho_pdf.removesuffix(".pdf") + ".yaml"
    caminho = _ask_text("Nome do arquivo YAML:", default=default_yaml)
    if not caminho.endswith(".yaml"):
        caminho += ".yaml"
    return caminho
