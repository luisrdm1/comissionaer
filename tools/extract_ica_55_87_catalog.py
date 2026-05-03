"""Extract a versioned mission catalog from ICA 55-87/2026.

This is a curation tool, not a runtime dependency of ComissionAER. It extracts only
structured ficha headers/tables from the PDF and writes the catalog YAML used by
the CLI/planning flow.
"""

from __future__ import annotations

import argparse
import importlib
import json
import re
import unicodedata
from collections.abc import Callable
from datetime import date, timedelta
from pathlib import Path
from types import TracebackType
from typing import Protocol, cast

import yaml

DOCUMENT_TITLE = "ICA 55-87 - Programa de Atividades Operacionais do COMPREP - 2026"
DEFAULT_PDF = Path("..") / "ICA 55-87 - Programa de Atividades Operacionais do COMPREP - 2026.pdf"
DEFAULT_OUTPUT = Path("comissionaer/data/missoes_ica_55_87_2026.yaml")


class PdfPage(Protocol):
    page_number: int

    def extract_text(self, layout: bool = False) -> str | None: ...

    def extract_tables(self) -> list[list[list[str | None]]] | None: ...


class PdfDocument(Protocol):
    pages: list[PdfPage]

    def __enter__(self) -> PdfDocument: ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool | None: ...


class PdfPlumberModule(Protocol):
    def open(self, path: str | Path) -> PdfDocument: ...


def load_pdfplumber() -> PdfPlumberModule:
    return cast(PdfPlumberModule, importlib.import_module("pdfplumber"))


PDFPLUMBER = load_pdfplumber()

ICAO_TO_OM: dict[str, str] = {
    "SBAF": "BAAF",
    "SBAN": "BAAN",
    "SBBE": "BABE",
    "SBBR": "BABR",
    "SBBV": "BABV",
    "SBCG": "BACG",
    "SBCO": "BACO",
    "SBFL": "BAFL",
    "SBGL": "BAGL",
    "SBMN": "BAMN",
    "SBNT": "BANT",
    "SBSC": "BASC",
    "SBSM": "BASM",
    "SBYS": "AFA",
    "SBCC": "CPBV",
}

OM_TO_LOCAL: dict[str, tuple[str, str]] = {
    "BAAF": ("Rio de Janeiro", "RJ"),
    "BAAN": ("Anapolis", "GO"),
    "BABE": ("Belem", "PA"),
    "BABR": ("Brasilia", "DF"),
    "BABV": ("Boa Vista", "RR"),
    "BACG": ("Campo Grande", "MS"),
    "BACO": ("Canoas", "RS"),
    "BAFL": ("Florianopolis", "SC"),
    "BAGL": ("Rio de Janeiro", "RJ"),
    "BAMN": ("Manaus", "AM"),
    "BANT": ("Parnamirim", "RN"),
    "BASC": ("Rio de Janeiro", "RJ"),
    "BASM": ("Santa Maria", "RS"),
    "CPBV": ("Campo de Provas Brigadeiro Velloso", "PA"),
    "AFA": ("Pirassununga", "SP"),
}

AIRPORT_FALLBACK: dict[str, tuple[str, str]] = {
    "SBAF": ("Rio de Janeiro", "RJ"),
    "SBAN": ("Anapolis", "GO"),
    "SBBE": ("Belem", "PA"),
    "SBBR": ("Brasilia", "DF"),
    "SBBV": ("Boa Vista", "RR"),
    "SBCG": ("Campo Grande", "MS"),
    "SBCO": ("Canoas", "RS"),
    "SBFL": ("Florianopolis", "SC"),
    "SBGL": ("Rio de Janeiro", "RJ"),
    "SBMN": ("Manaus", "AM"),
    "SBNT": ("Parnamirim", "RN"),
    "SBSC": ("Rio de Janeiro", "RJ"),
    "SBSM": ("Santa Maria", "RS"),
    "SBYS": ("Pirassununga", "SP"),
    "SBCC": ("Campo de Provas Brigadeiro Velloso", "PA"),
    "SBSJ": ("Sao Jose dos Campos", "SP"),
    "SBGP": ("Gaviao Peixoto", "SP"),
    "SBGW": ("Guaratingueta", "SP"),
    "SBRF": ("Recife", "PE"),
    "SBST": ("Santos", "SP"),
    "SBUA": ("Sao Gabriel da Cachoeira", "AM"),
    "SBTT": ("Tabatinga", "AM"),
    "CYQQ": ("Comox", ""),
}

