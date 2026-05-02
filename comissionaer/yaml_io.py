"""Serialização/deserialização de planejamentos de comissionamento em YAML."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

import yaml

from comissionaer.models import (
    CategoriaDiaria,
    Dependentes,
    DuracaoComissionamento,
    Habilitacao,
    Militar,
    Missao,
    Posto,
)


def _militar_to_dict(m: Militar) -> dict[str, Any]:
    return {
        "nome": m.nome,
        "posto": m.posto.name,
        "habilitacao": m.habilitacao.name,
        "dependentes": m.dependentes == Dependentes.SIM,
        "pct_compensacao_organica": str(m.pct_compensacao_organica),
        "duracao": m.duracao.name,
        "posto_encerramento": m.posto_encerramento.name if m.posto_encerramento else None,
        "habilitacao_encerramento": (
            m.habilitacao_encerramento.name if m.habilitacao_encerramento else None
        ),
        "pct_compensacao_organica_encerramento": (
            str(m.pct_compensacao_organica_encerramento)
            if m.pct_compensacao_organica_encerramento is not None
            else None
        ),
    }


def _missao_to_dict(m: Missao) -> dict[str, Any]:
    return {
        "descricao": m.descricao,
        "om_destino": m.om_destino,
        "cidade": m.cidade,
        "uf": m.uf,
        "categoria_diaria": m.categoria_diaria.name,
        "data_inicio": m.data_inicio.isoformat(),
        "data_termino": m.data_termino.isoformat(),
        "num_deslocamentos": m.num_deslocamentos,
    }


def salvar_yaml(
    militar: Militar,
    missoes: list[Missao],
    caminho_pdf: str,
    caminho_yaml: str,
    nome_aba: str | None = None,
) -> None:
    data: dict[str, Any] = {
        "militar": _militar_to_dict(militar),
        "missoes": [_missao_to_dict(m) for m in missoes],
        "caminho_pdf": caminho_pdf,
    }
    if nome_aba:
        data["nome_aba"] = nome_aba
    Path(caminho_yaml).write_text(
        yaml.dump(data, allow_unicode=True, default_flow_style=False, sort_keys=False),
        encoding="utf-8",
    )


def _dict_to_militar(d: dict[str, Any]) -> Militar:
    return Militar(
        nome=str(d["nome"]),
        posto=Posto[str(d["posto"])],
        habilitacao=Habilitacao[str(d["habilitacao"])],
        dependentes=Dependentes.SIM if d["dependentes"] else Dependentes.NAO,
        pct_compensacao_organica=Decimal(str(d["pct_compensacao_organica"])),
        duracao=DuracaoComissionamento[str(d["duracao"])],
        posto_encerramento=(
            Posto[str(d["posto_encerramento"])] if d.get("posto_encerramento") else None
        ),
        habilitacao_encerramento=(
            Habilitacao[str(d["habilitacao_encerramento"])]
            if d.get("habilitacao_encerramento")
            else None
        ),
        pct_compensacao_organica_encerramento=(
            Decimal(str(d["pct_compensacao_organica_encerramento"]))
            if d.get("pct_compensacao_organica_encerramento") is not None
            else None
        ),
    )


def _dict_to_missao(d: dict[str, Any]) -> Missao:
    return Missao(
        descricao=str(d["descricao"]),
        om_destino=str(d["om_destino"]),
        cidade=str(d["cidade"]),
        uf=str(d["uf"]),
        categoria_diaria=CategoriaDiaria[str(d["categoria_diaria"])],
        data_inicio=date.fromisoformat(str(d["data_inicio"])),
        data_termino=date.fromisoformat(str(d["data_termino"])),
        num_deslocamentos=int(d.get("num_deslocamentos", 1)),
    )


def carregar_yaml(caminho_yaml: str) -> tuple[Militar, list[Missao], str, str | None]:
    raw: dict[str, Any] = yaml.safe_load(Path(caminho_yaml).read_text(encoding="utf-8"))
    militar = _dict_to_militar(raw["militar"])
    missoes = [_dict_to_missao(m) for m in raw["missoes"]]
    caminho_pdf = str(raw.get("caminho_pdf", "comissionamento.pdf"))
    nome_aba = str(raw["nome_aba"]) if raw.get("nome_aba") else None
    return militar, missoes, caminho_pdf, nome_aba
