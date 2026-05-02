"""Ponto de entrada: comissionaer."""

import sys

from rich.console import Console
from rich.panel import Panel

from comissionaer.calc import calcular
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


def main() -> None:
    console.print(
        Panel.fit(
            "[bold cyan]ComissionAER[/bold cyan] — Análise de Economicidade de Comissionamento\n"
            "[dim]Força Aérea Brasileira · 2026[/dim]",
            border_style="cyan",
        )
    )

    caminho_xls = _parse_flag("--xls")
    caminho_yaml_from = _parse_flag("--from")

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

    if caminho_xls:
        from comissionaer.xls_io import atualizar_xls, derivar_nome_aba

        aba = nome_aba or derivar_nome_aba(calculo)
        console.print(f"\n[bold green]Atualizando XLS:[/bold green] aba [cyan]{aba}[/cyan]")
        atualizar_xls(caminho_xls, {aba: calculo})
        console.print(f"[bold]XLS salvo em:[/bold] [underline]{caminho_xls}[/underline]")


if __name__ == "__main__":
    main()