UF_NAMES: dict[str, str] = {
    "Acre": "AC",
    "Alagoas": "AL",
    "Amapá": "AP",
    "Amazonas": "AM",
    "Bahia": "BA",
    "Ceará": "CE",
    "Federal-District": "DF",
    "Distrito Federal": "DF",
    "Espírito Santo": "ES",
    "Goiás": "GO",
    "Maranhão": "MA",
    "Mato Grosso": "MT",
    "Mato Grosso do Sul": "MS",
    "Minas Gerais": "MG",
    "Pará": "PA",
    "Paraíba": "PB",
    "Paraná": "PR",
    "Pernambuco": "PE",
    "Piauí": "PI",
    "Rio de Janeiro": "RJ",
    "Rio Grande do Norte": "RN",
    "Rio Grande do Sul": "RS",
    "Rondônia": "RO",
    "Roraima": "RR",
    "Santa Catarina": "SC",
    "São Paulo": "SP",
    "Sergipe": "SE",
    "Tocantins": "TO",
}

CAPITAIS = {
    "Aracaju",
    "Belem",
    "Belo Horizonte",
    "Boa Vista",
    "Campo Grande",
    "Cuiaba",
    "Curitiba",
    "Florianopolis",
    "Fortaleza",
    "Goiania",
    "Joao Pessoa",
    "Macapa",
    "Maceio",
    "Natal",
    "Palmas",
    "Porto Alegre",
    "Porto Velho",
    "Recife",
    "Rio Branco",
    "Salvador",
    "Sao Luis",
    "Teresina",
    "Vitoria",
}
ESPECIAIS = {"Brasilia", "Manaus", "Rio de Janeiro"}

MONTHS: dict[str, int] = {
    "JAN": 1,
    "FEV": 2,
    "MAR": 3,
    "ABR": 4,
    "MAI": 5,
    "JUN": 6,
    "JUL": 7,
    "AGO": 8,
    "SET": 9,
    "OUT": 10,
    "NOV": 11,
    "DEZ": 12,
    "JANEIRO": 1,
    "FEVEREIRO": 2,
    "MARCO": 3,
    "MARÇO": 3,
    "ABRIL": 4,
    "MAIO": 5,
    "JUNHO": 6,
    "JULHO": 7,
    "AGOSTO": 8,
    "SETEMBRO": 9,
    "OUTUBRO": 10,
    "NOVEMBRO": 11,
    "DEZEMBRO": 12,
}

MEETING_RE = re.compile(r"\b(IPC|MPC|FPC|CDC|BACKUP|BACK UP|RESERVA)\b", re.I)
ICAO_RE = re.compile(r"\bSB[A-Z]{2}\b|\bCYQQ\b")
LABEL_RE = re.compile(
    r"DIRETOR DO EXERCÍCIO|COORDENADOR DO EXERCÍCIO|GERENTE DO EXERCÍCIO|"
    r"GERENTE OPERACIONAL|PERÍODO DE EXECUÇÃO|PERÍODO \(S\) DE EXECUÇÃO|"
    r"OM EXECUTORA|ÁREA DE OPERAÇÃO|LOCAL DE DESDOBRAMENTO|"
    r"LOCALIDADES DE DESDOBRAMENTO|NOME",
    re.I,
)
TITLE_RE = re.compile(
    r"^(EXERC[IÍ]CIO|OPERA[ÇC][AÃ]O|AVAOP|REUNI[AÃ]O|INSTEX|AVOP|EW |RADAR |ZEUS|SAREX)",
    re.I,
)
NOISE_RE = re.compile(
    r"^(ANEXO|FICHA DE PLANEJAMENTO|OPERAÇÃO / EXERCÍCIO|ATIVIDADE|DIREÇÃO|LOCAL|"
    r"MATERIAL|Art\.|NÍVEL|PROGRAMA |OBJETIVOS|PREVISÃO|TOTAL|CUSTOS|SUBCENTRO|"
    r"COMANDOS|PARTICIPANTES|UAE |OM |ND |DÓLAR|CONVERSÃO|OBSERVAÇÕES)",
    re.I,
)

