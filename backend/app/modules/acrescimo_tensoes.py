# backend/app/modules/acrescimo_tensoes.py
import numpy as np
from typing import Optional
# Importa os modelos Pydantic do ficheiro centralizado
from app.models import (
    PontoInteresse, CargaPontual, CargaFaixa, CargaCircular, # Adicionado CargaFaixa, CargaCircular
    AcrescimoTensoesInput, AcrescimoTensoesOutput
)

PI = np.pi
EPSILON = 1e-9

# --- Funções de Cálculo Específicas ---

def calcular_acrescimo_boussinesq_pontual(carga: CargaPontual, ponto: PontoInteresse) -> float:
    """ (Código inalterado) """
    P = carga.P
    z = ponto.z
    r_quadrado = (ponto.x - carga.x)**2 + (ponto.y - carga.y)**2
    denominador_raiz = r_quadrado + z**2
    if denominador_raiz <= EPSILON: return float('nan')
    delta_sigma_v = (3 * P * (z**3)) / (2 * PI * (denominador_raiz**2.5)) #
    return delta_sigma_v

def calcular_acrescimo_carothers_faixa(carga: CargaFaixa, ponto: PontoInteresse) -> float:
    """
    Calcula o acréscimo de tensão vertical (Δσv) num ponto (x, z)
    devido a uma carga em faixa de largura 'b' (largura = 2 * semi_largura 'a') e intensidade 'p'.
    Assume que a faixa é infinita na direção y e o ponto está no plano xz.

    Fórmula usada (consistente com várias fontes):
    Δσv = (p / π) * [ α + sin(α) * cos(α + 2β) ]
    Onde α e β são os ângulos (rad) formados pelas linhas que unem o ponto às bordas da faixa
    com a vertical passando pelo ponto.

    Alternativamente, usando os ângulos 2α e 2β definidos no PDF:
    Δσv = (p / π) * (2α + sin(2α) * cos(2β)) onde 2α e 2β são ângulos subentendidos.

    Args:
        carga: Objeto CargaFaixa com largura (b) e intensidade (p).
        ponto: Ponto de interesse com x (dist. horizontal do centro) e z (profundidade).

    Referências:
    - PDF: 9. Tensões_devido_a_Sobrecarga-MAIO_2022.pdf (Pág. 15) - Cuidado com a definição dos ângulos.
    - Outras fontes de Mecânica dos Solos (ex: Das, Coduto)
    """
    p = carga.intensidade
    b = carga.largura # Largura total da faixa
    x = ponto.x # Distância horizontal do ponto ao centro da faixa
    z = ponto.z

    if z <= EPSILON: return p if abs(x) < b/2 else 0.0 # Na superfície

    # Usando a formulação com ângulos das bordas α1 e α2
    # α1: ângulo com a borda direita (x = b/2)
    # α2: ângulo com a borda esquerda (x = -b/2)
    alpha1 = np.arctan((b/2 - x) / z)
    alpha2 = np.arctan((-b/2 - x) / z)

    # Ângulo subentendido pela faixa no ponto P: delta_alpha = alpha1 - alpha2 (equivale a 2α do PDF)
    delta_alpha = alpha1 - alpha2
    # Ângulo relacionado à posição horizontal: sum_alpha = alpha1 + alpha2 (equivale a 2β do PDF)
    sum_alpha = alpha1 + alpha2

    # Aplicando a fórmula do PDF - Confirmar a convenção dos ângulos beta e alpha
    # Δσv = (p / π) * (sen(2α) * cos(2β) + 2α)
    # No PDF, 2α parece ser o ângulo subentendido e 2β o ângulo da bissetriz com a vertical
    # Na nossa dedução: delta_alpha = 2α do PDF, sum_alpha = 2β do PDF
    delta_sigma_v = (p / PI) * (delta_alpha + np.sin(delta_alpha) * np.cos(sum_alpha))

    return delta_sigma_v


