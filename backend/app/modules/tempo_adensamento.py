# backend/app/modules/tempo_adensamento.py
import numpy as np
from app.models import TempoAdensamentoInput, TempoAdensamentoOutput
from typing import Optional

PI = np.pi
EPSILON = 1e-9

def calcular_Tv_de_Uz(Uz_percent: float) -> Optional[float]:
    """ Calcula o Fator Tempo (Tv) a partir do Grau de Adensamento Médio (Uz) em %. """
    if Uz_percent < 0 or Uz_percent > 100:
        return None
    if np.isclose(Uz_percent, 100.0):
        return float('inf') # Teoricamente infinito para 100%

    Uz = Uz_percent / 100.0
    if Uz <= 0.60: # Para U <= 60%
        Tv = (PI / 4) * (Uz**2) #
    else: # Para U > 60%
        Tv = -0.933 * np.log10(1 - Uz) - 0.085 #
    return Tv

def calcular_Uz_de_Tv(Tv: float) -> Optional[float]:
    """ Calcula o Grau de Adensamento Médio (Uz) em % a partir do Fator Tempo (Tv). """
    if Tv < 0:
        return None
    if Tv == 0:
        return 0.0

    if Tv <= 0.283: # Corresponde a U ~ 60%
        # Tv = (PI/4) * U^2 => U = sqrt(4*Tv / PI)
        Uz = np.sqrt(4 * Tv / PI)
    else:
        # Tv = -0.933 * log10(1 - U) - 0.085 => log10(1 - U) = (Tv + 0.085) / -0.933
        # 1 - U = 10**((Tv + 0.085) / -0.933) => U = 1 - 10**(-(Tv + 0.085) / 0.933)
        try:
            # Verifica se o expoente não é muito grande para evitar overflow/underflow
            exponent = -(Tv + 0.085) / 0.933
            if exponent < -30: # Limite prático para evitar 1 - ~0 = 1
                Uz = 1.0
            else:
                 Uz = 1 - (10**exponent)
        except OverflowError:
             Uz = 1.0 # Aproxima para 100% se o cálculo falhar por overflow

    # Garante que Uz esteja entre 0 e 1, depois converte para percentagem
    Uz = np.clip(Uz, 0, 1)
    return Uz * 100

def calcular_tempo_adensamento(dados: TempoAdensamentoInput) -> TempoAdensamentoOutput:
    """
    Realiza a análise do tempo de adensamento primário.
    Calcula o tempo para um dado Uz, ou o recalque e Uz para um dado tempo.

    Referências:
    - PDF: 11.2. Recalques_por_adensamento_Junho_2022-1.pdf (Págs. 27-32)
    """
    try:
        delta_H_total = dados.recalque_total_primario
        Cv = dados.coeficiente_adensamento
        Hd = dados.altura_drenagem

        if delta_H_total <= 0 or Cv <= 0 or Hd <= 0:
            raise ValueError("Recalque total, Cv e Hd devem ser positivos.")
        if dados.tempo is None and dados.grau_adensamento_medio is None:
            raise ValueError("É necessário fornecer 'tempo' ou 'grau_adensamento_medio'.")
        if dados.tempo is not None and dados.grau_adensamento_medio is not None:
            raise ValueError("Forneça apenas 'tempo' OU 'grau_adensamento_medio', não ambos.")

        tempo_calculado: Optional[float] = None
        recalque_no_tempo: Optional[float] = None
        Uz_calculado: Optional[float] = None
        Tv_calculado: Optional[float] = None

        # Caso 1: Calcular tempo para atingir Uz
        if dados.grau_adensamento_medio is not None:
            Uz_desejado = dados.grau_adensamento_medio
            Tv_calculado = calcular_Tv_de_Uz(Uz_desejado)
            if Tv_calculado is None:
                raise ValueError("Grau de adensamento médio inválido (deve ser entre 0 e 100).")
            if np.isinf(Tv_calculado):
                tempo_calculado = float('inf')
                recalque_no_tempo = delta_H_total
                Uz_calculado = 100.0
            else:
                tempo_calculado = (Tv_calculado * (Hd**2)) / Cv #
                recalque_no_tempo = (Uz_desejado / 100.0) * delta_H_total
                Uz_calculado = Uz_desejado

        # Caso 2: Calcular recalque e Uz num dado tempo
        elif dados.tempo is not None:
            tempo = dados.tempo
            if tempo < 0: raise ValueError("Tempo deve ser não-negativo.")
            if tempo == 0:
                Tv_calculado = 0.0
                Uz_calculado = 0.0
                recalque_no_tempo = 0.0
            else:
                Tv_calculado = (Cv * tempo) / (Hd**2) #
                Uz_calculado = calcular_Uz_de_Tv(Tv_calculado)
                if Uz_calculado is None:
                    # Isso não deve acontecer se Tv >= 0
                    raise ValueError("Erro ao calcular Uz a partir de Tv.")
                recalque_no_tempo = (Uz_calculado / 100.0) * delta_H_total
            tempo_calculado = tempo # O tempo foi dado como entrada


        return TempoAdensamentoOutput(
            tempo_calculado=round(tempo_calculado, 3) if tempo_calculado is not None and np.isfinite(tempo_calculado) else tempo_calculado,
            recalque_no_tempo=round(recalque_no_tempo, 4) if recalque_no_tempo is not None else None,
            grau_adensamento_medio_calculado=round(Uz_calculado, 2) if Uz_calculado is not None else None,
            fator_tempo=round(Tv_calculado, 4) if Tv_calculado is not None and np.isfinite(Tv_calculado) else Tv_calculado
        )

    except ValueError as ve:
        return TempoAdensamentoOutput(erro=str(ve))
    except Exception as e:
        print(f"Erro inesperado no cálculo de tempo de adensamento: {e}")
        return TempoAdensamentoOutput(erro=f"Erro interno no servidor: {type(e).__name__}")