FIELD_MAP: dict[str, str] = {
    "DIRETOR DO EXERCÍCIO": "om_diretora",
    "COORDENADOR DO EXERCÍCIO": "om_coordenadora",
    "GERENTE DO EXERCÍCIO": "gerente",
    "GERENTE OPERACIONAL": "gerente",
    "PERÍODO DE EXECUÇÃO": "periodo",
    "PERÍODO (S) DE EXECUÇÃO": "periodo",
    "OM EXECUTORA": "om_executora",
    "ÁREA DE OPERAÇÃO": "area_operacao",
    "LOCAL DE DESDOBRAMENTO": "local_desdobramento",
    "LOCALIDADES DE DESDOBRAMENTO": "local_desdobramento",
    "NOME": "nome",
}

MANUAL_PORTOES: list[tuple[str, str, str, str, str, str, str, int, str]] = [
    (
        "desfile-aereo-90-aniversario-babe-2026",
        "Desfile Aereo - 90o Aniversario da Base Aerea de Belem",
        "BABE",
        "Belem",
        "PA",
        "2026-09-09",
        "2026-09-11",
        184,
        "LOCAL Belem - PA DATA 09 a 11.09.26",
    ),
    (
        "desfile-aereo-can-dia-aviacao-transporte-2026",
        "Desfile Aereo - Cerimonia do CAN/Dia da Aviacao de Transporte",
        "BAGL",
        "Rio de Janeiro",
        "RJ",
        "2026-06-12",
        "2026-06-12",
        184,
        "LOCAL Rio de Janeiro - RJ DATA 12.06.26",
    ),
    (
        "desfile-aereo-eduardo-gomes-2026",
        "Desfile Aereo - 130o Aniversario de nascimento do Marechal Eduardo Gomes",
        "BAGL",
        "Rio de Janeiro",
        "RJ",
        "2026-09-20",
        "2026-09-20",
        184,
        "LOCAL Rio de Janeiro - RJ DATA 20.09.26",
    ),
    (
        "desfile-aereo-platinas-epcar-2026",
        "Desfile Aereo - Entrega de Platinas do 1o Esquadrao",
        "",
        "Barbacena",
        "MG",
        "2026-02-06",
        "2026-02-06",
        185,
        "LOCAL Barbacena - MG DATA 06.02.26",
    ),
    (
        "desfile-aereo-cpcar-2026",
        "Desfile Aereo - Conclusao do Curso Preparatorio de Cadetes do Ar",
        "",
        "Barbacena",
        "MG",
        "2026-12-04",
        "2026-12-04",
        185,
        "LOCAL Barbacena - MG DATA 04.12.26",
    ),
    (
        "portoes-abertos-musal-air-show-2026",
        "Portoes Abertos - MUSAL Air Show e Dia internacional de Museus",
        "BAGL",
        "Rio de Janeiro",
        "RJ",
        "2026-05-16",
        "2026-05-17",
        185,
        "LOCAL Rio de Janeiro - RJ DATA 16 a 17 MAI 26",
    ),
    (
        "desfile-aereo-santos-dumont-musal-2026",
        "Desfile Aereo - Aniversario de Santos Dumont e Aniversario do MUSAL",
        "BAGL",
        "Rio de Janeiro",
        "RJ",
        "2026-07-18",
        "2026-07-19",
        185,
        "LOCAL Rio de Janeiro - RJ DATA 18 a 19 JUL 26",
    ),
]


