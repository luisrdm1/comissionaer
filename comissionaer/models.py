"""Modelos de domínio: enums, dataclasses e cálculos de propriedade."""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from enum import Enum


class Posto(Enum):
    SEGUNDO_TENENTE = "2º Ten"
    PRIMEIRO_TENENTE = "1º Ten"
    CAPITAO = "Cap"
    MAJOR = "Maj"
    TENENTE_CORONEL = "TC"
    CORONEL = "Cel"
    BRIGADEIRO = "Brig"
    MAJOR_BRIGADEIRO = "Maj Brig"
    TENENTE_BRIGADEIRO = "Ten Brig"


class Habilitacao(Enum):
    FORMACAO = "Formação (12%) — AFA / EEAR / EAGS"
    ESPECIALIZACAO = "Especialização (27%) — Piloto de Caça, Paraquedista, CTA…"
    APERFEICOAMENTO = "Aperfeiçoamento (45%) — CAP / CAS / ITA (CEAAE, CASSA, CEAO…)"
    ALTOS_II = "Altos Estudos Cat. II — Mestrado (68%)"
    ALTOS_I = "Altos Estudos Cat. I — Doutorado / ECEMAR (73%)"


class CategoriaDiaria(Enum):
    ESPECIAL = "Especial — Brasília, Manaus, Rio de Janeiro, São Paulo (R$ 425,00)"
    CAPITAL = "Capital de estado (R$ 380,00)"
    PADRAO = "Demais municípios (R$ 335,00)"


class DuracaoComissionamento(Enum):
    CURTO = "15 dias a 3 meses"
    LONGO = "Acima de 3 meses até 12 meses"


class Dependentes(Enum):
    SIM = True
    NAO = False


@dataclass
class Missao:
    descricao: str
    om_destino: str
    cidade: str
    uf: str
    categoria_diaria: CategoriaDiaria
    data_inicio: date
    data_termino: date
    num_deslocamentos: int = 1


@dataclass
class BaseRemuneratoria:
    soldo: Decimal
    adicional_habilitacao: Decimal
    adicional_militar: Decimal
    adicional_disponibilidade: Decimal
    adicional_compensacao_organica: Decimal

    @property
    def total(self) -> Decimal:
        return (
            self.soldo
            + self.adicional_habilitacao
            + self.adicional_militar
            + self.adicional_disponibilidade
            + self.adicional_compensacao_organica
        )


@dataclass
class Militar:
    nome: str
    posto: Posto
    habilitacao: Habilitacao
    dependentes: Dependentes
    pct_compensacao_organica: Decimal  # 0 se não aplicável
    duracao: DuracaoComissionamento = DuracaoComissionamento.LONGO
    # Situação no encerramento — preencher só se houver promoção ou nova habilitação
    # (Decreto 4.307/2002 art. 56: ajuda de volta usa remuneração da data de encerramento)
    posto_encerramento: Posto | None = None
    habilitacao_encerramento: Habilitacao | None = None
    pct_compensacao_organica_encerramento: Decimal | None = None


@dataclass
class ResultadoMissao:
    missao: Missao
    dias: int
    valor_diaria_unitario: Decimal
    total_diarias: Decimal
    total_deslocamento: Decimal

    @property
    def total(self) -> Decimal:
        return self.total_diarias + self.total_deslocamento


@dataclass
class Calculo:
    militar: Militar
    base: BaseRemuneratoria  # remuneração na abertura
    base_encerramento: BaseRemuneratoria  # remuneração no encerramento (pode ser == base)
    fator_ida: Decimal
    fator_volta: Decimal
    missoes: list[ResultadoMissao] = field(default_factory=list[ResultadoMissao])

    @property
    def mudanca_encerramento(self) -> bool:
        return (
            self.militar.posto_encerramento is not None
            or self.militar.habilitacao_encerramento is not None
            or self.militar.pct_compensacao_organica_encerramento is not None
        )

    @property
    def total_ajuda_custo(self) -> Decimal:
        """Decreto 4.307/2002 art. 56 — ida usa base abertura, volta usa base encerramento."""
        return self.base.total * self.fator_ida + self.base_encerramento.total * self.fator_volta

    @property
    def total_dias(self) -> int:
        return sum((m.dias for m in self.missoes), 0)

    @property
    def total_diarias(self) -> Decimal:
        return sum((m.total_diarias for m in self.missoes), Decimal("0"))

    @property
    def total_deslocamentos(self) -> Decimal:
        return sum((m.total_deslocamento for m in self.missoes), Decimal("0"))

    @property
    def total_missoes(self) -> Decimal:
        return self.total_diarias + self.total_deslocamentos

    @property
    def economicidade(self) -> Decimal:
        """Positivo = missões custam mais que ajuda de custo → comissionamento justificado."""
        return self.total_missoes - self.total_ajuda_custo
