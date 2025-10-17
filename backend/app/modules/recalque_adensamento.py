# backend/app/modules/recalque_adensamento.py
import numpy as np
from app.models import RecalqueAdensamentoInput, RecalqueAdensamentoOutput
from typing import Optional

EPSILON = 1e-9 # Pequena tolerância

def calcular_recalque_adensamento(dados: RecalqueAdensamentoInput) -> RecalqueAdensamentoOutput:
    """
    Calcula o recalque total por adensamento primário (ΔH) para uma camada
    de solo compressível, com base na Teoria de Terzaghi.

    Considera se o solo é Normalmente Adensado (NA) ou Pré-Adensado (PA).

    Referências:
    - PDF: 11.2. Recalques_por_adensamento_Junho_2022-1.pdf (Págs. 12-16)
    - PDF: 11.1. Compressibilidade_e_Recalque_rotated-1.pdf
    """
    try:
        # Extrai dados de entrada
        H0 = dados.espessura_camada
        e0 = dados.indice_vazios_inicial
        Cc = dados.Cc
        Cr = dados.Cr
        sigma_v0_prime = dados.tensao_efetiva_inicial
        sigma_vm_prime = dados.tensao_pre_adensamento
        delta_sigma_prime = dados.acrescimo_tensao

        # Validações básicas
        if H0 <= 0 or e0 <= 0 or Cc <= 0 or Cr <= 0 or sigma_v0_prime <= 0 or sigma_vm_prime <= 0 or delta_sigma_prime < 0:
            raise ValueError("Valores de entrada inválidos (espessura, e0, Cc, Cr, tensões devem ser positivos, Δσ' >= 0).")
        if 1 + e0 <= EPSILON:
             raise ValueError("Índice de vazios inicial (e0) inválido.")
        if Cr > Cc:
            # Não é um erro fatal, mas um aviso pode ser útil
            # print("Aviso: Cr (Índice de Recompressão) é maior que Cc (Índice de Compressão).")
            pass

        # Calcula tensão efetiva final
        sigma_vf_prime = sigma_v0_prime + delta_sigma_prime

        # Calcula Razão de Pré-Adensamento (RPA ou OCR)
        RPA = sigma_vm_prime / sigma_v0_prime

        # Determina o estado de adensamento e calcula a deformação volumétrica (εv)
        epsilon_v: float = 0.0
        estado_adensamento: str = ""

        # Caso 1: Solo Normalmente Adensado (NA)
        # Consideramos NA se RPA estiver próximo de 1 (ex: entre 0.95 e 1.1)
        if abs(RPA - 1.0) < 0.1: # Tolerância para considerar NA
            estado_adensamento = "Normalmente Adensado (RPA ≈ 1)"
            if sigma_v0_prime <= EPSILON: raise ValueError("Tensão efetiva inicial não pode ser zero para solo NA.")
            epsilon_v = (Cc / (1 + e0)) * np.log10(sigma_vf_prime / sigma_v0_prime) #

        # Caso 2: Solo Pré-Adensado (PA)
        elif RPA > 1.0:
            estado_adensamento = "Pré-Adensado (RPA > 1)"
            # Caso 2a: Tensão final NÃO excede a tensão de pré-adensamento
            if sigma_vf_prime <= sigma_vm_prime:
                if sigma_v0_prime <= EPSILON: raise ValueError("Tensão efetiva inicial não pode ser zero.")
                epsilon_v = (Cr / (1 + e0)) * np.log10(sigma_vf_prime / sigma_v0_prime) #
            # Caso 2b: Tensão final EXCEDE a tensão de pré-adensamento
            else:
                 if sigma_v0_prime <= EPSILON or sigma_vm_prime <= EPSILON:
                      raise ValueError("Tensões inicial e de pré-adensamento devem ser maiores que zero.")
                 # Deformação na faixa de recompressão + deformação na faixa virgem
                 epsilon_v = (Cr / (1 + e0)) * np.log10(sigma_vm_prime / sigma_v0_prime) + \
                             (Cc / (1 + e0)) * np.log10(sigma_vf_prime / sigma_vm_prime) #

        # Caso 3: Solo Sub-Adensado (RPA < 1) - Menos comum, tratar como NA?
        else: # RPA < 1 (considerando a tolerância anterior)
             estado_adensamento = "Sub-Adensado (RPA < 1) - Cálculo como Normalmente Adensado"
             # O cálculo é similar ao NA, mas o estado inicial já está na curva virgem
             if sigma_v0_prime <= EPSILON: raise ValueError("Tensão efetiva inicial não pode ser zero.")
             epsilon_v = (Cc / (1 + e0)) * np.log10(sigma_vf_prime / sigma_v0_prime)

        # Calcula o recalque total primário
        recalque_total = epsilon_v * H0 #

        return RecalqueAdensamentoOutput(
            recalque_total_primario=round(recalque_total, 4), # Em metros, 4 casas decimais
            deformacao_volumetrica=round(epsilon_v, 5),
            tensao_efetiva_final=round(sigma_vf_prime, 2),
            estado_adensamento=estado_adensamento,
            RPA=round(RPA, 2)
        )

    except ValueError as ve:
        return RecalqueAdensamentoOutput(erro=str(ve))
    except Exception as e:
        print(f"Erro inesperado no cálculo de recalque: {e}")
        return RecalqueAdensamentoOutput(erro=f"Erro interno no servidor: {type(e).__name__}")