class NoAliasDumper(yaml.SafeDumper):
    """YAML dumper that avoids anchors for repeated lists."""

    def ignore_aliases(self, data: object) -> bool:
        return True


def ascii_text(value: str) -> str:
    value = value.replace("–", "-").replace("—", "-").replace("º", "o").replace("ª", "a")
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", value).strip()


def clean(value: object) -> str:
    return " ".join(str(value or "").replace("\u00a0", " ").split())


def slug(value: str) -> str:
    value = ascii_text(value).lower()
    return re.sub(r"[^a-z0-9]+", "-", value).strip("-") or "missao"


def year4(value: str | None) -> int:
    if not value:
        return 2026
    year = int(value)
    return 2000 + year if year < 100 else year


def make_date(day: str, month: str, year: str | None) -> date:
    return date(year4(year), int(month), int(day))


def make_month_date(day: str, month: str, year: str | None) -> date:
    return date(year4(year), MONTHS[ascii_text(month).upper()], int(day))


def context_label(text: str, start: int) -> str:
    prefix = text[max(0, start - 80) : start]
    prefix = re.split(r"[.;]\s*", prefix)[-1]
    return re.sub(r"\s+", " ", prefix).strip(" :-")[:80]


def add_range(
    ranges: list[dict[str, object]],
    text: str,
    start_idx: int,
    start: date,
    end: date,
    raw: str,
) -> None:
    if start.year != 2026 and end.year != 2026:
        return
    if end < start:
        end = date(start.year, end.month, end.day)
    ranges.append(
        {
            "label": ascii_text(context_label(text, start_idx)),
            "inicio": start,
            "termino": end,
            "raw": ascii_text(raw),
        }
    )


def extract_ranges(periodo: str) -> list[dict[str, object]]:
    text = periodo.replace("\n", " ")
    ranges: list[dict[str, object]] = []
    spans: list[tuple[int, int]] = []
    patterns = [
        re.compile(r"(\d{1,2})[./](\d{1,2})[./](\d{2,4})\s*(?:a|A|À|-|–)\s*(\d{1,2})[./](\d{1,2})[./](\d{2,4})"),
        re.compile(r"(\d{1,2})[./](\d{1,2})[./](\d{2,4})\s*(?:a|A|À|-|–)\s*(\d{1,2})[./](\d{1,2})\b"),
        re.compile(r"(\d{1,2})\s*(?:a|A|À|-|–)\s*(\d{1,2})[./](\d{1,2})[./](\d{2,4})"),
    ]
    for pattern in patterns:
        for match in pattern.finditer(text):
            if any(not (match.end() <= start or match.start() >= end) for start, end in spans):
                continue
            groups = match.groups()
            if len(groups) == 6:
                start = make_date(groups[0], groups[1], groups[2])
                end = make_date(groups[3], groups[4], groups[5])
            elif len(groups) == 5:
                start = make_date(groups[0], groups[1], groups[2])
                end = make_date(groups[3], groups[4], groups[2])
            else:
                start = make_date(groups[0], groups[2], groups[3])
                end = make_date(groups[1], groups[2], groups[3])
            add_range(ranges, text, match.start(), start, end, match.group(0))
            spans.append((match.start(), match.end()))

    month_patterns = [
        re.compile(r"(\d{1,2})\s+([A-Za-zÇç]{3,9})\s+(?:a|A|À|-|–)\s+(\d{1,2})\s+([A-Za-zÇç]{3,9})\s+(\d{2,4})"),
        re.compile(r"(\d{1,2})\s+(?:a|A|À|-|–)\s+(\d{1,2})\s+([A-Za-zÇç]{3,9})\s+(\d{2,4})"),
    ]
    for pattern in month_patterns:
        for match in pattern.finditer(text):
            if any(not (match.end() <= start or match.start() >= end) for start, end in spans):
                continue
            groups = match.groups()
            if len(groups) == 5:
                start = make_month_date(groups[0], groups[1], groups[4])
                end = make_month_date(groups[2], groups[3], groups[4])
            else:
                start = make_month_date(groups[0], groups[2], groups[3])
                end = make_month_date(groups[1], groups[2], groups[3])
            add_range(ranges, text, match.start(), start, end, match.group(0))
            spans.append((match.start(), match.end()))

    operational = [r for r in ranges if not MEETING_RE.search(str(r["label"]))]
    if operational:
        ranges = operational

    unique: list[dict[str, object]] = []
    seen: set[tuple[object, object, object]] = set()
    for item in ranges:
        key = (item["inicio"], item["termino"], item["label"])
        if key not in seen:
            seen.add(key)
            unique.append(item)
    return unique


