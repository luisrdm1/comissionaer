from datetime import date

from comissionaer.catalogo_ica import (
    buscar_missoes_catalogo,
    carregar_catalogo_ica_55_87_2026,
    missao_planejamento_from_catalogo,
)
from comissionaer.models import CategoriaDiaria


def test_carrega_catalogo_ica_55_87_2026() -> None:
    catalogo = carregar_catalogo_ica_55_87_2026()

    assert catalogo.schema_version == 3
    assert len(catalogo.missoes) > 100


def test_busca_catalogo_por_texto_om_cidade_uf_icao_e_ano() -> None:
    catalogo = carregar_catalogo_ica_55_87_2026()

    resultados = buscar_missoes_catalogo(
        catalogo,
        texto="verificacao tecnica",
        om="BAAN",
        cidade="Anapolis",
        uf="GO",
        icao="SBAN",
        ano=2026,
    )

    ids = {missao.id for missao in resultados}
    assert "avop-f-39e-2026-fase-1-verificacao-tecnica-2026-05-11" in ids


def test_converte_missao_catalogo_para_planejamento() -> None:
    catalogo = carregar_catalogo_ica_55_87_2026()
    item = buscar_missoes_catalogo(catalogo, texto="AVOP F-39E", icao="SBAN")[0]

    missao = missao_planejamento_from_catalogo(item)

    assert missao.descricao == "AVOP F-39E – Fase 1 (Verificação Técnica) (2026)"
    assert missao.om_destino == "BAAN"
    assert missao.cidade == "Anapolis"
    assert missao.uf == "GO"
    assert missao.categoria_diaria == CategoriaDiaria.PADRAO
    assert missao.data_inicio == date(2026, 5, 10)
    assert missao.data_termino == date(2026, 5, 30)
