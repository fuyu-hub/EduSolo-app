# backend/app/modules/fluxo_hidraulico.py
import numpy as np
from typing import List, Optional, Dict
# Importa os modelos Pydantic definidos em app/models.py
from app.models import CamadaFluxo, FluxoHidraulicoOutput, TensaoPontoFluxo

PI = np.pi
EPSILON = 1e-9

def calcular_permeabilidade_equivalente(camadas: List[CamadaFluxo], direcao: str) -> Optional[float]:
    """
    Calcula o coeficiente de permeabilidade equivalente para fluxo
    horizontal (kh) ou vertical (kv) em solo estratificado.

    Referências:
    - PDF: 10.1. Hidrulica_dos_Solos_Ana_Patricia_Maio_2022_Parte_1.pdf (Pág. 9)
    """
    if not camadas:
        return None

    espessura_total = sum(c.espessura for c in camadas if c.espessura is not None and c.espessura > 0)
    if espessura_total <= EPSILON:
        return None

    # Verifica se todas as camadas têm k definido
    if any(c.k is None or c.k < 0 for c in camadas):
        raise ValueError("Todas as camadas devem ter um coeficiente de permeabilidade (k) não-negativo definido.")

    if direcao.lower() == 'horizontal':
        # Média ponderada pela espessura
        kh_num = sum(c.k * c.espessura for c in camadas)
        return kh_num / espessura_total
    elif direcao.lower() == 'vertical':
        # Média harmônica ponderada pela espessura
        # Verifica se algum k é zero para evitar divisão por zero
        if any(np.isclose(c.k, 0) for c in camadas):
             # Se alguma camada for impermeável (k=0), kv será zero
             # (assumindo que a espessura dessa camada não é zero)
             if any(np.isclose(c.k, 0) and c.espessura > EPSILON for c in camadas):
                 return 0.0
             else: # Se k=0 mas espessura=0, ignora essa camada
                  kv_den_sum = sum(c.espessura / c.k for c in camadas if c.k is not None and c.k > EPSILON and c.espessura > EPSILON)
                  if kv_den_sum <= EPSILON: return None # Caso incomum
                  return espessura_total / kv_den_sum

        kv_den_sum = sum(c.espessura / c.k for c in camadas if c.k > EPSILON) # Evita k=0
        if kv_den_sum <= EPSILON:
            return None # Evita divisão por zero se todos os k/espessura forem zero
        return espessura_total / kv_den_sum
    else:
        raise ValueError("Direção deve ser 'horizontal' ou 'vertical'.")

def calcular_velocidades_fluxo(k: float, i: float, n: Optional[float]) -> Dict[str, Optional[float]]:
    """
    Calcula a velocidade de descarga (v) e a velocidade de fluxo/percolação (vf).

    Referências:
    - PDF: 10.1. Hidrulica_dos_Solos_Ana_Patricia_Maio_2022_Parte_1.pdf (Pág. 8, 21)
    """
    if k < 0 or i < 0:
        raise ValueError("Coeficiente de permeabilidade (k) e gradiente hidráulico (i) devem ser não-negativos.")

    v_descarga = k * i # Lei de Darcy
    v_fluxo = None
    if n is not None:
        if n <= 0 or n >= 1:
             raise ValueError("Porosidade (n) deve estar entre 0 e 1 (exclusivo).")
        else:
             v_fluxo = v_descarga / n #

    return {"velocidade_descarga": v_descarga, "velocidade_fluxo": v_fluxo}