def calcular_acrescimo_love_circular_centro(carga: CargaCircular, ponto: PontoInteresse) -> float:
    """
    Calcula o acréscimo de tensão vertical (Δσv) num ponto sob o CENTRO
    de uma área circular de raio R carregada uniformemente com intensidade p.

    Fórmula: Δσv = p * [1 - (1 / (1 + (R/z)²))^(3/2)]

    Args:
        carga: Objeto CargaCircular com raio (R) e intensidade (p).
        ponto: Ponto de interesse com profundidade z.

    Referências:
    - PDF: 9. Tensões_devido_a_Sobrecarga-MAIO_2022.pdf (Pág. 17)
    """
    p = carga.intensidade
    R = carga.raio
    z = ponto.z

    if z <= EPSILON: return p # Na superfície
    if R <= EPSILON: return 0.0 # Raio zero

    rz_ratio_sq = (R / z)**2
    termo_base = 1 / (1 + rz_ratio_sq)
    # Verifica se a base da potência é muito pequena para evitar underflow ou NaN
    if termo_base < EPSILON and 1.5 > 0: # Base quase zero e expoente positivo
        delta_sigma_v = p * (1.0 - 0.0)
    else:
        delta_sigma_v = p * (1 - termo_base**1.5)

    return delta_sigma_v

# Função para usar o Ábaco de Love (simplificado)
def calcular_acrescimo_love_circular_abaco(carga: CargaCircular, ponto: PontoInteresse) -> Optional[float]:
    """
    Estima o acréscimo de tensão vertical (Δσv) usando uma
    aproximação digital do ábaco de Love (Fig. Pág 18 do PDF 9).
    """
    p = carga.intensidade
    R = carga.raio
    z = ponto.z
    r = np.sqrt(ponto.x**2 + ponto.y**2) # Distância radial do centro

    if z <= EPSILON: return p if r < R else 0.0
    if R <= EPSILON: return 0.0

    z_R = z / R
    r_R = r / R

    # Dados aproximados do ábaco (extraídos visualmente ou de tabela externa)
    # Formato: { z/R: [(r/R, sigma_z/p), ...], ... }
    abaco_data = {
        0.5: [(0, 0.91), (0.5, 0.85), (0.75, 0.75), (1.0, 0.50), (1.25, 0.23), (1.5, 0.10)],
        1.0: [(0, 0.65), (0.5, 0.60), (0.75, 0.52), (1.0, 0.37), (1.25, 0.22), (1.5, 0.12)],
        1.5: [(0, 0.42), (0.5, 0.40), (0.75, 0.36), (1.0, 0.29), (1.25, 0.20), (1.5, 0.13)],
        2.0: [(0, 0.29), (0.5, 0.28), (0.75, 0.26), (1.0, 0.22), (1.25, 0.17), (1.5, 0.12)],
        3.0: [(0, 0.14), (0.5, 0.14), (0.75, 0.13), (1.0, 0.12), (1.25, 0.10), (1.5, 0.08)],
        # Adicionar mais pontos ou usar interpolação mais sofisticada
    }

    # Interpolação Bilinear Simples
    z_R_keys = sorted(abaco_data.keys())
    # Encontra z/R inferior e superior no ábaco
    z_R_inf = max([k for k in z_R_keys if k <= z_R], default=min(z_R_keys))
    z_R_sup = min([k for k in z_R_keys if k >= z_R], default=max(z_R_keys))

    if z_R_inf == z_R_sup: # z/R exato no ábaco
        curva = abaco_data[z_R_inf]
    else: # Interpola linearmente entre as curvas z/R
        curva_inf = abaco_data[z_R_inf]
        curva_sup = abaco_data[z_R_sup]
        # Pondera pela distância relativa a z/R
        peso_sup = (z_R - z_R_inf) / (z_R_sup - z_R_inf)
        peso_inf = 1.0 - peso_sup
        # Interpola os valores de sigma_z/p para cada r/R
        # Assume que ambas as curvas têm os mesmos pontos r/R (pode precisar de ajuste)
        curva = []
        for i in range(len(curva_inf)):
            r_R_val = curva_inf[i][0]
            sigma_p_inf = curva_inf[i][1]
            # Encontra o ponto correspondente na curva superior
            sigma_p_sup = next((p[1] for p in curva_sup if np.isclose(p[0], r_R_val)), sigma_p_inf) # Usa valor inf se não achar
            sigma_p_interp = peso_inf * sigma_p_inf + peso_sup * sigma_p_sup
            curva.append((r_R_val, sigma_p_interp))

    # Agora, interpola linearmente na curva resultante para o r/R do ponto
    r_R_vals = [p[0] for p in curva]
    sigma_p_vals = [p[1] for p in curva]

    if r_R >= r_R_vals[-1]: # Fora do ábaco (à direita)
        # Pode extrapolar ou retornar o último valor/zero? Retornar o último valor por segurança.
        fator_I = sigma_p_vals[-1]
    elif r_R <= r_R_vals[0]: # Fora do ábaco (à esquerda - centro)
        fator_I = sigma_p_vals[0]
    else: # Interpola linearmente
        fator_I = np.interp(r_R, r_R_vals, sigma_p_vals)

    if fator_I < 0: fator_I = 0.0 # Garante não-negativo

    delta_sigma_v = p * fator_I
    return delta_sigma_v

