"""Ponto de entrada: calcfab."""

from rich.console import Console
from rich.panel import Panel

from calcfab.calc import calcular
from calcfab.cli import coletar_dados
from calcfab.report import gerar_pdf

console = Console()


def main() -> None:
    console.print(
        Panel.fit(
            "[bold cyan]CalcFAB[/bold cyan] — Calculadora de Comissionamento\n"
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