def split_icaos(raw: str) -> list[str]:
    return sorted(set(ICAO_RE.findall(raw or "")))


def load_airportsdata() -> dict[str, dict[str, object]]:
    try:
        module = importlib.import_module("airportsdata")
        load = cast(Callable[[str], dict[str, dict[str, object]]], module.load)
        return load("ICAO")
    except ModuleNotFoundError:
        return {}


def airport_city_uf(icao: str, airports: dict[str, dict[str, object]]) -> tuple[str, str]:
    if icao in AIRPORT_FALLBACK:
        return AIRPORT_FALLBACK[icao]
    item = airports.get(icao)
    if not item:
        return "", ""
    city = ascii_text(str(item.get("city") or "")).title().replace(" De ", " de ")
    uf = UF_NAMES.get(str(item.get("subd") or ""), "")
    return city, uf


def parse_area(area: str) -> tuple[str, str]:
    area_ascii = ascii_text(area)
    match = re.search(r"([A-Za-z ]+)\s*-\s*([A-Z]{2})\b", area_ascii)
    if match:
        return match.group(1).strip().title().replace(" De ", " de "), match.group(2)
    return area_ascii, ""


def categoria(cidade: str, uf: str) -> str:
    if not cidade or not uf:
        return ""
    first = cidade.split(" / ")[0]
    if first in ESPECIAIS:
        return "ESPECIAL"
    if first in CAPITAIS:
        return "CAPITAL"
    return "PADRAO"


def source_snippet(title: str, periodo: str, area: str, local: str) -> str:
    return ascii_text(f"{title}; periodo: {periodo}; area: {area}; local: {local}")[:260]


def phase_name(label: str, idx: int, total: int) -> str:
    label = ascii_text(label)
    if label and len(label) >= 3:
        label = re.sub(
            r"^(PERIODO DE EXECUCAO|PERIODO \(S\) DE EXECUCAO)\s*",
            "",
            label,
            flags=re.I,
        )
        label = label.strip(" :-")
    if not label:
        return f"fase-{idx}" if total > 1 else ""
    return label


def row_cells(row: list[object | None]) -> list[str]:
    return [clean(cell) for cell in row if clean(cell)]


def value_after_label(cells: list[str], label: str) -> str:
    text = " ".join(cells)
    match = re.search(re.escape(label), text, re.I)
    if not match:
        return ""
    value = text[match.end() :].strip(" :-")
    if value:
        return value
    for index, cell in enumerate(cells):
        if re.fullmatch(re.escape(label), cell, re.I):
            return " ".join(cells[index + 1 :]).strip(" :-")
    return ""


def find_title(lines: list[str], rows: list[list[str]]) -> str:
    for cells in rows[:8]:
        text = " ".join(cells)
        if LABEL_RE.search(text) or NOISE_RE.match(text):
            continue
        if len(text) >= 5 and not re.search(r"\d{2}[:.]\d{2}|\d{2}\.\d{2}", text):
            return text
    for line in lines[:18]:
        if LABEL_RE.search(line) or NOISE_RE.match(line):
            continue
        if len(line) >= 5 and not re.search(r"\d{2}[:.]\d{2}|\d{2}\.\d{2}", line):
            return line
    return ""


