"""Configurações institucionais: texto para PDF e ODS."""

from __future__ import annotations

import os

# Lê de variáveis de ambiente se disponíveis; senão usa default genérico.
# Configure COMISSIONAER_DIRETOR_NOME e COMISSIONAER_DIRETOR_CARGO no .env.
DIRETOR_NOME: str = os.getenv(
    "COMISSIONAER_DIRETOR_NOME",
    "NOME DO DIRETOR — configure COMISSIONAER_DIRETOR_NOME",
)
DIRETOR_CARGO: str = os.getenv(
    "COMISSIONAER_DIRETOR_CARGO",
    "Diretor do IAOp",
)
