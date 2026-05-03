"""Migra missoes_ica_55_87_2026.yaml de schema_version 2 para 3.

Remove o campo `descricao` e adiciona `tipo`, `nome`, `fase`, `ano`
para cada entrada. Execute com `uv run python migrate_v3.py`.
"""

import sys
from pathlib import Path

import yaml

# id → (tipo, nome, fase)  — ano fixo = 2026 para toda esta ICA
LOOKUP: dict[str, tuple[str, str, str | None]] = {
    "exercicio-tecnico-lancamento-aereo-kc-390-fase-1-2026-02-02": (
        "EXTEC",
        "Lançamento Aéreo KC-390",
        "Fase 1",
    ),
    "desfile-aereo-platinas-epcar-2026": ("DESFILE", "Entrega de Platinas do 1º Esquadrão", None),
    "operacao-thor-fx-2-periodo-1-p1-26-01-2026-06-02-2026-com-semana-de-reserva-2026-02-09": (
        "OPERACAO",
        "Thor FX-2",
        "Período 1 (P1)",
    ),
    "exercicio-operacional-tapio-sentinel-26-br-2026-02-10": ("EXOP", "Tapio Sentinel", "IPC (BR)"),
    "avaop-carp-do-fms-do-c-105-etapa-1-precursora-2026-02-22": (
        "AVAOP",
        "CARP do FMS do C-105",
        "Etapa 1 (Precursora)",
    ),
    "avaop-ccdp-do-kc-390-etapa-1-precursora-2026-02-22": (
        "AVAOP",
        "CCDP do KC-390",
        "Etapa 1 (Precursora)",
    ),
    "avaop-mx-15-do-r-99-etapa-1-precursora-2026-02-22": (
        "AVAOP",
        "MX-15 do R-99",
        "Etapa 1 (Precursora)",
    ),
    "exercicio-tecnico-cabra-da-peste-pceo-tr-fase-1-instrutores-2026-02-22": (
        "EXTEC",
        "Cabra da Peste (PCEO-TR)",
        "Fase 1 (Instrutores)",
    ),
    "avop-th-x-1-2026-02-23": ("AVOP", "TH-X", None),
    "exercicio-operacional-ivr-25-exercicio-2026-03-02": ("EXOP", "IVR", "Única"),
    "exercicio-tecnico-assaet-tracaja-para-sar-1-2026-03-02": (
        "EXTEC",
        "Assaet Tracajá Para-SAR",
        "Única",
    ),
    "exercicio-tecnico-lancamento-aereo-kc-390-25-baan-fase-3-2026-03-02": (
        "EXTEC",
        "Lançamento Aéreo KC-390",
        "Fase 3",
    ),
    "exercicio-tecnico-lancamento-aereo-kc-390-26-baaf-fase-2-2026-03-02": (
        "EXTEC",
        "Lançamento Aéreo KC-390",
        "Fase 2",
    ),
    "exercicio-tecnico-bvr-pampa-caca-f-5m-fase1-2026-03-09": (
        "EXTEC",
        "BVR Pampa-Caça F-5M",
        "Fase 1",
    ),
    "instrucao-de-salto-de-emergencia-isem-e-operacoes-aeroterrestres-opae-1-2026-03-09": (
        "INSTRUCAO",
        "de Salto de Emergência (ISEM) e Operações Aeroterrestres (OPAE)",
        None,
    ),
    "exercicio-tecnico-pista-critica-c-98-fase-1-2026-03-16": (
        "EXTEC",
        "Pista Crítica C-98",
        "Fase 1",
    ),
    "exercicio-tecnico-tiro-aereo-3o-grupo-1-2026-03-16": ("EXTEC", "Tiro Aéreo 3º Grupo", "Única"),
    "exercicio-tecnico-icamento-no-mar-puma-1-2026-03-23": (
        "EXTEC",
        "Içamento no Mar Puma",
        "Única",
    ),
    "operacao-iris-2026-fase-1-2026-03-23": ("OPERACAO", "Iris 2026", "Fase 1"),
    "exercicio-tecnico-formacao-kc-390-1-2026-04-06": ("EXTEC", "Formação KC-390", "Única"),
    "exercicio-tecnico-icamento-no-mar-pantera-1-2026-04-06": (
        "EXTEC",
        "Içamento no Mar Pantera",
        "Única",
    ),
    "exercicio-tecnico-raio-2026-exercicio-2026-04-06": ("EXTEC", "Raio", "Única"),
    "exercicio-tecnico-lancamento-aereo-c-105-1-2026-04-12": (
        "EXTEC",
        "Lançamento Aéreo C-105",
        "Única",
    ),
    "exercicio-tecnico-pista-critica-c-97-1-2026-04-15": ("EXTEC", "Pista Crítica C-97", "Única"),
    "avaop-carp-do-fms-do-c-105-2026-etapa-2-execucao-2026-04-19": (
        "AVAOP",
        "CARP do FMS do C-105",
        "Etapa 2 (Execução)",
    ),
    "avaop-ccdp-do-kc-390-2026-etapa-2-execucao-2026-04-19": (
        "AVAOP",
        "CCDP do KC-390",
        "Etapa 2 (Execução)",
    ),
    "avaop-mx-15-do-r-99-2026-etapa-2-execucao-2026-04-19": (
        "AVAOP",
        "MX-15 do R-99",
        "Etapa 2 (Execução)",
    ),
    "reuniao-da-aviacao-de-caca-1-2026-04-19": ("REUNIAO", "da Aviação de Caça", None),
    "exercicio-operacional-evam-dbnqr-26-videoconferencia-exercicio-2026-04-27": (
        "EXOP",
        "EVAM DBNQR",
        "Única (Videoconferência)",
    ),
    "exercicio-tecnico-tiro-aereo-pantera-1-2026-04-27": ("EXTEC", "Tiro Aéreo Pantera", "Única"),
    "exercicio-tecnico-wvr-1-2026-04-27": ("EXTEC", "WVR", "Única"),
    "exercicio-tecnico-interceptacao-a-29-fase-1-2026-05-05": (
        "EXTEC",
        "Interceptação A-29",
        "Fase 1",
    ),
    "exercicio-tecnico-soturno-negro-1-2026-05-10": ("EXTEC", "Soturno Negro", "Única"),
    "avop-f-39e-2026-fase-1-verificacao-tecnica-2026-05-11": (
        "AVOP",
        "F-39E",
        "Fase 1 (Verificação Técnica)",
    ),
    "exercicio-conjunto-escudo-tinia-26-exercicio-2026-05-11": ("EXCON", "Escudo-Tinia", "Única"),
    "exercicio-tecnico-arcanjo-missao-de-paz-1-2026-05-11": (
        "EXTEC",
        "Arcanjo (Missão de Paz)",
        "Única",
    ),
    "exercicio-tecnico-noturno-1-gavca-1-2026-05-11": ("EXTEC", "Noturno 1 GAVCA", "Única"),
    "exercicio-operacional-tapio-sentinel-26-br-2026-05-12": ("EXOP", "Tapio Sentinel", "MPC (BR)"),
    "portoes-abertos-musal-air-show-2026": (
        "PORTOES",
        "MUSAL Air Show e Dia Internacional de Museus",
        None,
    ),
    "exercicio-tecnico-sar-001-1-2026-05-19": ("EXTEC", "SAR 001", "Única"),
    "reuniao-da-aviacao-de-asas-rotativas-1-2026-05-19": (
        "REUNIAO",
        "da Aviação de Asas Rotativas",
        None,
    ),
    "reuniao-da-aviacao-de-patrulha-1-2026-05-21": ("REUNIAO", "da Aviação de Patrulha", None),
    "exercicio-tecnico-defensor-2026-exercicio-2026-05-28": ("EXTEC", "Defensor", "Única"),
    "exercicio-tecnico-interceptacao-a-29-26-fase-2-2026-05-30": (
        "EXTEC",
        "Interceptação A-29",
        "Fase 2",
    ),
    "ew-f-x2-2026-ew-2026-06-08": ("EXTEC", "EW F-X2", "Única"),  # tipo provisional — verificar ICA
    "exercicio-operacional-salto-livre-operacional-26-vc-fase-unica-2026-06-08": (
        "EXOP",
        "Salto Livre Operacional",
        "Única (VC)",
    ),
    "exercicio-tecnico-selva-pelicano-1-2026-06-08": ("EXTEC", "Selva Pelicano", "Única"),
    "reuniao-da-aviacao-de-transporte-1-2026-06-09": ("REUNIAO", "da Aviação de Transporte", None),
    "desfile-aereo-can-dia-aviacao-transporte-2026": (
        "DESFILE",
        "Cerimônia do CAN/Dia da Aviação de Transporte",
        None,
    ),
    "exercicio-tecnico-receiver-opfm-kc-390-fase-1-2026-06-15": (
        "EXTEC",
        "Receiver OPFM KC-390",
        "Fase 1",
    ),
    "exercicio-tecnico-pista-critica-c-98-26-fase-2-2026-06-17": (
        "EXTEC",
        "Pista Crítica C-98",
        "Fase 2",
    ),
    "exercicio-tecnico-receiver-opfm-kc-390-26-fase-2-2026-06-20": (
        "EXTEC",
        "Receiver OPFM KC-390",
        "Fase 2",
    ),
    "reuniao-da-busca-e-salvamento-reusar-1-2026-06-22": (
        "REUNIAO",
        "de Busca e Salvamento (REUSAR)",
        None,
    ),
    "reuniao-da-aviacao-de-reconhecimento-1-2026-06-23": (
        "REUNIAO",
        "da Aviação de Reconhecimento",
        None,
    ),
    "exercicio-operacional-tapio-sentinel-26-br-2026-06-30": ("EXOP", "Tapio Sentinel", "FPC (BR)"),
    "exercicio-tecnico-lancamento-aereo-kc-390-25-baaf-fase-4-2026-07-06": (
        "EXTEC",
        "Lançamento Aéreo KC-390",
        "Fase 4",
    ),
    "salitre-2026-1-2026-07-06": ("EXCON", "SALITRE", "Única"),
    "exercicio-tecnico-bvr-pampa-caca-f-5m-fase-2-2026-07-13": (
        "EXTEC",
        "BVR Pampa-Caça F-5M",
        "Fase 2",
    ),
    "desfile-aereo-santos-dumont-musal-2026": (
        "DESFILE",
        "Aniversário de Santos Dumont e do MUSAL",
        None,
    ),
    "reuniao-da-infantaria-da-aeronautica-1-2026-07-27": (
        "REUNIAO",
        "da Infantaria da Aeronáutica",
        None,
    ),
    "avaop-irst-do-f-39-etapa-1-precursora-2026-08-02": (
        "AVAOP",
        "IRST do F-39",
        "Etapa 1 (Precursora)",
    ),
    "avaop-rdr-1600-modo-search-do-h-36-fase-1-precursora-2026-08-02": (
        "AVAOP",
        "RDR-1600 Modo Search do H-36",
        "Fase 1 (Precursora)",
    ),
    "avaop-sar-do-lessonia-etapa-1-precursora-2026-08-02": (
        "AVAOP",
        "SAR do Lessônia",
        "Etapa 1 (Precursora)",
    ),
    "avaop-comunicacao-hf-integracao-2026-fase-2-kc-390-2026-08-03": (
        "AVAOP",
        "Comunicação HF – Integração",
        "Fase 2 (KC-390)",
    ),
    "exercicio-tecnico-trinitro-fase-1-2026-08-03": ("EXTEC", "Trinitro", "Fase 1"),
    "exercicio-tecnico-noe-gaviao-fase-1-2026-08-10": ("EXTEC", "NOE Gavião", "Fase 1"),
    "exercicio-operacional-tapio-sentinel-26-exercicio-fase-warrior-2026-08-14": (
        "EXOP",
        "Tapio Sentinel",
        "Fase Warrior",
    ),
    "exercicio-tecnico-lancamento-aereo-kc-390-25-bacg-fase-5-2026-08-17": (
        "EXTEC",
        "Lançamento Aéreo KC-390",
        "Fase 5",
    ),
    "exercicio-tecnico-reop-lacador-26-reop-sbpk-2026-08-17": ("EXTEC", "REOP Laçador", "Única"),
    "exercicio-tecnico-retorno-a-pista-c-98-1-2026-08-17": (
        "EXTEC",
        "Retorno à Pista C-98",
        "Única",
    ),
    "exercicio-tecnico-rumba-ivr-fase-teorica-2026-08-17": ("EXTEC", "Rumba IVR", "Fase Teórica"),
    "radar-f-x2-2026-1-2026-08-17": (
        "EXTEC",
        "Radar F-X2",
        "Única",
    ),  # tipo provisional — verificar ICA
    "exercicio-tecnico-bvr-pampa-caca-f-5m-e-fase-3-2026-08-31": (
        "EXTEC",
        "BVR Pampa-Caça F-5M",
        "Fase 3",
    ),
    "exercicio-tecnico-rumba-ivr-26-fase-1-2026-08-31": ("EXTEC", "Rumba IVR", "Fase 1"),
    "exercicio-tecnico-cabra-da-peste-pceo-tr-26-fase-2-estagiarios-2026-09-04": (
        "EXTEC",
        "Cabra da Peste (PCEO-TR)",
        "Fase 2 (Estagiários)",
    ),
    "operacao-semana-da-patria-md-1-2026-09-04": ("OPERACAO", "Semana da Pátria (MD)", None),
    "exercicio-tecnico-noe-falcao-1-2026-09-07": ("EXTEC", "NOE Falcão", "Única"),
    "exercicio-tecnico-trinitro-26-fase-2-2026-09-07": ("EXTEC", "Trinitro", "Fase 2"),
    "exercicio-tecnico-noe-gaviao-2026-fase-2-2026-09-08": ("EXTEC", "NOE Gavião", "Fase 2"),
    "exercicio-tecnico-pista-critica-nvg-c-105-fase-sbua-2026-09-08": (
        "EXTEC",
        "Pista Crítica/NVG C-105",
        "Fase SBUA",
    ),
    "desfile-aereo-90-aniversario-babe-2026": (
        "DESFILE",
        "90º Aniversário da Base Aérea de Belém",
        None,
    ),
    "exercicio-tecnico-lancamento-aereo-kc-390-26-baaf-fase-6-2026-09-09": (
        "EXTEC",
        "Lançamento Aéreo KC-390",
        "Fase 6",
    ),
    "exercicio-operacional-tapio-sentinel-2026-fase-rescue-2026-09-11": (
        "EXOP",
        "Tapio Sentinel",
        "Fase Rescue",
    ),
    "operacao-thor-fx-2-026-06-02-2026-com-semana-de-reserva-09-02-2026-a-13-02-2026-periodo-2-p2-2026-09-14": (
        "OPERACAO",
        "Thor FX-2",
        "Período 2 (P2)",
    ),
    "desfile-aereo-eduardo-gomes-2026": (
        "DESFILE",
        "130º Aniversário de Nascimento do Marechal Eduardo Gomes",
        None,
    ),
    "sarex-2026-1-2026-09-21": ("EXCON", "SAREX", "Única"),
    "operacoes-aeromoveis-1-2026-09-27": ("OPERACAO", "Aeromóveis", None),
    "operacao-iris-2026-e-fase-2-2026-09-28": ("OPERACAO", "Iris 2026", "Fase 2"),
    "operacao-thor-fx-2-02-2026-a-13-02-2026-periodo-2-p2-14-09-2026-25-09-2026-com-semana-reserva-2026-09-28": (
        "OPERACAO",
        "Thor FX-2",
        "Período 2 (P2) – Semana de Reserva",
    ),
    "avaop-irst-do-f-39-2026-etapa-2-execucao-2026-10-04": (
        "AVAOP",
        "IRST do F-39",
        "Etapa 2 (Execução)",
    ),
    "avaop-rdr-1600-modo-search-do-h-36-2026-fase-2-execucao-2026-10-04": (
        "AVAOP",
        "RDR-1600 Modo Search do H-36",
        "Fase 2 (Execução)",
    ),
    "avaop-sar-do-lessonia-2026-etapa-2-execucao-2026-10-04": (
        "AVAOP",
        "SAR do Lessônia",
        "Etapa 2 (Execução)",
    ),
    "exercicio-tecnico-rumba-ivr-26-fase-2-2026-10-05": ("EXTEC", "Rumba IVR", "Fase 2"),
    "exercicio-tecnico-pista-critica-nvg-c-105-26-fase-sbtt-2026-10-11": (
        "EXTEC",
        "Pista Crítica/NVG C-105",
        "Fase SBTT",
    ),
    "exercicio-tecnico-ar-solo-f-5m-1-2026-10-13": ("EXTEC", "AR-Solo F-5M", "Única"),
    "exercicio-tecnico-revo-ca-1-2026-10-13": ("EXTEC", "REVO-CA", "Única"),
    "exercicio-tecnico-maffs-1-2026-10-19": ("EXTEC", "MAFFS", "Única"),
    "exercicio-operacional-nuntius-26-vc-exercicio-preparacao-2026-10-26": (
        "EXOP",
        "Nuntius",
        "Preparação (VC)",
    ),
    "exercicio-operacional-carranca-26-exercicio-2026-10-29": ("EXOP", "Carranca", "Única"),
    "exercicio-operacional-nuntius-26-exercicio-fase-1-parte-teorica-2026-11-01": (
        "EXOP",
        "Nuntius",
        "Fase 1 (Parte Teórica)",
    ),
    "exercicio-operacional-nuntius-26-exercicio-fase-2-parte-pratica-2026-11-12": (
        "EXOP",
        "Nuntius",
        "Fase 2 (Parte Prática)",
    ),
    "desfile-aereo-cpcar-2026": (
        "DESFILE",
        "Conclusão do Curso Preparatório de Cadetes do Ar",
        None,
    ),
}