def extract_candidates(pdf_path: Path) -> list[dict[str, object]]:
    candidates: list[dict[str, object]] = []
    with PDFPLUMBER.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_number = int(page.page_number)
            if page_number < 24 or page_number > 191:
                continue
            text = page.extract_text(layout=True) or page.extract_text() or ""
            lines = [clean(line) for line in text.splitlines() if clean(line)]
            rows: list[list[str]] = []
            for table in page.extract_tables() or []:
                for row in table:
                    cells = row_cells(cast(list[object | None], row))
                    if cells:
                        rows.append(cells)
            has_labels = any(LABEL_RE.search(" ".join(row)) for row in rows[:16]) or any(
                LABEL_RE.search(line) for line in lines[:25]
            )
            if not has_labels:
                continue
            fields: dict[str, str] = {}
            for label, key in FIELD_MAP.items():
                for cells in rows[:18]:
                    value = value_after_label(cells, label)
                    if value:
                        fields[key] = value
                        break
                if key not in fields:
                    for line in lines[:30]:
                        value = value_after_label([line], label)
                        if value:
                            fields[key] = value
                            break
            if not fields.get("periodo") and page_number not in {24, 46, 99, 149, 168}:
                continue
            candidates.append(
                {
                    "page": page_number,
                    "title": fields.get("nome") or find_title(lines, rows),
                    "fields": fields,
                }
            )
    return candidates


def infer_om_from_base(mission: dict[str, object]) -> None:
    oms = list(cast(list[str], mission.get("om_destino") or []))
    if oms:
        return
    fonte = cast(dict[str, object], mission.get("fonte") or {})
    trecho = str(fonte.get("trecho") or "")
    local_part = trecho.split(" local: ", 1)[1] if " local: " in trecho else trecho
    found: list[str] = []
    for om in OM_TO_LOCAL:
        if re.search(rf"(?<![A-Z0-9]){re.escape(om)}(?![A-Z0-9])", local_part):
            found.append(om)
    diretora = str(mission.get("om_diretora") or "")
    if not found and diretora in OM_TO_LOCAL:
        found.append(diretora)
    if not found:
        return
    mission["om_destino"] = list(dict.fromkeys(found))
    if len(found) == 1:
        city, uf = OM_TO_LOCAL[found[0]]
        mission["cidade"] = city
        mission["uf"] = uf
        mission["categoria_diaria"] = categoria(city, uf)
    note = "OM destino inferida automaticamente por mapeamento de OM/base local -> cidade/UF."
    mission["observacoes"] = f"{mission.get('observacoes') or ''} {note}".strip()