# --- Função Principal do Módulo ---

def calcular_acrescimo_tensoes(dados: AcrescimoTensoesInput) -> AcrescimoTensoesOutput:
    """
    Calcula o acréscimo de tensão vertical com base no tipo de carga especificado.
    Suporta: 'pontual', 'faixa', 'circular'.
    """
    try:
        tipo = dados.tipo_carga.lower()
        ponto = dados.ponto_interesse

        if ponto.z <= EPSILON:
             raise ValueError("Profundidade (z) do ponto de interesse deve ser maior que zero.")

        delta_sigma: Optional[float] = None
        metodo: Optional[str] = None

        if tipo == "pontual":
            if dados.carga_pontual is None: raise ValueError("Dados de 'carga_pontual' necessários.")
            delta_sigma = calcular_acrescimo_boussinesq_pontual(dados.carga_pontual, ponto)
            metodo = "Boussinesq (Pontual)"

        elif tipo == "faixa":
            if dados.carga_faixa is None: raise ValueError("Dados de 'carga_faixa' necessários.")
            delta_sigma = calcular_acrescimo_carothers_faixa(dados.carga_faixa, ponto)
            metodo = "Carothers (Faixa)"

        elif tipo == "circular":
            if dados.carga_circular is None: raise ValueError("Dados de 'carga_circular' necessários.")
            # Usar ábaco para pontos fora do centro
            delta_sigma = calcular_acrescimo_love_circular_abaco(dados.carga_circular, ponto)
            metodo = "Love (Circular - Ábaco)"
            # Se fosse apenas no centro:
            # if abs(ponto.x) > EPSILON or abs(ponto.y) > EPSILON:
            #     return AcrescimoTensoesOutput(metodo="Love (Circular)", erro="Cálculo fora do centro requer ábaco/métodos numéricos (não implementado).")
            # else:
            #     delta_sigma = calcular_acrescimo_love_circular_centro(dados.carga_circular, ponto)
            #     metodo = "Love (Circular - Centro)"

        # elif tipo == "retangular":
             # Implementação futura usando Newmark (integração ou ábaco digitalizado)
             # return AcrescimoTensoesOutput(erro="Cálculo para carga retangular ainda não implementado.")

        else:
            return AcrescimoTensoesOutput(erro=f"Tipo de carga '{dados.tipo_carga}' não suportado.")

        # --- Processamento do Resultado ---
        if delta_sigma is None:
             return AcrescimoTensoesOutput(metodo=metodo, erro="Falha no cálculo interno.")
        elif np.isnan(delta_sigma):
             return AcrescimoTensoesOutput(metodo=metodo, erro="Cálculo resultou em valor indefinido (NaN). Verifique os dados.")
        else:
            return AcrescimoTensoesOutput(
                delta_sigma_v=round(delta_sigma, 4),
                metodo=metodo
            )

    except ValueError as ve:
        return AcrescimoTensoesOutput(erro=str(ve))
    except Exception as e:
        import traceback
        print(f"Erro inesperado no cálculo de acréscimo de tensões: {e}\n{traceback.format_exc()}")
        return AcrescimoTensoesOutput(erro=f"Erro interno no servidor: {type(e).__name__}")