def migrar_missao(m: dict) -> dict:  # type: ignore[type-arg]
    missao_id = m["id"]
    if missao_id not in LOOKUP:
        print(f"ERRO: id sem entrada no lookup: {missao_id}", file=sys.stderr)
        sys.exit(1)

    tipo, nome, fase = LOOKUP[missao_id]

    # dict em Python 3.7+ preserva ordem de inserção
    novo: dict = {}  # type: ignore[type-arg]
    novo["id"] = missao_id
    novo["tipo"] = tipo
    novo["nome"] = nome
    novo["fase"] = fase  # None vira `null` no YAML — explícito é melhor
    novo["ano"] = 2026
    for k, v in m.items():
        if k not in ("id", "descricao"):
            novo[k] = v
    return novo


def main() -> None:
    yaml_path = Path("comissionaer/data/missoes_ica_55_87_2026.yaml")
    with yaml_path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)

    total = len(data["missoes"])
    data["schema_version"] = 3
    data["missoes"] = [migrar_missao(m) for m in data["missoes"]]

    with yaml_path.open("w", encoding="utf-8", newline="\n") as f:
        yaml.dump(
            data,
            f,
            allow_unicode=True,
            default_flow_style=False,
            sort_keys=False,
            width=120,
        )

    print(f"OK — {total} missões migradas para schema_version 3.")
    print("Verificando lookup completo...")
    ids_yaml = {m["id"] for m in yaml.safe_load(yaml_path.read_text(encoding="utf-8"))["missoes"]}
    ids_lookup = set(LOOKUP.keys())
    extra = ids_lookup - ids_yaml
    faltam = ids_yaml - ids_lookup
    if extra:
        print(f"AVISO — ids no lookup mas não no YAML: {extra}", file=sys.stderr)
    if faltam:
        print(f"AVISO — ids no YAML sem entrada no lookup: {faltam}", file=sys.stderr)
    if not extra and not faltam:
        print("Lookup 100% cobrindo o YAML.")


if __name__ == "__main__":
    main()
