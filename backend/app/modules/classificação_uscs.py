# backend/app/modules/classificacao_uscs.py
from typing import Dict, Optional, Tuple
# Importa os modelos Pydantic definidos em app/models.py
from app.models import ClassificacaoUSCSInput, ClassificacaoUSCSOutput

EPSILON = 1e-9

def classificar_uscs(dados: ClassificacaoUSCSInput) -> ClassificacaoUSCSOutput:
    """
    Classifica o solo de acordo com o Sistema Unificado de Classificação de Solos (USCS).

    Args:
        dados: Objeto ClassificacaoUSCSInput contendo os parâmetros necessários.

    Returns:
        Um objeto ClassificacaoUSCSOutput com a classificação e descrição ou erro.

    Referências:
    - PDF: 6. Classificao_dos_Solos_2022.pdf (Págs. 6-14)
    """
    try:
        # Extrai dados de entrada
        pass_peneira_200 = dados.pass_peneira_200
        pass_peneira_4 = dados.pass_peneira_4
        ll = dados.ll
        ip = dados.ip
        Cu = dados.Cu
        Cc = dados.Cc
        is_organico_fino = dados.is_organico_fino # Se é OL/OH
        is_altamente_organico = dados.is_altamente_organico # Se é Pt

        # --- Validações Iniciais ---
        if not (0 <= pass_peneira_200 <= 100):
            raise ValueError("Percentagem passando na #200 deve estar entre 0 e 100.")
        if not (0 <= pass_peneira_4 <= 100):
            raise ValueError("Percentagem passando na #4 deve estar entre 0 e 100.")
        if pass_peneira_200 > pass_peneira_4:
             raise ValueError("Percentagem passando na #200 não pode ser maior que a #4.")

        # --- Verificação Inicial: Solo Altamente Orgânico (Turfa) ---
        if is_altamente_organico:
             return ClassificacaoUSCSOutput(
                 classificacao="Pt",
                 descricao="Turfa e outros solos altamente orgânicos"
             ) #

        # --- Determina se é Solo Grosso ou Fino ---
        if pass_peneira_200 < 50: # Solo Grosso
            percent_grosso = 100.0 - pass_peneira_200
            percent_areia_total = pass_peneira_4 - pass_peneira_200
            percent_pedregulho_total = 100.0 - pass_peneira_4

            # É Pedregulho (G) ou Areia (S)? Verifica qual fração predomina
            is_pedregulho = percent_pedregulho_total > percent_areia_total
            prefixo_principal = "G" if is_pedregulho else "S"

            # --- Sub-classificação do Solo Grosso ---
            # Caso 1: Poucos finos (< 5%)
            if pass_peneira_200 < 5:
                if Cu is None or Cc is None:
                     raise ValueError("Cu e Cc são necessários para classificar solos grossos com menos de 5% de finos.")

                # Verifica critérios de Bem Graduado (W)
                bem_graduado = False
                if is_pedregulho:
                    if Cu >= 4 and 1 <= Cc <= 3: bem_graduado = True # Critério GW
                else: # É Areia
                     if Cu >= 6 and 1 <= Cc <= 3: bem_graduado = True # Critério SW

                sufixo_secundario = "W" if bem_graduado else "P"
                descricao = f"{'Pedregulho' if is_pedregulho else 'Areia'} {'bem graduado(a)' if bem_graduado else 'mal graduado(a)'}, {'com pouca ou nenhuma finos'}"
                classificacao = prefixo_principal + sufixo_secundario

            # Caso 2: Muitos finos (> 12%)
            elif pass_peneira_200 > 12:
                 if ll is None or ip is None:
                     raise ValueError("LL e IP são necessários para classificar solos grossos com mais de 12% de finos.")
                 if ll < 0 or ip < 0:
                     raise ValueError("LL e IP não podem ser negativos.")

                 # Usa Carta de Plasticidade para classificar a fração fina
                 acima_linha_A, tipo_fino = _classificar_finos_carta(ll, ip)

                 if tipo_fino is None: # IP inválido ou LL muito baixo (NP ou na zona hachurada)
                      # A USCS classifica como GM ou SM se cair na zona hachurada (IP<4 ou abaixo A)
                      if ip < 4 or (0.73 * (ll - 20)) > ip :
                          tipo_fino = "M"
                      else:
                          # Se está acima da linha A mas IP < 4? Ou na linha A com IP < 4?
                          # Esta condição é rara ou impossível pela definição da linha A.
                          raise ValueError("Valores de LL e IP inconsistentes para classificação dos finos (acima da Linha A mas IP < 4).")


                 sufixo_secundario = tipo_fino # M ou C
                 classificacao = prefixo_principal + sufixo_secundario
                 descricao = f"{'Pedregulho' if is_pedregulho else 'Areia'} {'siltoso(a)' if tipo_fino == 'M' else 'argiloso(a)'}"

            # Caso 3: Finos entre 5% e 12% (Classificação Dupla)
            else:
                 if ll is None or ip is None or Cu is None or Cc is None:
                     raise ValueError("LL, IP, Cu e Cc são necessários para classificação dupla (5-12% de finos).")
                 if ll < 0 or ip < 0 or Cu < 0 or Cc < 0:
                      raise ValueError("LL, IP, Cu e Cc não podem ser negativos.")

                 # Determina sufixo W ou P
                 bem_graduado = False
                 if is_pedregulho:
                     if Cu >= 4 and 1 <= Cc <= 3: bem_graduado = True
                 else:
                     if Cu >= 6 and 1 <= Cc <= 3: bem_graduado = True
                 sufixo_graduacao = "W" if bem_graduado else "P"

                 # Determina sufixo M ou C
                 acima_linha_A, tipo_fino = _classificar_finos_carta(ll, ip)
                 if tipo_fino is None:
                     if ip < 4 or (0.73 * (ll - 20)) > ip : tipo_fino = "M"
                     else: raise ValueError("Valores de LL e IP inconsistentes para classificação dupla.")
                 sufixo_plasticidade = tipo_fino

                 classificacao = f"{prefixo_principal}{sufixo_graduacao}-{prefixo_principal}{sufixo_plasticidade}"
                 descricao = f"{'Pedregulho' if is_pedregulho else 'Areia'} {'bem graduado(a)' if bem_graduado else 'mal graduado(a)'} {'com silte' if tipo_fino == 'M' else 'com argila'}"

        else: # Solo Fino (>= 50% passando #200)
             if ll is None or ip is None:
                 raise ValueError("LL e IP são necessários para classificar solos finos.")
             if ll < 0 or ip < 0:
                  raise ValueError("LL e IP não podem ser negativos.")

             # Determina sufixo L ou H
             sufixo_plasticidade = "L" if ll < 50 else "H"

             # Verifica se é Orgânico (OL/OH) ou Inorgânico (ML/CL/MH/CH)
             if is_organico_fino:
                 prefixo_final = "O"
                 descricao_tipo = "Solo Orgânico"
             else:
                 acima_linha_A, tipo_principal = _classificar_finos_carta(ll, ip)
                 if tipo_principal is None:
                      # Se caiu na zona hachurada (IP<4 ou abaixo A com IP<7) -> ML ou OL
                      if ip < 4 or (0.73 * (ll - 20)) > ip :
                          prefixo_final = "M" # Assume ML/MH
                          descricao_tipo = "Silte"
                      else:
                          raise ValueError("Valores de LL e IP inconsistentes para classificação de solo fino.")
                 else:
                      prefixo_final = tipo_principal # M ou C
                      descricao_tipo = "Silte" if prefixo_final == 'M' else "Argila"


             classificacao = f"{prefixo_final}{sufixo_plasticidade}"
             descricao_plast = "baixa plasticidade/compressibilidade" if sufixo_plasticidade == 'L' else "alta plasticidade/compressibilidade"
             descricao = f"{descricao_tipo} de {descricao_plast}"


        return ClassificacaoUSCSOutput(classificacao=classificacao, descricao=descricao)

    except ValueError as ve:
        return ClassificacaoUSCSOutput(erro=str(ve))
    except Exception as e:
        print(f"Erro inesperado na classificação USCS: {e}")
        return ClassificacaoUSCSOutput(erro=f"Erro interno no servidor: {type(e).__name__}")


def _classificar_finos_carta(ll: float, ip: float) -> Tuple[Optional[bool], Optional[str]]:
    """
    Classifica a fração fina (M ou C) usando a Carta de Plasticidade de Casagrande.
    Retorna (acima_linha_A, tipo_fino).
    Retorna (None, None) se cair na zona hachurada ou dados inválidos.
    """
    if ll < 0 or ip < 0: return None, None # Valores não podem ser negativos

    # Linha A
    ip_linha_A = 0.73 * (ll - 20)

    # Verifica zona hachurada (IP < 4 OU IP < IP_linha_A)
    # A zona CL-ML (4 <= IP <= 7 e abaixo da linha A) é tratada separadamente pela classificação dupla em solos grossos,
    # mas para solos finos, cai abaixo da linha A e é M (ML/MH) ou O (OL/OH).
    if ip < 4 or ip < ip_linha_A:
        return False, "M" # Assume Silte (M) ou Orgânico (O) se abaixo da linha A ou IP<4

    # Se chegou aqui, está acima ou na linha A e IP >= 4
    # Se está na linha A (IP == IP_linha_A) ou acima, classifica como Argila (C)
    return True, "C"