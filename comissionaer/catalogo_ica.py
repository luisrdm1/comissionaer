"""Carga e busca do catalogo ICA 55-87/2026."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from importlib import resources
from typing import cast
from unicodedata import normalize

import yaml

from comissionaer.models import CategoriaDiaria, Missao

_CATALOGO_ARQUIVO = "missoes_ica_55_87_2026.yaml"


@dataclass(frozen=True)
class FonteCatalogoICA:
    documento: str
    pagina: int | None
    trecho: str


@dataclass(frozen=True)
class MissaoCatalogoICA:
    id: str
    descricao: str
    om_destino: tuple[str, ...]
    om_diretora: str
    om_coordenadora: str
    om_executora: str
    local_desdobramento_icao: tuple[str, ...]
    cidade: str
    uf: str
    categoria_diaria: CategoriaDiaria | None
    data_inicio_oficial: date
    data_termino_oficial: date
    data_inicio_planejamento: date
    data_termino_planejamento: date
    fonte: FonteCatalogoICA
    confianca: str
    observacoes: str


@dataclass(frozen=True)
class CatalogoICA:
    schema_version: int
    missoes: tuple[MissaoCatalogoICA, ...]


def _as_mapping(value: object, campo: str) -> Mapping[object, object]:
    if not isinstance(value, Mapping):
        raise ValueError(f"Campo {campo} deve ser um mapa YAML.")
    return cast(Mapping[object, object], value)


def _as_sequence(value: object, campo: str) -> Sequence[object]:
    if isinstance(value, str) or not isinstance(value, Sequence):
        raise ValueError(f"Campo {campo} deve ser uma lista YAML.")
    return cast(Sequence[object], value)


def _required(mapping: Mapping[object, object], key: str, contexto: str) -> object:
    if key not in mapping:
        raise ValueError(f"Campo obrigatorio ausente em {contexto}: {key}")
    return mapping[key]


def _optional_str(mapping: Mapping[object, object], key: str) -> str:
    value = mapping.get(key, "")
    if value is None:
        return ""
    return str(value)


def _str_list(value: object, campo: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value,) if value else ()
    return tuple(str(item) for item in _as_sequence(value, campo) if item is not None and str(item))


def _date(value: object, campo: str) -> date:
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        return date.fromisoformat(value)
    raise ValueError(f"Campo {campo} deve ser uma data ISO.")


def _int(value: object, campo: str) -> int:
    if isinstance(value, bool) or value is None:
        raise ValueError(f"Campo {campo} deve ser um inteiro.")
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        return int(value)
    raise ValueError(f"Campo {campo} deve ser um inteiro.")


def _categoria(value: object) -> CategoriaDiaria | None:
    if value is None:
        return None
    raw = str(value)
    if not raw:
        return None
    if raw in CategoriaDiaria.__members__:
        return CategoriaDiaria[raw]
    for categoria in CategoriaDiaria:
        if categoria.value == raw:
            return categoria
    raise ValueError(f"Categoria de diaria desconhecida: {raw}")


def _fonte(value: object, contexto: str) -> FonteCatalogoICA:
    mapping = _as_mapping(value, f"{contexto}.fonte")
    pagina_obj = mapping.get("pagina")
    return FonteCatalogoICA(
        documento=_optional_str(mapping, "documento"),
        pagina=_int(pagina_obj, f"{contexto}.fonte.pagina") if pagina_obj is not None else None,
        trecho=_optional_str(mapping, "trecho"),
    )


def _missao(value: object) -> MissaoCatalogoICA:
    mapping = _as_mapping(value, "missoes[]")
    missao_id = str(_required(mapping, "id", "missao"))
    contexto = f"missao {missao_id}"
    return MissaoCatalogoICA(
        id=missao_id,
        descricao=str(_required(mapping, "descricao", contexto)),
        om_destino=_str_list(mapping.get("om_destino"), f"{contexto}.om_destino"),
        om_diretora=_optional_str(mapping, "om_diretora"),
        om_coordenadora=_optional_str(mapping, "om_coordenadora"),
        om_executora=_optional_str(mapping, "om_executora"),
        local_desdobramento_icao=_str_list(
            mapping.get("local_desdobramento_icao"), f"{contexto}.local_desdobramento_icao"
        ),
        cidade=_optional_str(mapping, "cidade"),
        uf=_optional_str(mapping, "uf"),
        categoria_diaria=_categoria(mapping.get("categoria_diaria")),
        data_inicio_oficial=_date(
            _required(mapping, "data_inicio_oficial", contexto), f"{contexto}.data_inicio_oficial"
        ),
        data_termino_oficial=_date(
            _required(mapping, "data_termino_oficial", contexto), f"{contexto}.data_termino_oficial"
        ),
        data_inicio_planejamento=_date(
            _required(mapping, "data_inicio_planejamento", contexto),
            f"{contexto}.data_inicio_planejamento",
        ),
        data_termino_planejamento=_date(
            _required(mapping, "data_termino_planejamento", contexto),
            f"{contexto}.data_termino_planejamento",
        ),
        fonte=_fonte(_required(mapping, "fonte", contexto), contexto),
        confianca=_optional_str(mapping, "confianca"),
        observacoes=_optional_str(mapping, "observacoes"),
    )


def carregar_catalogo_ica_55_87_2026() -> CatalogoICA:
    texto = (
        resources.files("comissionaer.data").joinpath(_CATALOGO_ARQUIVO).read_text(encoding="utf-8")
    )
    raw_obj: object = yaml.safe_load(texto)
    raw = _as_mapping(raw_obj, "catalogo")
    missoes_obj = _required(raw, "missoes", "catalogo")
    missoes = tuple(_missao(item) for item in _as_sequence(missoes_obj, "catalogo.missoes"))
    return CatalogoICA(
        schema_version=_int(
            _required(raw, "schema_version", "catalogo"), "catalogo.schema_version"
        ),
        missoes=missoes,
    )


def _normalizar(value: str) -> str:
    ascii_text = normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    return ascii_text.casefold()


def _contem(haystack: Sequence[str], needle: str) -> bool:
    termo = _normalizar(needle)
    return any(termo in _normalizar(item) for item in haystack)


def _ano_atinge(missao: MissaoCatalogoICA, ano: int) -> bool:
    return (
        missao.data_inicio_oficial.year <= ano <= missao.data_termino_oficial.year
        or missao.data_inicio_planejamento.year <= ano <= missao.data_termino_planejamento.year
    )


def buscar_missoes_catalogo(
    catalogo: CatalogoICA,
    *,
    texto: str = "",
    om: str = "",
    cidade: str = "",
    uf: str = "",
    icao: str = "",
    ano: int | None = None,
) -> list[MissaoCatalogoICA]:
    resultados: list[MissaoCatalogoICA] = []
    for missao in catalogo.missoes:
        campos_texto = (
            missao.id,
            missao.descricao,
            missao.cidade,
            missao.uf,
            *missao.om_destino,
            missao.om_diretora,
            missao.om_coordenadora,
            missao.om_executora,
            *missao.local_desdobramento_icao,
        )
        if texto and not _contem(campos_texto, texto):
            continue
        if om and not _contem(
            (
                *missao.om_destino,
                missao.om_diretora,
                missao.om_coordenadora,
                missao.om_executora,
            ),
            om,
        ):
            continue
        if cidade and not _contem((missao.cidade,), cidade):
            continue
        if uf and _normalizar(missao.uf) != _normalizar(uf):
            continue
        if icao and not _contem(missao.local_desdobramento_icao, icao):
            continue
        if ano is not None and not _ano_atinge(missao, ano):
            continue
        resultados.append(missao)
    return resultados


def missao_planejamento_from_catalogo(
    item: MissaoCatalogoICA,
    *,
    om_destino: str | None = None,
    categoria_diaria: CategoriaDiaria | None = None,
    data_inicio: date | None = None,
    data_termino: date | None = None,
    num_deslocamentos: int = 1,
) -> Missao:
    categoria = categoria_diaria or item.categoria_diaria
    if categoria is None:
        raise ValueError("Missao do catalogo nao possui categoria de diaria definida.")
    return Missao(
        descricao=item.descricao,
        om_destino=om_destino or (item.om_destino[0] if item.om_destino else ""),
        cidade=item.cidade,
        uf=item.uf,
        categoria_diaria=categoria,
        data_inicio=data_inicio or item.data_inicio_planejamento,
        data_termino=data_termino or item.data_termino_planejamento,
        num_deslocamentos=num_deslocamentos,
    )
