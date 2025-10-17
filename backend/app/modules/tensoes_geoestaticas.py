import numpy as np
from typing import List, Optional
# Importa os modelos Pydantic do ficheiro centralizado
from app.models import CamadaSolo, TensaoPonto, TensoesGeostaticasInput, TensoesGeostaticasOutput

def calcular_tensoes_geostaticas(dados: TensoesGeostaticasInput) -> TensoesGeostaticasOutput:
    """
    Calcula os perfis de tensão total vertical (σv), pressão neutra (u) e
    tensão efetiva vertical (σ'v) e horizontal (σ'h) para um perfil de solo estratificado.

    Considera a posição do Nível d'Água (NA) e a franja capilar.

    Referências:
    - PDF: 8. Tenses_no_Solo-Maio_2022-1.pdf (Págs. 3-13, 27-32)
    """
    pontos_calculo: List[TensaoPonto] = []
    profundidade_atual: float = 0.0
    tensao_total_atual: float = 0.0
    gama_w = dados.peso_especifico_agua

    try:
        if not dados.camadas:
             raise ValueError("A lista de camadas não pode estar vazia.")

        # Ponto inicial na superfície
        # Calcula pressão neutra inicial considerando capilaridade
        u_inicial = 0.0
        if dados.profundidade_na <= 0 and dados.altura_capilar > 0: # NA na superfície ou acima
            # Considera apenas a parte da capilaridade acima da superfície (se houver)
            # Neste caso simplificado, se NA=0, a pressão na superfície é negativa pela capilaridade
             u_inicial = -min(dados.altura_capilar, 0) * gama_w # Será 0 se NA=0, mas pode ser negativa se NA < 0
             # Para o caso NA=0 exato, a pressão é -altura_capilar*gama_w, mas só se z<altura_capilar
             # Na superfície (z=0), se NA=0, u = -altura_capilar*gama_w *apenas* se h_capilar > 0
             u_inicial = -dados.altura_capilar * gama_w if dados.altura_capilar > 0 else 0.0


        sigma_ef_v_inicial = 0.0 - u_inicial
        sigma_ef_h_inicial = sigma_ef_v_inicial * dados.camadas[0].Ko # Usa Ko da primeira camada

        pontos_calculo.append(TensaoPonto(
            profundidade=0.0,
            tensao_total_vertical=0.0,
            pressao_neutra=u_inicial,
            tensao_efetiva_vertical=sigma_ef_v_inicial,
            tensao_efetiva_horizontal=sigma_ef_h_inicial
        ))


        for i, camada in enumerate(dados.camadas):
            profundidade_base_camada = profundidade_atual + camada.espessura
            z_topo = profundidade_atual
            z_base = profundidade_base_camada

            # --- Calcular Tensão Total na Base da Camada ---
            if z_base <= dados.profundidade_na: # Camada inteira acima do NA
                gama_camada = camada.gama_nat
                if gama_camada is None:
                    raise ValueError(f"Peso específico natural (γnat) não definido para a camada {i+1} (ID: {i}) que está acima do NA (Prof: {z_topo:.2f}-{z_base:.2f} m, NA: {dados.profundidade_na:.2f} m).")
                tensao_total_atual += gama_camada * camada.espessura

            elif z_topo >= dados.profundidade_na: # Camada inteira abaixo do NA
                gama_camada = camada.gama_sat
                if gama_camada is None:
                    raise ValueError(f"Peso específico saturado (γsat) não definido para a camada {i+1} (ID: {i}) que está abaixo do NA (Prof: {z_topo:.2f}-{z_base:.2f} m, NA: {dados.profundidade_na:.2f} m).")
                tensao_total_atual += gama_camada * camada.espessura

            else: # Camada atravessada pelo NA
                espessura_acima_na = dados.profundidade_na - z_topo
                espessura_abaixo_na = z_base - dados.profundidade_na

                gama_nat_camada = camada.gama_nat
                gama_sat_camada = camada.gama_sat

                if gama_nat_camada is None:
                     raise ValueError(f"Peso específico natural (γnat) não definido para a camada {i+1} (ID: {i}) que é atravessada pelo NA (NA: {dados.profundidade_na:.2f} m).")
                if gama_sat_camada is None:
                     raise ValueError(f"Peso específico saturado (γsat) não definido para a camada {i+1} (ID: {i}) que é atravessada pelo NA (NA: {dados.profundidade_na:.2f} m).")

                # Adiciona contribuição da parte acima do NA
                tensao_total_na_interface = tensao_total_atual + gama_nat_camada * espessura_acima_na

                # Adiciona ponto de cálculo exatamente no NA se ele corta a camada
                u_no_na = 0.0 # Por definição
                sigma_v_no_na = tensao_total_na_interface
                sigma_ef_v_no_na = sigma_v_no_na - u_no_na
                sigma_ef_h_no_na = sigma_ef_v_no_na * camada.Ko
                # Evita duplicar se o NA coincide com interface de camadas
                if not any(np.isclose(p.profundidade, dados.profundidade_na) for p in pontos_calculo):
                    pontos_calculo.append(TensaoPonto(
                        profundidade=dados.profundidade_na,
                        tensao_total_vertical=round(sigma_v_no_na, 4),
                        pressao_neutra=round(u_no_na, 4),
                        tensao_efetiva_vertical=round(sigma_ef_v_no_na, 4),
                        tensao_efetiva_horizontal=round(sigma_ef_h_no_na, 4)
                    ))

                # Adiciona contribuição da parte abaixo do NA para chegar na base da camada
                tensao_total_atual = tensao_total_na_interface + gama_sat_camada * espessura_abaixo_na

            # --- Calcular Pressão Neutra e Tensão Efetiva na Base da Camada ---
            # Distância vertical da base da camada até o NA
            distancia_vertical_na = z_base - dados.profundidade_na

            # Considera capilaridade
            if distancia_vertical_na >= 0: # Abaixo ou no NA
                pressao_neutra = distancia_vertical_na * gama_w
            elif abs(distancia_vertical_na) <= dados.altura_capilar: # Dentro da franja capilar
                 # u = -γw * h (onde h é a altura acima do NA, que é -distancia_vertical_na)
                 pressao_neutra = distancia_vertical_na * gama_w # Já é negativo
            else: # Acima da franja capilar
                pressao_neutra = 0.0

            tensao_efetiva_vertical = tensao_total_atual - pressao_neutra
            # Garante que não seja negativa devido a erros de precisão ou capilaridade muito alta
            if tensao_efetiva_vertical < -1e-9: # Pequena tolerância para zero
                 # Isso pode acontecer se a capilaridade for muito alta ou γnat baixo
                 # Pode ser um aviso, mas para cálculo, limitamos a zero
                 # print(f"Aviso: Tensão efetiva vertical calculada negativa ({tensao_efetiva_vertical:.4f}) na profundidade {z_base:.2f} m. Limitando a 0.")
                 tensao_efetiva_vertical = 0.0

            tensao_efetiva_horizontal = tensao_efetiva_vertical * camada.Ko

            # Adiciona ponto de cálculo na base da camada
            pontos_calculo.append(TensaoPonto(
                profundidade=round(profundidade_base_camada, 4),
                tensao_total_vertical=round(tensao_total_atual, 4),
                pressao_neutra=round(pressao_neutra, 4),
                tensao_efetiva_vertical=round(tensao_efetiva_vertical, 4),
                tensao_efetiva_horizontal=round(tensao_efetiva_horizontal, 4)
            ))

            profundidade_atual = profundidade_base_camada

        # Ordena os pontos por profundidade para garantir a ordem correta para plotagem
        pontos_calculo.sort(key=lambda p: p.profundidade)

        # Remove pontos duplicados de profundidade (pode ocorrer se NA = interface)
        pontos_unicos = []
        profundidades_vistas = set()
        for ponto in pontos_calculo:
            if round(ponto.profundidade, 4) not in profundidades_vistas:
                pontos_unicos.append(ponto)
                profundidades_vistas.add(round(ponto.profundidade, 4))

        return TensoesGeostaticasOutput(pontos_calculo=pontos_unicos)

    except ValueError as ve:
        return TensoesGeostaticasOutput(pontos_calculo=[], erro=str(ve))
    except Exception as e:
        import traceback
        print(f"Erro inesperado no cálculo de tensões geostáticas: {e}\n{traceback.format_exc()}")
        return TensoesGeostaticasOutput(pontos_calculo=[], erro=f"Erro interno no servidor: {type(e).__name__}")