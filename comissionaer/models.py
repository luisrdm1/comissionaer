"""Modelos de domínio: enums, dataclasses e cálculos de propriedade."""

import calendar
from dataclasses import dataclass, field
from datetime import date, timedelta
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
    SUBOFICIAL = "SO"
    PRIMEIRO_SARGENTO = "1º Sgt"
    SEGUNDO_SARGENTO = "2º Sgt"
    TERCEIRO_SARGENTO = "3º Sgt"
    CABO = "Cb"
    SOLDADO = "Sd"


class Habilitacao(Enum):
    FORMACAO = "Formação (12%) — AFA / EEAR / EAGS"
    ESPECIALIZACAO = "Especialização (27%) — Piloto de Caça, Paraquedista, CTA…"
    APERFEICOAMENTO = "Aperfeiçoamento (45%) — CAP / CAS / ITA (CEAAE, CASSA, CEAO…)"
    ALTOS_II = "Altos Estudos Cat. II — Mestrado (68%)"
    ALTOS_I = "Altos Estudos Cat. I — Doutorado / ECEMAR (73%)"


class TierDiaria(Enum):
    OFICIAL_GENERAL = "Oficial General"
    OFICIAL_SUPERIOR = "Oficial Superior"
    OFICIAL_SUBALTERNO = "Oficial Intermediário/Subalterno"
    PRACA_GRADUADA = "Praça Graduada (SO/Sgt)"
    PRACA = "Praça (Cb/Sd)"


TIER_DIARIA: dict[Posto, TierDiaria] = {
    Posto.SEGUNDO_TENENTE: TierDiaria.OFICIAL_SUBALTERNO,
    Posto.PRIMEIRO_TENENTE: TierDiaria.OFICIAL_SUBALTERNO,
    Posto.CAPITAO: TierDiaria.OFICIAL_SUBALTERNO,
    Posto.MAJOR: TierDiaria.OFICIAL_SUPERIOR,
    Posto.TENENTE_CORONEL: TierDiaria.OFICIAL_SUPERIOR,
    Posto.CORONEL: TierDiaria.OFICIAL_SUPERIOR,
    Posto.BRIGADEIRO: TierDiaria.OFICIAL_GENERAL,
    Posto.MAJOR_BRIGADEIRO: TierDiaria.OFICIAL_GENERAL,
    Posto.TENENTE_BRIGADEIRO: TierDiaria.OFICIAL_GENERAL,
    Posto.SUBOFICIAL: TierDiaria.PRACA_GRADUADA,
    Posto.PRIMEIRO_SARGENTO: TierDiaria.PRACA_GRADUADA,
    Posto.SEGUNDO_SARGENTO: TierDiaria.PRACA_GRADUADA,
    Posto.TERCEIRO_SARGENTO: TierDiaria.PRACA_GRADUADA,
    Posto.CABO: TierDiaria.PRACA,
    Posto.SOLDADO: TierDiaria.PRACA,
}


class CategoriaDiaria(Enum):
    ESPECIAL = "Especial — Brasília, Manaus, Rio de Janeiro, São Paulo"
    CAPITAL = "Capital de estado"
    PADRAO = "Demais municípios"


class FaixaAjudaCusto(Enum):
    SEM_DESLIGAMENTO_ATE_15_DIAS = "Comissão sem desligamento até 15 dias"
    SEM_DESLIGAMENTO_15_DIAS_A_3_MESES = (
        "Comissão sem desligamento superior a 15 dias e até 3 meses"
    )
    SEM_DESLIGAMENTO_ACIMA_3_MESES = "Comissão sem desligamento superior a 3 meses"


class Dependentes(Enum):
    SIM = True
    NAO = False


_ORDEM_PROMOCAO: tuple[Posto, ...] = (
    Posto.SOLDADO,
    Posto.CABO,
    Posto.TERCEIRO_SARGENTO,
    Posto.SEGUNDO_SARGENTO,
    Posto.PRIMEIRO_SARGENTO,
    Posto.SUBOFICIAL,
    Posto.SEGUNDO_TENENTE,
    Posto.PRIMEIRO_TENENTE,
    Posto.CAPITAO,
    Posto.MAJOR,
    Posto.TENENTE_CORONEL,
    Posto.CORONEL,
    Posto.BRIGADEIRO,
    Posto.MAJOR_BRIGADEIRO,
    Posto.TENENTE_BRIGADEIRO,
)


def proximo_posto(posto: Posto) -> Posto | None:
    indice = _ORDEM_PROMOCAO.index(posto)
    if indice == len(_ORDEM_PROMOCAO) - 1:
        return None
    return _ORDEM_PROMOCAO[indice + 1]


def _somar_meses(inicio: date, meses: int) -> date:
    month_index = inicio.month - 1 + meses
    year = inicio.year + month_index // 12
    month = month_index % 12 + 1
    day = min(inicio.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def _limite_meses_inclusivo(inicio: date, meses: int) -> date:
    return _somar_meses(inicio, meses) - timedelta(days=1)


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


def dias_missoes(missoes: list[Missao]) -> int:
    return sum(((missao.data_termino - missao.data_inicio).days + 1 for missao in missoes), 0)


def periodo_missoes(missoes: list[Missao]) -> tuple[date, date]:
    if not missoes:
        raise ValueError("Não há missões para derivar o período do comissionamento.")
    for missao in missoes:
        if missao.data_termino < missao.data_inicio:
            raise ValueError("Missão com data de término anterior ao início.")
    return (
        min(missao.data_inicio for missao in missoes),
        max(missao.data_termino for missao in missoes),
    )


def dias_periodo(inicio: date, termino: date) -> int:
    return (termino - inicio).days + 1


def classificar_ajuda_custo(inicio: date, termino: date) -> FaixaAjudaCusto:
    if termino < inicio:
        raise ValueError("Data de término do comissionamento anterior ao início.")
    if dias_periodo(inicio, termino) <= 15:
        return FaixaAjudaCusto.SEM_DESLIGAMENTO_ATE_15_DIAS
    if termino <= _limite_meses_inclusivo(inicio, 3):
        return FaixaAjudaCusto.SEM_DESLIGAMENTO_15_DIAS_A_3_MESES
    return FaixaAjudaCusto.SEM_DESLIGAMENTO_ACIMA_3_MESES


def classificar_ajuda_custo_por_dias(total_dias: int) -> FaixaAjudaCusto:
    """Classifica pela soma dos dias de missão, não pelo span do calendário."""
    if total_dias <= 15:
        return FaixaAjudaCusto.SEM_DESLIGAMENTO_ATE_15_DIAS
    if total_dias <= 90:
        return FaixaAjudaCusto.SEM_DESLIGAMENTO_15_DIAS_A_3_MESES
    return FaixaAjudaCusto.SEM_DESLIGAMENTO_ACIMA_3_MESES


def classificar_ajuda_custo_missoes(missoes: list[Missao]) -> FaixaAjudaCusto:
    return classificar_ajuda_custo_por_dias(dias_missoes(missoes))


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
    data_inicio_comissionamento: date | None = None
    data_termino_comissionamento: date | None = None
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