def calcular_tensoes_com_fluxo(
    profundidades: List[float], # Lista de profundidades onde calcular
    camadas: List[CamadaFluxo], # Lista de camadas com k, gamma_sat
    profundidade_na_entrada: float, # NA a montante
    profundidade_na_saida: float,   # NA a jusante
    gamma_w: float,
    direcao_fluxo: str # 'ascendente' ou 'descendente' (vertical)
) -> List[TensaoPontoFluxo]:
    """
    Calcula as tensões (total, neutra, efetiva) em várias profundidades
    sob fluxo vertical constante. Assume solo totalmente saturado entre a entrada e saída.

    Args:
        profundidades: Lista de profundidades (z) desde a superfície.
        camadas: Lista das camadas saturadas envolvidas no fluxo.
        profundidade_na_entrada: Profundidade do NA que define a carga de entrada.
        profundidade_na_saida: Profundidade do NA que define a carga de saída.
        gamma_w: Peso específico da água.
        direcao_fluxo: 'ascendente' ou 'descendente'.

    Returns:
        Lista de TensaoPontoFluxo com os resultados.

    Referências:
    - PDF: 10.2. Hidrulica_dos_Solos_Ana_Patricia_Maio_2022_Parte_2.pdf (Págs. 4-6)
    """
    if not camadas:
        raise ValueError("Lista de camadas não pode ser vazia.")
    if gamma_w <= 0:
        raise ValueError("Peso específico da água deve ser positivo.")

    # Assume que as camadas estão ordenadas de cima para baixo
    profundidade_topo_fluxo = 0.0 # Profundidade do início da primeira camada de fluxo
    espessura_total_fluxo = sum(c.espessura for c in camadas)
    profundidade_base_fluxo = profundidade_topo_fluxo + espessura_total_fluxo

    # Carga hidráulica total (delta_h)
    carga_entrada = -profundidade_na_entrada # Assumindo datum na superfície
    carga_saida = -profundidade_na_saida
    delta_h_total = carga_entrada - carga_saida

    # Gradiente hidráulico médio
    if espessura_total_fluxo <= EPSILON:
        raise ValueError("Espessura total das camadas de fluxo não pode ser zero.")
    i_medio = delta_h_total / espessura_total_fluxo # Positivo para descendente, Negativo para ascendente

    # Valida direção do fluxo vs gradiente
    if direcao_fluxo.lower() == 'descendente' and i_medio < 0:
         raise ValueError("Direção de fluxo 'descendente' inconsistente com NA de entrada abaixo do NA de saída.")
    if direcao_fluxo.lower() == 'ascendente' and i_medio > 0:
         raise ValueError("Direção de fluxo 'ascendente' inconsistente com NA de entrada acima do NA de saída.")

    resultados: List[TensaoPontoFluxo] = []
    tensao_total_acumulada = 0.0 # Tensão total na profundidade_topo_fluxo (pode vir de camadas acima)
    profundidade_camada_atual = profundidade_topo_fluxo

    # Calcula a carga hidráulica no topo da zona de fluxo
    # h_total(z) = u/gamma_w + z_elevation (datum na superfície, z positivo para baixo)
    # h_total_topo = profundidade_na_entrada (se z=0 for superfície) - profundidade_topo_fluxo ???
    # h_total(z) = Carga Piezométrica + Carga de Elevação
    # Usando datum na superfície (z=0): Elevacao(z) = -z
    # Carga total no NA entrada = 0 + (-profundidade_na_entrada) = -profundidade_na_entrada
    # Carga total no NA saida = 0 + (-profundidade_na_saida) = -profundidade_na_saida
    carga_total_topo = -profundidade_na_entrada # Assumindo que a entrada define a carga no topo da zona

    pontos_interesse = sorted(list(set(profundidades))) # Ordena e remove duplicados

    idx_camada = 0
    for z_ponto in pontos_interesse:
        # Encontra a camada onde o ponto está
        while idx_camada < len(camadas) and z_ponto > profundidade_camada_atual + camadas[idx_camada].espessura + EPSILON:
             tensao_total_acumulada += camadas[idx_camada].gamma_sat * camadas[idx_camada].espessura
             profundidade_camada_atual += camadas[idx_camada].espessura
             idx_camada += 1

        if idx_camada >= len(camadas): # Ponto está abaixo da última camada de fluxo
            # Calcular como se estivesse na base da última camada? Ou erro?
            # Por simplicidade, calcula na base da última camada
            z_relativo = camadas[-1].espessura
            camada_atual = camadas[-1]
        else:
            z_relativo = z_ponto - profundidade_camada_atual
            camada_atual = camadas[idx_camada]

        # Calcula Tensão Total Vertical (σv)
        sigma_v = tensao_total_acumulada + camada_atual.gamma_sat * z_relativo

        # Calcula Carga Hidráulica Total (h_total) no ponto z_ponto
        # Assumindo gradiente constante dentro de cada camada ou médio? Usar médio por simplicidade.
        carga_total_ponto = carga_total_topo + i_medio * (z_ponto - profundidade_topo_fluxo)

        # Calcula Pressão Neutra (u)
        # h_total = u/gamma_w + Z_elev => u = gamma_w * (h_total - Z_elev)
        # Z_elev = -z_ponto (datum na superfície)
        pressao_neutra = gamma_w * (carga_total_ponto - (-z_ponto))
        pressao_neutra = max(0, pressao_neutra) # Pressão neutra não pode ser negativa em fluxo saturado (exceto capilaridade, não considerada aqui)

        # Calcula Tensão Efetiva Vertical (σ'v)
        tensao_efetiva_v = sigma_v - pressao_neutra
        tensao_efetiva_v = max(0, tensao_efetiva_v) # Garante não-negatividade

        resultados.append(TensaoPontoFluxo(
            profundidade=z_ponto,
            tensao_total_vertical=round(sigma_v, 3),
            pressao_neutra=round(pressao_neutra, 3),
            tensao_efetiva_vertical=round(tensao_efetiva_v, 3),
            carga_hidraulica_total=round(carga_total_ponto, 3)
        ))

    return resultados


def calcular_gradiente_critico(gamma_sat: float, gamma_w: float) -> Optional[float]:
    """
    Calcula o gradiente hidráulico crítico (icrit) para ocorrência de areia movediça.

    Referências:
    - PDF: 10.2. Hidrulica_dos_Solos_Ana_Patricia_Maio_2022_Parte_2.pdf (Pág. 7)
    """
    if gamma_w <= EPSILON:
        return None
    gamma_sub = gamma_sat - gamma_w
    if gamma_sub < 0: # Não faz sentido físico
        return None
    if gamma_w <= EPSILON: # Evita divisão por zero
        return float('inf') if gamma_sub > EPSILON else None # Indefinido se ambos forem zero
    icrit = gamma_sub / gamma_w #
    return icrit

def calcular_fs_liquefacao(icrit: float, i_atuante: float) -> Optional[float]:
    """ Calcula o Fator de Segurança contra liquefação (areia movediça). """
    # i_atuante deve ser positivo para fluxo ascendente
    if i_atuante <= EPSILON:
        # Se não há fluxo ascendente significativo, FS é "infinito" ou muito alto
        return float('inf')
    if icrit < 0: # icrit inválido
        return None
    fs = icrit / i_atuante #
    return fs