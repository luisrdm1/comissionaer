"""Serialização/deserialização de planejamentos de comissionamento em YAML."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

import yaml
from typing_extensions import TypedDict

from comissionaer.models import (
    CategoriaDiaria,
    Dependentes,
    Habilitacao,
    Militar,
    Missao,
    Posto,
)


class _MilitarDict(TypedDict):
    nome: str
    nome_guerra: str
    saram: str
    posto: str
    habilitacao: str
    dependentes: bool
    pct_compensacao_organica: str
    data_inicio_comissionamento: str | None
    data_termino_comissionamento: str | None
    posto_encerramento: str | None
    habilitacao_encerramento: str | None
    pct_compensacao_organica_encerramento: str | None


class _MissaoDict(TypedDict):
    descricao: str
    om_destino: str
    cidade: str
    uf: str
    categoria_diaria: str
    data_inicio: str
    data_termino: str
    num_deslocamentos: int


def _militar_to_dict(m: Militar) -> _MilitarDict:
    return {
        "nome": m.nome,
        "nome_guerra": m.nome_guerra,
        "saram": m.saram,
        "posto": m.posto.name,
        "habilitacao": m.habilitacao.name,
        "dependentes": m.dependentes == Dependentes.SIM,
        "pct_compensacao_organica": str(m.pct_compensacao_organica),
        "data_inicio_comissionamento": (
            m.data_inicio_comissionamento.isoformat() if m.data_inicio_comissionamento else None
        ),
        "data_termino_comissionamento": (
            m.data_termino_comissionamento.isoformat() if m.data_termino_comissionamento else None
        ),
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


def _missao_to_dict(m: Missao) -> _MissaoDict:
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
    data: dict[str, object] = {
        "militar": _militar_to_dict(militar),
        "missoes": [_missao_to_dict(m) for m in missoes],
        "caminho_pdf": caminho_pdf,
    }
    if nome_aba is not None:
        data["nome_aba"] = nome_aba
    Path(caminho_yaml).write_text(
        yaml.dump(data, allow_unicode=True, default_flow_style=False, sort_keys=False),
        encoding="utf-8",
    )


def _dict_to_militar(d: _MilitarDict) -> Militar:
    data_inicio = d["data_inicio_comissionamento"]
    data_termino = d["data_termino_comissionamento"]
    return Militar(
        nome=d["nome"],
        nome_guerra=d["nome_guerra"],
        saram=d["saram"],
        posto=Posto[d["posto"]],
        habilitacao=Habilitacao[d["habilitacao"]],
        dependentes=Dependentes.SIM if d["dependentes"] else Dependentes.NAO,
        pct_compensacao_organica=Decimal(d["pct_compensacao_organica"]),
        data_inicio_comissionamento=date.fromisoformat(data_inicio) if data_inicio else None,
        data_termino_comissionamento=date.fromisoformat(data_termino) if data_termino else None,
        posto_encerramento=Posto[d["posto_encerramento"]] if d["posto_encerramento"] else None,
        habilitacao_encerramento=(
            Habilitacao[d["habilitacao_encerramento"]] if d["habilitacao_encerramento"] else None
        ),
        pct_compensacao_organica_encerramento=(
            Decimal(d["pct_compensacao_organica_encerramento"])
            if d["pct_compensacao_organica_encerramento"] is not None
            else None
        ),
    )


def _dict_to_missao(d: _MissaoDict) -> Missao:
    return Missao(
        descricao=d["descricao"],
        om_destino=d["om_destino"],
        cidade=d["cidade"],
        uf=d["uf"],
        categoria_diaria=CategoriaDiaria[d["categoria_diaria"]],
        data_inicio=date.fromisoformat(d["data_inicio"]),
        data_termino=date.fromisoformat(d["data_termino"]),
        num_deslocamentos=d["num_deslocamentos"],
    )


def carregar_yaml(caminho_yaml: str) -> tuple[Militar, list[Missao], str, str | None]:
    raw: dict[str, object] = yaml.safe_load(Path(caminho_yaml).read_text(encoding="utf-8"))
    militar = _dict_to_militar(raw["militar"])  # type: ignore[arg-type]
    missoes = [_dict_to_missao(m) for m in raw["missoes"]]  # type: ignore[arg-type]
    caminho_pdf = str(raw.get("caminho_pdf", "comissionamento.pdf"))
    nome_aba = str(raw["nome_aba"]) if raw.get("nome_aba") else None
    return militar, missoes, caminho_pdf, nome_aba
