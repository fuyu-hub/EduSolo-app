import numpy as np
from typing import Optional
# Importa os modelos Pydantic do ficheiro centralizado
from app.models import PontoInteresse, CargaPontual, AcrescimoTensoesInput, AcrescimoTensoesOutput

# Constante
PI = np.pi

def calcular_acrescimo_boussinesq_pontual(carga: CargaPontual, ponto: PontoInteresse) -> float:
    """
    Calcula o acréscimo de tensão vertical (Δσv) num ponto (x, y, z)
    devido a uma carga pontual P aplicada em (carga.x, carga.y, 0),
    usando a solução de Boussinesq (1885).

    Fórmula: Δσv = (3 * P * z³) / (2 * π * (r² + z²)^(5/2))
             onde r² = (x_ponto - x_carga)² + (y_ponto - y_carga)²

    Referências:
    - PDF: 9. Tensões_devido_a_Sobrecarga-MAIO_2022.pdf (Pág. 13-14)
    """
    P = carga.P
    z = ponto.z # Profundidade do ponto de interesse (z > 0)

    # Distância horizontal radial (r) do ponto de interesse à projeção vertical da carga
    r_quadrado = (ponto.x - carga.x)**2 + (ponto.y - carga.y)**2

    denominador_raiz = r_quadrado + z**2
    if denominador_raiz <= 1e-9: # Evita divisão por zero (z>0 já é garantido pela validação Pydantic)
        # Este caso só ocorreria se r=0 e z=0, mas z>0 é exigido.
         return float('nan') # Ou um erro, mas NaN é matematicamente correto

    delta_sigma_v = (3 * P * (z**3)) / (2 * PI * (denominador_raiz**2.5))

    return delta_sigma_v

def calcular_acrescimo_tensoes(dados: AcrescimoTensoesInput) -> AcrescimoTensoesOutput:
    """
    Calcula o acréscimo de tensão vertical com base no tipo de carga especificado.
    MVP: Suporta apenas carga pontual (Boussinesq).
    """
    try:
        # Validação do tipo de carga (embora já feita no main.py, redundância não faz mal)
        if dados.tipo_carga.lower() == "pontual":
            if dados.carga_pontual is None:
                raise ValueError("Dados da 'carga_pontual' são necessários para tipo_carga 'pontual'.")
            # Validação de profundidade já feita pelo Pydantic (gt=0)

            delta_sigma = calcular_acrescimo_boussinesq_pontual(
                carga=dados.carga_pontual,
                ponto=dados.ponto_interesse
            )

            # Verifica se o resultado foi NaN (caso r=0, z=0 que não deveria ocorrer com z>0)
            if np.isnan(delta_sigma):
                 return AcrescimoTensoesOutput(metodo="Boussinesq (Pontual)", erro="Cálculo resultou em valor indefinido (NaN). Verifique os dados.")

            return AcrescimoTensoesOutput(
                delta_sigma_v=round(delta_sigma, 4), # Arredonda para kPa, por exemplo
                metodo="Boussinesq (Pontual)"
            )

        # --- Placeholders para futuras implementações ---
        # elif dados.tipo_carga.lower() == "retangular":
        #     if dados.carga_retangular is None:
        #         raise ValueError("Dados da 'carga_retangular' são necessários.")
        #     # Chamar função de Newmark (a implementar)
        #     # delta_sigma = calcular_acrescimo_newmark(...)
        #     # return AcrescimoTensoesOutput(delta_sigma_v=delta_sigma, metodo="Newmark (Retangular)")
        #     return AcrescimoTensoesOutput(erro="Cálculo para carga retangular ainda não implementado.")
        #
        # elif dados.tipo_carga.lower() == "circular":
        #      if dados.carga_circular is None:
        #         raise ValueError("Dados da 'carga_circular' são necessários.")
        #      # Chamar função de Love (a implementar)
        #      # delta_sigma = calcular_acrescimo_love(...)
        #      # return AcrescimoTensoesOutput(delta_sigma_v=delta_sigma, metodo="Love (Circular)")
        #      return AcrescimoTensoesOutput(erro="Cálculo para carga circular ainda não implementado.")
        #
        # elif dados.tipo_carga.lower() == "faixa":
        #       if dados.carga_faixa is None:
        #         raise ValueError("Dados da 'carga_faixa' são necessários.")
        #       # Chamar função de Carothers (a implementar)
        #       # delta_sigma = calcular_acrescimo_carothers(...)
        #       # return AcrescimoTensoesOutput(delta_sigma_v=delta_sigma, metodo="Carothers (Faixa)")
        #       return AcrescimoTensoesOutput(erro="Cálculo para carga em faixa ainda não implementado.")
        else:
            return AcrescimoTensoesOutput(erro=f"Tipo de carga '{dados.tipo_carga}' não suportado.")

    except ValueError as ve:
        return AcrescimoTensoesOutput(erro=str(ve))
    except Exception as e:
        import traceback
        print(f"Erro inesperado no cálculo de acréscimo de tensões: {e}\n{traceback.format_exc()}")
        return AcrescimoTensoesOutput(erro=f"Erro interno no servidor: {type(e).__name__}")