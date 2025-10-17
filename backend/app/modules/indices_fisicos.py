import numpy as np
from app.models import IndicesFisicosInput, IndicesFisicosOutput
from typing import Optional

# Definindo uma pequena tolerância para evitar divisão por zero em alguns casos
EPSILON = 1e-9

def calcular_indices_fisicos(dados: IndicesFisicosInput) -> IndicesFisicosOutput:
    """
    Calcula as propriedades e índices físicos do solo a partir de diferentes
    combinações de dados de entrada, utilizando as relações fundamentais.
    Prioriza cálculos mais diretos e tenta derivar o máximo de informações.
    Retorna os resultados em unidades consistentes (kN/m³, adimensional ou %).

    Referências Principais:
    - PDF: 4. Indices_Fisicos_2022-Maro.pdf
    """
    try:
        # Inicializa variáveis a partir dos dados de entrada
        # Converte percentagens para decimais para cálculos
        w: Optional[float] = dados.umidade / 100 if dados.umidade is not None else None
        n: Optional[float] = dados.porosidade / 100 if dados.porosidade is not None else None
        S: Optional[float] = dados.grau_saturacao / 100 if dados.grau_saturacao is not None else None

        # Dados diretos
        e: Optional[float] = dados.indice_vazios
        gs: Optional[float] = dados.Gs
        gama_s: Optional[float] = dados.peso_especifico_solidos
        gama_nat: Optional[float] = dados.peso_especifico_natural
        gama_d: Optional[float] = dados.peso_especifico_seco
        gama_w: float = dados.peso_especifico_agua # Peso específico da água (ex: 10 kN/m³)

        # Variáveis calculadas
        gama_sat: Optional[float] = None
        gama_sub: Optional[float] = None

        # --- Lógica de Cálculo em Cascata ---

        # 0. Consistência entre Gs e gama_s
        if gs is None and gama_s is not None:
            gs = gama_s / gama_w # [cite: 1672]
        elif gama_s is None and gs is not None:
            gama_s = gs * gama_w # [cite: 1672]
        elif gs is not None and gama_s is not None:
            # Se ambos forem fornecidos, verifica a consistência (opcional)
             if not np.isclose(gama_s, gs * gama_w, rtol=1e-3):
                 return IndicesFisicosOutput(erro=f"Gs ({gs}) e Peso Específico dos Sólidos ({gama_s} kN/m³) são inconsistentes para γw={gama_w} kN/m³.")

        # 1. Relações básicas entre e e n
        if e is None and n is not None:
            if 1 - n == 0: raise ValueError("Porosidade (n) não pode ser 100%")
            e = n / (1 - n) # 
        elif n is None and e is not None:
            if 1 + e == 0: raise ValueError("Índice de Vazios (e) inválido")
            n = e / (1 + e) # 

        # 2. Relação fundamental: Se = w * Gs
        # Tenta calcular S
        if S is None and w is not None and gs is not None and e is not None:
             if e <= EPSILON: S = 0.0 # Se não há vazios, não há saturação
             else: S = (w * gs) / e # 
             if S > 1.0 + EPSILON: # Verifica se S não ultrapassa ~100%
                 # Pode indicar inconsistência nos dados de entrada
                 S = 1.0 # Limita a 100% mas pode ser um aviso
             elif S < 0.0:
                 S = 0.0 # Limita a 0%
        # Tenta calcular e
        elif e is None and w is not None and gs is not None and S is not None:
            if S <= EPSILON:
                # Se S=0, e pode ser qualquer valor > 0, não é possível determinar 'e'
                # A menos que w=0, aí S=0 para qualquer 'e'.
                if w > EPSILON: raise ValueError("Saturação (S) não pode ser 0 se a umidade (w) for maior que 0.")
                # Se w=0, não conseguimos calcular 'e' por aqui
            else:
                e = (w * gs) / S # 
        # Tenta calcular w
        elif w is None and S is not None and e is not None and gs is not None:
             if gs <= EPSILON: raise ValueError("Gs não pode ser zero para calcular umidade (w).")
             w = (S * e) / gs # 
        # Não tentamos calcular Gs por aqui, assumindo que é um parâmetro mais fundamental

        # Recalcula 'n' se 'e' foi calculado
        if n is None and e is not None:
             if 1 + e == 0: raise ValueError("Índice de Vazios (e) inválido")
             n = e / (1 + e) # 

        # 3. Relações com Pesos Específicos
        # γd = γnat / (1+w)
        if gama_d is None and gama_nat is not None and w is not None:
             if 1 + w == 0: raise ValueError("Umidade (w) inválida (-100%)")
             gama_d = gama_nat / (1 + w) # 
        elif gama_nat is None and gama_d is not None and w is not None:
             gama_nat = gama_d * (1 + w) # 

        # γd = Gs * γw / (1+e)
        if gama_d is None and gs is not None and e is not None:
             if 1 + e == 0: raise ValueError("Índice de Vazios (e) inválido")
             gama_d = (gs * gama_w) / (1 + e) # 
        elif e is None and gama_d is not None and gs is not None:
             if gama_d <= EPSILON: # Se gama_d é 0, ou Gs=0 ou e=infinito. Assume e=infinito se Gs>0
                 e = float('inf') if gs > EPSILON else None # Não podemos determinar e se Gs=0 e gama_d=0
             else:
                 e = (gs * gama_w) / gama_d - 1 # 
                 if e < 0: # Fisicamente impossível
                      raise ValueError("Cálculo resultou em índice de vazios negativo. Verifique γd e Gs.")

        # γnat = γw * (Gs + S*e) / (1+e)
        if gama_nat is None and gs is not None and e is not None and S is not None:
             if 1 + e == 0: raise ValueError("Índice de Vazios (e) inválido")
             gama_nat = gama_w * (gs + S * e) / (1 + e) # 
        # Tentar calcular S a partir de γnat
        elif S is None and gama_nat is not None and gs is not None and e is not None:
             if abs(e) <= EPSILON: # Se e=0, S=0 (ou indefinido, mas 0 faz sentido físico)
                 S = 0.0
             elif gama_w * e == 0: raise ValueError("Erro de divisão por zero ao tentar calcular S.")
             else:
                 S = (gama_nat * (1 + e) - gs * gama_w) / (gama_w * e) #  rearranjada
                 if S > 1.0 + EPSILON: S = 1.0 # Limita
                 elif S < 0.0: S = 0.0         # Limita


        # Tentar calcular w a partir de γnat e γd
        if w is None and gama_nat is not None and gama_d is not None:
             if gama_d <= EPSILON: # Se gama_d=0, ou w infinito ou gama_nat=0.
                 w = float('inf') if gama_nat > EPSILON else 0.0
             else:
                 w = (gama_nat / gama_d) - 1 #  rearranjada

        # Se 'e' foi calculado, recalcular 'n'
        if n is None and e is not None:
             if 1 + e == 0: raise ValueError("Índice de Vazios (e) inválido")
             n = e / (1 + e) # 

        # Se 'w' foi calculado, tentar calcular 'S' se ainda não foi
        if S is None and w is not None and gs is not None and e is not None:
             if e <= EPSILON: S = 0.0
             else: S = (w * gs) / e # 
             if S > 1.0 + EPSILON: S = 1.0
             elif S < 0.0: S = 0.0

        # 4. Cálculo de γsat e γsub
        if gama_sat is None:
             if gs is not None and e is not None:
                 if 1 + e == 0: raise ValueError("Índice de Vazios (e) inválido")
                 gama_sat = gama_w * (gs + e) / (1 + e) # [cite: 1787]
             elif gama_d is not None and e is not None: # Usando S=1 na eq. γnat
                 if 1 + e == 0: raise ValueError("Índice de Vazios (e) inválido")
                 # Derivação: γsat = γd(1+w_sat); w_sat = e/Gs; γd = Gs*γw/(1+e) => γsat = [Gs*γw/(1+e)]*(1+e/Gs) = Gs*γw/(1+e) + e*γw/(1+e) = γw(Gs+e)/(1+e)
                 # Se não tivermos Gs, não podemos usar w_sat diretamente
                 # Mas podemos usar γnat = γw(Gs+Se)/(1+e). Para S=1, γsat = γw(Gs+e)/(1+e)
                 # E γd = Gs*γw/(1+e) => Gs = γd(1+e)/γw
                 # Substituindo Gs: γsat = γw * [ (γd(1+e)/γw) + e ] / (1+e) = (γd(1+e) + e*γw) / (1+e) = γd + e*γw/(1+e)
                 gama_sat = gama_d + (e * gama_w / (1 + e))


        if gama_sub is None and gama_sat is not None:
            gama_sub = gama_sat - gama_w # [cite: 1648]

        # --- Verificações Finais e Preparação da Saída ---

        # Arredondamento (opcional, pode ser feito no frontend)
        precisao_gama = 2
        precisao_indice = 3
        precisao_perc = 1

        gama_nat = round(gama_nat, precisao_gama) if gama_nat is not None else None
        gama_d = round(gama_d, precisao_gama) if gama_d is not None else None
        gama_sat = round(gama_sat, precisao_gama) if gama_sat is not None else None
        gama_sub = round(gama_sub, precisao_gama) if gama_sub is not None else None
        gama_s = round(gama_s, precisao_gama) if gama_s is not None else None
        gs = round(gs, precisao_indice) if gs is not None else None
        e = round(e, precisao_indice) if e is not None else None
        w_out = round(w * 100, precisao_perc) if w is not None else None
        n_out = round(n * 100, precisao_perc) if n is not None else None
        S_out = round(S * 100, precisao_perc) if S is not None else None


        # Dados para Diagrama de Fases (Vs=1) 
        vol_s_norm = 1.0
        peso_s_norm: Optional[float] = None
        vol_v_norm: Optional[float] = None
        vol_w_norm: Optional[float] = None
        peso_w_norm: Optional[float] = None
        vol_a_norm: Optional[float] = None

        if gs is not None:
             # Usa γw em g/cm³ para consistência com pesos em g
             gama_w_gcm3 = gama_w / 9.81 if np.isclose(gama_w, 9.81, rtol=1e-2) else gama_w / 10.0 # Aproximação se γw=10
             peso_s_norm = round(gs * gama_w_gcm3 * vol_s_norm, 2) # Peso = Gs * γw * Vs

        if e is not None:
            vol_v_norm = round(e * vol_s_norm, precisao_indice)

            if S is not None:
                 vol_w_norm = round(S * vol_v_norm, precisao_indice) # Vw = S * Vv
                 vol_a_norm = round(vol_v_norm - vol_w_norm, precisao_indice) # Va = Vv - Vw
                 if vol_a_norm < 0: vol_a_norm = 0.0 # Corrige pequenas imprecisões

                 if vol_w_norm is not None:
                     peso_w_norm = round(vol_w_norm * gama_w_gcm3, 2) # Peso = Vw * γw

            # Tenta calcular Vw a partir de w e Ws
            elif w is not None and peso_s_norm is not None:
                 peso_w_norm = round(w * peso_s_norm, 2) # Pw = w * Ps
                 vol_w_norm = round(peso_w_norm / gama_w_gcm3, precisao_indice) # Vw = Pw / γw
                 vol_a_norm = round(vol_v_norm - vol_w_norm, precisao_indice)
                 if vol_a_norm < 0: vol_a_norm = 0.0


        return IndicesFisicosOutput(
            peso_especifico_natural=gama_nat,
            peso_especifico_seco=gama_d,
            peso_especifico_saturado=gama_sat,
            peso_especifico_submerso=gama_sub,
            peso_especifico_solidos=gama_s,
            Gs=gs,
            indice_vazios=e,
            porosidade=n_out,
            grau_saturacao=S_out,
            umidade=w_out,
            # Diagrama de fases normalizado
            volume_solidos_norm=vol_s_norm,
            volume_agua_norm=vol_w_norm,
            volume_ar_norm=vol_a_norm,
            peso_solidos_norm=peso_s_norm,
            peso_agua_norm=peso_w_norm
        )

    except ValueError as ve: # Captura erros de lógica/dados inconsistentes
         return IndicesFisicosOutput(erro=str(ve))
    except Exception as e: # Captura outros erros inesperados
        # Logar o erro completo no servidor seria ideal aqui
        print(f"Erro inesperado no cálculo de índices físicos: {e}")
        return IndicesFisicosOutput(erro=f"Erro interno no servidor durante o cálculo: {type(e).__name__}")