def build_missions(
    candidates: list[dict[str, object]],
    airports: dict[str, dict[str, object]],
) -> list[dict[str, object]]:
    missions: list[dict[str, object]] = []
    seen_ids: dict[str, int] = {}
    for entry in candidates:
        page_value = entry["page"]
        if not isinstance(page_value, int):
            raise TypeError(f"invalid candidate page: {page_value!r}")
        page = page_value
        if page == 121:
            continue
        fields = cast(dict[str, str], entry.get("fields") or {})
        title = ascii_text(str(entry.get("title") or fields.get("nome") or ""))
        periodo = fields.get("periodo") or ""
        if not title or not periodo or ascii_text(periodo).upper() == "ASD":
            continue
        ranges = extract_ranges(periodo)
        if not ranges:
            continue
        area = fields.get("area_operacao") or ""
        local = fields.get("local_desdobramento") or ""
        icaos = split_icaos(local) or split_icaos(area)
        oms = list(dict.fromkeys(ICAO_TO_OM[icao] for icao in icaos if icao in ICAO_TO_OM))
        if icaos:
            cities_ufs = [airport_city_uf(icao, airports) for icao in icaos]
            cidade = " / ".join(dict.fromkeys(city for city, _ in cities_ufs if city))
            uf = " / ".join(dict.fromkeys(region for _, region in cities_ufs if region))
        else:
            cidade, uf = parse_area(area)
        for idx, item in enumerate(ranges, start=1):
            start = cast(date, item["inicio"])
            end = cast(date, item["termino"])
            label = phase_name(str(item["label"]), idx, len(ranges))
            desc = title if not label else f"{title} - {label}"
            base_id = slug(f"{title}-{label or idx}-{start.isoformat()}")
            count = seen_ids.get(base_id, 0)
            seen_ids[base_id] = count + 1
            mission_id = base_id if count == 0 else f"{base_id}-{count + 1}"
            notes: list[str] = []
            if oms:
                notes.append(
                    "OM destino inferida automaticamente por mapeamento "
                    "local_desdobramento_icao -> OM FAB."
                )
            if len(icaos) > 1:
                notes.append(
                    "Multiplos locais de desdobramento informados; "
                    "conferir OM/cidade ao selecionar."
                )
            mission: dict[str, object] = {
                "id": mission_id,
                "descricao": desc,
                "om_destino": oms,
                "om_diretora": ascii_text(fields.get("om_diretora") or ""),
                "om_coordenadora": ascii_text(fields.get("om_coordenadora") or ""),
                "om_executora": ascii_text(fields.get("om_executora") or ""),
                "local_desdobramento_icao": icaos,
                "cidade": cidade,
                "uf": uf,
                "categoria_diaria": categoria(cidade, uf),
                "data_inicio_oficial": start.isoformat(),
                "data_termino_oficial": end.isoformat(),
                "data_inicio_planejamento": (start - timedelta(days=1)).isoformat(),
                "data_termino_planejamento": end.isoformat(),
                "fonte": {
                    "documento": DOCUMENT_TITLE,
                    "pagina": page,
                    "trecho": source_snippet(title, periodo, area, local),
                },
                "confianca": "alta" if title and (area or icaos) else "media",
                "observacoes": " ".join(notes),
            }
            infer_om_from_base(mission)
            missions.append(mission)

    for mission in manual_portoes_missions():
        missions.append(mission)
    apply_curated_fixes(missions)
    missions.sort(key=lambda item: (str(item["data_inicio_oficial"]), str(item["id"])))
    return missions


def manual_portoes_missions() -> list[dict[str, object]]:
    missions: list[dict[str, object]] = []
    for mission_id, desc, om, city, uf, start_s, end_s, page, trecho in MANUAL_PORTOES:
        start = date.fromisoformat(start_s)
        end = date.fromisoformat(end_s)
        missions.append(
            {
                "id": mission_id,
                "descricao": desc,
                "om_destino": [om] if om else [],
                "om_diretora": "",
                "om_coordenadora": "",
                "om_executora": "",
                "local_desdobramento_icao": [],
                "cidade": city,
                "uf": uf,
                "categoria_diaria": categoria(city, uf),
                "data_inicio_oficial": start.isoformat(),
                "data_termino_oficial": end.isoformat(),
                "data_inicio_planejamento": (start - timedelta(days=1)).isoformat(),
                "data_termino_planejamento": end.isoformat(),
                "fonte": {
                    "documento": DOCUMENT_TITLE,
                    "pagina": page,
                    "trecho": ascii_text(trecho),
                },
                "confianca": "media",
                "observacoes": (
                    "Registro de Portoes Abertos/Desfile Aereo extraido de quadro resumido."
                ),
            }
        )
    return missions


