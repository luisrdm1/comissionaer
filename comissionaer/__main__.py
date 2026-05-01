"""Ponto de entrada: comissionaer."""

from rich.console import Console
from rich.panel import Panel

from comissionaer.calc import calcular
from comissionaer.cli import coletar_dados
from comissionaer.report import gerar_pdf

console = Console()


def main() -> None:
    console.print(
        Panel.fit(
            "[bold cyan]ComissionAER[/bold cyan] — Análise de Economicidade de Comissionamento\n"
            "[dim]Força Aérea Brasileira · 2026[/dim]",
            border_style="cyan",
        )
    )

    militar, missoes, caminho = coletar_dados()
    calculo = calcular(militar, missoes)

    console.print("\n[bold green]Gerando PDF...[/bold green]")
    gerar_pdf(calculo, caminho)
    console.print(f"[bold]Relatório salvo em:[/bold] [underline]{caminho}[/underline]")


if __name__ == "__main__":
    main()
