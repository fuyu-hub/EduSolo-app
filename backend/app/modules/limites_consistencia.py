# backend/app/modules/limites_consistencia.py

import numpy as np
from typing import List, Optional
# Importa os modelos Pydantic do ficheiro centralizado
from app.models import (
    PontoEnsaioLL,
    LimitesConsistenciaInput,
    LimitesConsistenciaOutput,
    PontoCurva
)

# Constante para logaritmo
LOG10_25 = np.log10(25)

def calcular_limites_consistencia(dados: LimitesConsistenciaInput) -> LimitesConsistenciaOutput:
    """
    Calcula os Limites de Atterberg (LL, LP), Índice de Plasticidade (IP),
    Índice de Consistência (IC) e Atividade da Argila (Ia).

    Referências Principais:
    - PDF: 5. Plasticidade_Maro_2022.pdf
    """
    try:
        # --- Cálculo das Umidades dos pontos do Ensaio LL ---
        pontos_grafico_ll_log: List[PontoCurva] = []
        umidades_ll: List[float] = []
        log_golpes_ll: List[float] = []

        if len(dados.pontos_ll) < 2:
            raise ValueError("São necessários pelo menos 2 pontos para o cálculo do Limite de Liquidez.")

        for i, ponto in enumerate(dados.pontos_ll):
            # Validações básicas
            if ponto.massa_umida_recipiente < ponto.massa_seca_recipiente:
                 raise ValueError(f"Ponto LL {i+1}: Massa úmida ({ponto.massa_umida_recipiente}g) menor que massa seca ({ponto.massa_seca_recipiente}g).")
            if ponto.massa_seca_recipiente < ponto.massa_recipiente:
                 raise ValueError(f"Ponto LL {i+1}: Massa seca ({ponto.massa_seca_recipiente}g) menor que massa do recipiente ({ponto.massa_recipiente}g).")
            if ponto.num_golpes <= 0:
                 raise ValueError(f"Ponto LL {i+1}: Número de golpes ({ponto.num_golpes}) inválido.")

            massa_agua = ponto.massa_umida_recipiente - ponto.massa_seca_recipiente
            massa_seca = ponto.massa_seca_recipiente - ponto.massa_recipiente

            if massa_seca <= 1e-9: # Evita divisão por zero
                raise ValueError(f"Ponto LL {i+1}: Massa seca calculada é zero ou negativa ({massa_seca:.2f}g). Verifique os dados.")
            if massa_agua < 0:
                # Pode acontecer devido a erros de pesagem, tratar como 0? Ou erro? Lançar erro é mais seguro.
                 raise ValueError(f"Ponto LL {i+1}: Massa de água calculada é negativa ({massa_agua:.2f}g). Verifique os dados.")

            umidade_ponto = (massa_agua / massa_seca) * 100 # Em porcentagem [cite: 80]
            log_golpes = np.log10(ponto.num_golpes)

            pontos_grafico_ll_log.append(PontoCurva(x=log_golpes, y=umidade_ponto))
            umidades_ll.append(umidade_ponto)
            log_golpes_ll.append(log_golpes)

        # --- Cálculo do Limite de Liquidez (LL) ---
        # Regressão Linear: log10(N) vs w%
        # Queremos w = a * log10(N) + b => polyfit retorna [a, b]
        try:
            coeffs = np.polyfit(log_golpes_ll, umidades_ll, 1) # Grau 1 para regressão linear
            poly_func = np.poly1d(coeffs)
            ll_calculado = poly_func(LOG10_25) # LL é a umidade para N=25 golpes
        except (np.linalg.LinAlgError, ValueError) as e:
             raise ValueError(f"Erro ao calcular regressão linear para LL: {e}. Verifique os pontos do ensaio.")

        if ll_calculado < 0: ll_calculado = 0.0 # Umidade não pode ser negativa

        # --- Cálculo do Limite de Plasticidade (LP) ---
        if dados.massa_umida_recipiente_lp < dados.massa_seca_recipiente_lp:
             raise ValueError(f"Ensaio LP: Massa úmida ({dados.massa_umida_recipiente_lp}g) menor que massa seca ({dados.massa_seca_recipiente_lp}g).")
        if dados.massa_seca_recipiente_lp < dados.massa_recipiente_lp:
             raise ValueError(f"Ensaio LP: Massa seca ({dados.massa_seca_recipiente_lp}g) menor que massa do recipiente ({dados.massa_recipiente_lp}g).")

        massa_agua_lp = dados.massa_umida_recipiente_lp - dados.massa_seca_recipiente_lp
        massa_seca_lp = dados.massa_seca_recipiente_lp - dados.massa_recipiente_lp

        if massa_seca_lp <= 1e-9: # Evita divisão por zero
            raise ValueError(f"Ensaio LP: Massa seca calculada é zero ou negativa ({massa_seca_lp:.2f}g).")
        if massa_agua_lp < 0:
             raise ValueError(f"Ensaio LP: Massa de água calculada é negativa ({massa_agua_lp:.2f}g).")

        lp_calculado = (massa_agua_lp / massa_seca_lp) * 100 # Em porcentagem [cite: 3039]
        if lp_calculado < 0: lp_calculado = 0.0

        # --- Cálculo do Índice de Plasticidade (IP) ---
        ip_calculado = ll_calculado - lp_calculado #
        # Se IP < 0, considera-se Não Plástico (NP)
        is_np = False
        if ip_calculado < 0:
            ip_calculado = 0.0
            is_np = True # Indica que é não plástico ou LL < LP

        # --- Classificação da Plasticidade --- [cite: 3054]
        classificacao_plasticidade = None
        if is_np or np.isclose(ip_calculado, 0):
             classificacao_plasticidade = "Não Plástico (NP)"
        elif ip_calculado > 0 and ip_calculado <= 7:
            classificacao_plasticidade = "Fracamente Plástico"
        elif ip_calculado > 7 and ip_calculado <= 15:
            classificacao_plasticidade = "Medianamente Plástico"
        elif ip_calculado > 15:
            classificacao_plasticidade = "Altamente Plástico"

        # --- Cálculo do Índice de Consistência (IC) ---
        ic_calculado: Optional[float] = None
        classificacao_consistencia: Optional[str] = None
        if dados.umidade_natural is not None:
            if ip_calculado > 1e-9: # Evita divisão por zero se IP=0
                ic_calculado = (ll_calculado - dados.umidade_natural) / ip_calculado #

                # --- Classificação da Consistência ---
                if ic_calculado < 0:
                    classificacao_consistencia = "Muito Mole (líquida)" # w > LL
                elif ic_calculado >= 0 and ic_calculado < 0.5:
                    classificacao_consistencia = "Mole"
                elif ic_calculado >= 0.5 and ic_calculado < 0.75:
                    classificacao_consistencia = "Média"
                elif ic_calculado >= 0.75 and ic_calculado < 1.0:
                    classificacao_consistencia = "Rija"
                elif ic_calculado >= 1.0:
                    classificacao_consistencia = "Dura (semi-sólida/sólida)" # w < LP
            else:
                 # Se IP=0 (NP), o conceito de IC não se aplica da mesma forma.
                 # Poderia indicar "Não aplicável (solo NP)"
                 classificacao_consistencia = "Não aplicável (solo Não Plástico)"


        # --- Cálculo da Atividade da Argila (Ia) ---
        atividade_calculada: Optional[float] = None
        classificacao_atividade: Optional[str] = None
        if dados.percentual_argila is not None:
            if dados.percentual_argila < 0 or dados.percentual_argila > 100:
                 raise ValueError("Percentual de argila deve estar entre 0 e 100%.")
            if dados.percentual_argila > 1e-9: # Evita divisão por zero
                 # IP já está >= 0 aqui
                 atividade_calculada = ip_calculado / dados.percentual_argila #

                 # --- Classificação da Atividade ---
                 if atividade_calculada < 0.75:
                     classificacao_atividade = "Inativa"
                 elif atividade_calculada >= 0.75 and atividade_calculada <= 1.25:
                     classificacao_atividade = "Normal"
                 else: # Ia > 1.25
                     classificacao_atividade = "Ativa"
            elif ip_calculado > 1e-9: # Se %argila=0 mas IP>0, atividade seria infinita? Ou indefinida?
                 # Na prática, se %argila=0, o solo não deveria ter IP>0. Indica inconsistência.
                 # Poderia retornar um erro ou aviso. Vamos retornar como None.
                 pass
            else: # %argila=0 e IP=0
                 # Atividade é 0/0 (indefinido) ou simplesmente não aplicável.
                 classificacao_atividade = "Não aplicável (solo NP ou sem argila)"


        # --- Preparar Saída ---
        precisao = 2 # Duas casas decimais para os limites
        return LimitesConsistenciaOutput(
            ll=round(ll_calculado, precisao),
            lp=round(lp_calculado, precisao),
            ip=round(ip_calculado, precisao),
            ic=round(ic_calculado, precisao) if ic_calculado is not None else None,
            classificacao_plasticidade=classificacao_plasticidade,
            classificacao_consistencia=classificacao_consistencia,
            atividade_argila=round(atividade_calculada, precisao) if atividade_calculada is not None else None,
            classificacao_atividade=classificacao_atividade,
            pontos_grafico_ll=pontos_grafico_ll_log # Retorna (log_golpes, umidade)
        )

    except ValueError as ve:
        return LimitesConsistenciaOutput(erro=str(ve))
    except Exception as e:
        import traceback
        print(f"Erro inesperado no cálculo de limites de consistência: {e}\n{traceback.format_exc()}")
        return LimitesConsistenciaOutput(erro=f"Erro interno no servidor: {type(e).__name__}")