def apply_curated_fixes(missions: list[dict[str, object]]) -> None:
    for mission in missions:
        if str(mission["id"]) == "avop-f-39e-2026-1-2026-05-11":
            mission["id"] = "avop-f-39e-2026-fase-1-verificacao-tecnica-2026-05-11"
            mission["descricao"] = "AVOP F-39E - Fase 1 (Verificacao Tecnica)"
            mission["om_destino"] = ["BAAN"]
            mission["local_desdobramento_icao"] = ["SBAN"]
            mission["cidade"] = "Anapolis"
            mission["uf"] = "GO"
            mission["categoria_diaria"] = "PADRAO"
            mission["confianca"] = "alta"
            mission["observacoes"] = (
                "Fases 2 e 3 aparecem como DATA ASD COMPREP na ICA e nao foram "
                "cadastradas como missoes datadas."
            )


def build_catalog(pdf_path: Path) -> dict[str, object]:
    candidates = extract_candidates(pdf_path)
    missions = build_missions(candidates, load_airportsdata())
    return {
        "schema_version": 2,
        "documento": {
            "titulo": DOCUMENT_TITLE,
            "arquivo_origem": pdf_path.name,
            "paginas": count_pages(pdf_path),
            "observacoes": (
                "Catalogo exaustivo preliminar extraido programaticamente com pdfplumber "
                "e curadoria automatica de ICAO/OM."
            ),
        },
        "regras_catalogo": {
            "datas_oficiais": (
                "Campos data_inicio_oficial/data_termino_oficial preservam o periodo "
                "de execucao da ICA."
            ),
            "datas_planejamento": (
                "Campos data_inicio_planejamento/data_termino_planejamento aplicam D-1 "
                "no inicio para deslocamento; termino igual ao oficial."
            ),
            "fases": (
                "Fases/etapas com periodos proprios sao registradas como missoes separadas."
            ),
            "icao": (
                "local_desdobramento_icao armazena designativos ICAO de "
                "aerodromos/localidades, separado de OM."
            ),
            "om_destino": (
                "Inferida automaticamente quando o ICAO possui mapeamento explicito "
                "para base/OM FAB."
            ),
        },
        "mapeamento_icao_om": ICAO_TO_OM,
        "missoes": missions,
    }


def count_pages(pdf_path: Path) -> int:
    with PDFPLUMBER.open(pdf_path) as pdf:
        return len(pdf.pages)


def write_catalog(catalog: dict[str, object], output_path: Path) -> None:
    output_path.write_text(
        yaml.dump(
            catalog,
            Dumper=NoAliasDumper,
            allow_unicode=False,
            default_flow_style=False,
            sort_keys=False,
            width=100,
        ),
        encoding="utf-8",
    )


def validate_catalog(catalog: dict[str, object]) -> None:
    missions = cast(list[dict[str, object]], catalog["missoes"])
    ids = [str(mission["id"]) for mission in missions]
    if len(ids) != len(set(ids)):
        raise ValueError("catalog contains duplicated mission ids")
    for mission in missions:
        start = date.fromisoformat(str(mission["data_inicio_oficial"]))
        end = date.fromisoformat(str(mission["data_termino_oficial"]))
        plan_start = date.fromisoformat(str(mission["data_inicio_planejamento"]))
        plan_end = date.fromisoformat(str(mission["data_termino_planejamento"]))
        if start > end or plan_start > plan_end:
            raise ValueError(f"invalid date range: {mission['id']}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf", type=Path, default=DEFAULT_PDF, help="ICA 55-87 PDF path")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="YAML output path")
    parser.add_argument(
        "--candidates-json",
        type=Path,
        default=None,
        help="Optional path to write intermediate ficha candidates JSON",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    pdf_path = cast(Path, args.pdf)
    output_path = cast(Path, args.output)
    catalog = build_catalog(pdf_path)
    validate_catalog(catalog)
    if args.candidates_json is not None:
        candidates_path = cast(Path, args.candidates_json)
        candidates_path.write_text(
            json.dumps(extract_candidates(pdf_path), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    write_catalog(catalog, output_path)
    missions = cast(list[dict[str, object]], catalog["missoes"])
    print(f"wrote={output_path}")
    print(f"missions={len(missions)}")


if __name__ == "__main__":
    main()
