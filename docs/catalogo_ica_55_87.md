# Catalogo ICA 55-87/2026

Este documento registra como o catalogo `comissionaer/data/missoes_ica_55_87_2026.yaml` foi criado e como reproduzir a extracao.

## Objetivo

Gerar um catalogo estruturado e buscavel das atividades anuais da ICA 55-87/2026, preservando fonte, pagina, datas oficiais e campos necessarios para planejamento de comissionamento.

## Arquivos

- PDF fonte: `../ICA 55-87 - Programa de Atividades Operacionais do COMPREP - 2026.pdf`
- Catalogo gerado: `comissionaer/data/missoes_ica_55_87_2026.yaml`
- Script de curadoria: `tools/extract_ica_55_87_catalog.py`

## Reproducao

O script usa `pdfplumber` e `pyyaml`, ja presentes no projeto. Para enriquecer cidade/UF por ICAO, pode usar `airportsdata` como dependencia temporaria sem adiciona-la ao runtime do pacote.

```powershell
uv run --with airportsdata python tools/extract_ica_55_87_catalog.py
```

Para salvar candidatos intermediarios fora do repositorio:

```powershell
uv run --with airportsdata python tools/extract_ica_55_87_catalog.py --candidates-json "C:\Users\molon\AppData\Local\Temp\opencode\ica_55_87_candidates.json"
```

## Metodologia

1. O script percorre apenas as paginas 24 a 191, onde ficam anexos com fichas e eventos operacionais.
2. Cada pagina e extraida com `pdfplumber` usando texto com layout e tabelas.
3. Uma pagina vira candidata quando contem rotulos como `PERIODO DE EXECUCAO`, `OM EXECUTORA`, `AREA DE OPERACAO` ou `LOCAL DE DESDOBRAMENTO`.
4. As datas operacionais sao extraidas de `PERIODO DE EXECUCAO` e reunioes de planejamento (`IPC`, `MPC`, `FPC`, `CDC`) sao descartadas quando ha periodo operacional no mesmo campo.
5. Fases com periodos proprios viram missoes separadas.
6. `local_desdobramento_icao` guarda ICAO de aerodromo/localidade, separado de OM.
7. `om_destino` e inferida por mapeamento explicito `ICAO -> OM FAB`, mantido no proprio YAML e no script.
8. `data_inicio_oficial` e `data_termino_oficial` preservam a ICA.
9. `data_inicio_planejamento` aplica D-1 para deslocamento; `data_termino_planejamento` fica igual ao termino oficial.

## Curadoria Manual Registrada

- Portoes abertos e desfiles das paginas 184-185 com datas em quadros resumidos sao incluidos em uma lista manual versionada no script.
- `AVOP F-39E - 2026` teve a Fase 1 cadastrada como `AVOP F-39E - Fase 1 (Verificacao Tecnica)`, com `SBAN -> BAAN`.
- As fases 2 e 3 do `AVOP F-39E` aparecem como `DATA ASD COMPREP`; elas nao sao cadastradas como missoes datadas.
- Entradas com `DATA ASD` sem data oficial nao sao inventadas.

## Validacao

Depois de regenerar o catalogo, executar:

```powershell
uv run pytest
uv run pyright
uv run ruff check .
```

Validacoes internas do script:

- IDs unicos.
- Datas ISO validas.
- Intervalos oficiais e de planejamento coerentes.

## Limites Conhecidos

- A extracao e heuristica porque a ICA mistura tabelas, texto corrido e quadros resumidos.
- Algumas fichas tem multiplos locais em uma unica linha; nesses casos o catalogo preserva listas em `local_desdobramento_icao` e `om_destino`.
- `airportsdata` e usado apenas como apoio de curadoria; o mapeamento essencial ICAO/OM fica versionado no YAML e no script.
