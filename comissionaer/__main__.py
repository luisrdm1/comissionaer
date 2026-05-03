"""Ponto de entrada: comissionaer."""

import sys

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from comissionaer.calc import calcular
from comissionaer.catalogo_ica import buscar_missoes_catalogo, carregar_catalogo_ica_55_87_2026
from comissionaer.cli import coletar_dados, perguntar_salvar_yaml
from comissionaer.report import gerar_pdf
from comissionaer.yaml_io import carregar_yaml, salvar_yaml

console = Console()


def _parse_flag(flag: str) -> str | None:
    """Retorna o valor do flag se presente em sys.argv, ou None."""
    args = sys.argv[1:]
    if flag in args:
        idx = args.index(flag)
        if idx + 1 < len(args):
            return args[idx + 1]
    return None


def _parse_int_flag(flag: str) -> int | None:
    raw = _parse_flag(flag)
    return int(raw) if raw else None


def _listar_catalogo_ica() -> None:
    catalogo = carregar_catalogo_ica_55_87_2026()
    resultados = buscar_missoes_catalogo(
        catalogo,
        texto=_parse_flag("--texto") or "",
        om=_parse_flag("--om") or "",
        cidade=_parse_flag("--cidade") or "",
        uf=_parse_flag("--uf") or "",
        icao=_parse_flag("--icao") or "",
        ano=_parse_int_flag("--ano"),
    )
    limite = _parse_int_flag("--limite") or 50
    table = Table(title=f"Catalogo ICA 55-87/2026 ({len(resultados)} encontradas)")
    table.add_column("Inicio")
    table.add_column("Termino")
    table.add_column("Missao")
    table.add_column("OM")
    table.add_column("Local")
    for missao in resultados[:limite]:
        table.add_row(
            missao.data_inicio_planejamento.isoformat(),
            missao.data_termino_planejamento.isoformat(),
            missao.descricao,
            ", ".join(missao.om_destino),
            f"{missao.cidade}/{missao.uf}" if missao.cidade and missao.uf else "",
        )
    console.print(table)


def main() -> None:
    console.print(
        Panel.fit(
            "[bold cyan]ComissionAER[/bold cyan] — Análise de Economicidade de Comissionamento\n"
            "[dim]Força Aérea Brasileira · 2026[/dim]",
            border_style="cyan",
        )
    )

    caminho_ods = _parse_flag("--ods")
    caminho_yaml_from = _parse_flag("--from")

    if "--catalogo-ica" in sys.argv[1:]:
        _listar_catalogo_ica()
        return

    if caminho_yaml_from:
        console.print(
            f"[bold]Carregando planejamento de:[/bold] [underline]{caminho_yaml_from}[/underline]"
        )
        militar, missoes, caminho, nome_aba = carregar_yaml(caminho_yaml_from)
    else:
        militar, missoes, caminho = coletar_dados()
        nome_aba = None
        caminho_yaml_destino = perguntar_salvar_yaml(caminho)
        if caminho_yaml_destino:
            salvar_yaml(militar, missoes, caminho, caminho_yaml_destino)
            console.print(
                f"[bold]Planejamento salvo em:[/bold] [underline]{caminho_yaml_destino}[/underline]"
            )

    calculo = calcular(militar, missoes)

    console.print("\n[bold green]Gerando PDF...[/bold green]")
    gerar_pdf(calculo, caminho)
    console.print(f"[bold]Relatório salvo em:[/bold] [underline]{caminho}[/underline]")

    if caminho_ods:
        from comissionaer.ods_io import atualizar_ods, derivar_nome_aba

        aba = nome_aba or derivar_nome_aba(calculo)
        console.print(f"\n[bold green]Atualizando ODS:[/bold green] aba [cyan]{aba}[/cyan]")
        atualizar_ods(caminho_ods, {aba: calculo})
        console.print(f"[bold]ODS salvo em:[/bold] [underline]{caminho_ods}[/underline]")


if __name__ == "__main__":
    main()
