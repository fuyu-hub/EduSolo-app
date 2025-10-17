import numpy as np
from typing import List, Tuple, Optional
from app.models import CompactacaoInput, CompactacaoOutput, PontoEnsaioCompactacao, PontoCurva

# Precisaremos do numpy para a interpolação polinomial
# Certifique-se que numpy está em requirements.txt e instalado

def calcular_compactacao(dados: CompactacaoInput) -> CompactacaoOutput:
    """
    Analisa os dados do ensaio de compactação de Proctor.
    Calcula o peso específico seco para cada ponto, ajusta uma curva
    polinomial para encontrar a umidade ótima (w_ot) e o peso
    específico seco máximo (γd,max).
    Calcula também a curva de saturação S=100%.

    Retorna os resultados e pontos para plotagem dos gráficos.
    """
    try:
        pontos_calculados: List[PontoCurva] = []
        gama_w = dados.peso_especifico_agua # kN/m³
        # γw em g/cm³ para consistência com massas em g e volume em cm³
        gama_w_gcm3 = gama_w / 9.81 if np.isclose(gama_w, 9.81, rtol=1e-2) else gama_w / 10.0

        if dados.Gs is not None and dados.Gs <= 0:
            raise ValueError("Gs (Densidade relativa dos grãos) deve ser maior que zero.")
        if gama_w <= 0:
             raise ValueError("Peso específico da água deve ser maior que zero.")

        for i, ponto in enumerate(dados.pontos_ensaio):
            # Validações básicas
            if ponto.volume_molde <= 0:
                raise ValueError(f"Volume do molde inválido ({ponto.volume_molde}) no ponto {i+1}.")
            if ponto.massa_molde < 0:
                 raise ValueError(f"Massa do molde inválida ({ponto.massa_molde}) no ponto {i+1}.")
            if ponto.massa_umida_total < ponto.massa_molde:
                 raise ValueError(f"Massa úmida total ({ponto.massa_umida_total}) menor que a massa do molde ({ponto.massa_molde}) no ponto {i+1}.")

            # Cálculo da Umidade (w) para o ponto
            massa_agua_w = ponto.massa_umida_recipiente_w - ponto.massa_seca_recipiente_w
            massa_seca_w = ponto.massa_seca_recipiente_w - ponto.massa_recipiente_w
            if massa_seca_w <= 0:
                raise ValueError(f"Massa seca inválida ({massa_seca_w}) no cálculo de umidade do ponto {i+1}.")
            if massa_agua_w < 0:
                 raise ValueError(f"Massa de água negativa ({massa_agua_w}) no cálculo de umidade do ponto {i+1}.")

            umidade_decimal = massa_agua_w / massa_seca_w # w em decimal
            umidade_percentual = umidade_decimal * 100

            # Cálculo do Peso Específico Seco (γd) para o ponto
            massa_solo_umido = ponto.massa_umida_total - ponto.massa_molde
            # Assume entrada em g e cm³, calcula γh em g/cm³
            gama_h_gcm3 = massa_solo_umido / ponto.volume_molde
            # Converte γh para kN/m³
            gama_h_knm3 = gama_h_gcm3 * gama_w / gama_w_gcm3 # Regra de três: (g/cm³) * (kN/m³ / (g/cm³))

            gama_d = gama_h_knm3 / (1 + umidade_decimal) # γd = γh / (1 + w)

            pontos_calculados.append(PontoCurva(umidade=umidade_percentual, peso_especifico_seco=gama_d))

        if len(pontos_calculados) < 3:
            return CompactacaoOutput(pontos_curva_compactacao=pontos_calculados, erro="São necessários pelo menos 3 pontos para traçar a curva de compactação.")

        # Ordena os pontos pela umidade para a interpolação
        pontos_calculados.sort(key=lambda p: p.umidade)

        umidades = np.array([p.umidade for p in pontos_calculados])
        gamas_d = np.array([p.peso_especifico_seco for p in pontos_calculados])

        # Ajuste polinomial (grau 2 ou 3 é geralmente suficiente)
        # Grau 3 pode capturar melhor a assimetria, mas pode oscilar com poucos pontos
        grau_polinomio = 3 if len(pontos_calculados) >= 4 else 2
        try:
             coeffs = np.polyfit(umidades, gamas_d, grau_polinomio)
             poly = np.poly1d(coeffs)

             # Encontra o máximo da curva polinomial
             # Derivada do polinômio
             deriv = poly.deriv()
             # Raízes da derivada (pontos críticos)
             critical_points = deriv.roots
             # Filtra raízes reais dentro do intervalo de umidade do ensaio
             real_roots = critical_points[np.isreal(critical_points)].real
             valid_roots = real_roots[(real_roots >= umidades.min()) & (real_roots <= umidades.max())]

             if len(valid_roots) > 0:
                 # Calcula a segunda derivada para verificar se é máximo
                 second_deriv = deriv.deriv()
                 # Avalia a segunda derivada nos pontos críticos válidos
                 second_deriv_values = second_deriv(valid_roots)
                 # Encontra o índice onde a segunda derivada é negativa (ponto de máximo)
                 max_indices = np.where(second_deriv_values < 0)[0]

                 if len(max_indices) > 0:
                     # Pega a umidade correspondente ao primeiro máximo encontrado
                     w_ot = valid_roots[max_indices[0]]
                     gd_max = poly(w_ot)
                 else: # Se não houver máximo claro (talvez pontos mal distribuídos)
                      # Pega o ponto mais alto dos dados originais como aproximação
                      max_idx = np.argmax(gamas_d)
                      w_ot = umidades[max_idx]
                      gd_max = gamas_d[max_idx]
             else: # Se nenhuma raiz estiver no intervalo, pega o máximo dos pontos originais
                 max_idx = np.argmax(gamas_d)
                 w_ot = umidades[max_idx]
                 gd_max = gamas_d[max_idx]

        except (np.linalg.LinAlgError, ValueError):
            # Se o ajuste falhar, retorna erro ou usa o ponto máximo medido
             max_idx = np.argmax(gamas_d)
             w_ot = umidades[max_idx]
             gd_max = gamas_d[max_idx]
             # Poderia adicionar uma mensagem de aviso aqui

        # --- Cálculo da Curva de Saturação S=100% ---
        pontos_saturacao_100 = []
        if dados.Gs is not None:
            # Gera um intervalo de umidades para plotar a curva S=100%
            # Começa um pouco antes da menor umidade medida e vai até um pouco depois da maior
            w_min_plot = max(0, umidades.min() - 5)
            w_max_plot = umidades.max() + 10
            umidades_plot = np.linspace(w_min_plot, w_max_plot, 20) # 20 pontos para a curva

            for w_p in umidades_plot:
                w_dec = w_p / 100.0
                # Fórmula da curva de S=100%: γd = Gs * γw / (1 + Gs * w)
                denominador = (1 + dados.Gs * w_dec)
                if abs(denominador) > EPSILON:
                     gd_sat = (dados.Gs * gama_w) / denominador
                     pontos_saturacao_100.append(PontoCurva(umidade=w_p, peso_especifico_seco=gd_sat))

        return CompactacaoOutput(
            umidade_otima=round(w_ot, 2),
            peso_especifico_seco_max=round(gd_max, 3), # Mais precisão para γd
            pontos_curva_compactacao=pontos_calculados,
            pontos_curva_saturacao_100=pontos_saturacao_100 if pontos_saturacao_100 else None
        )

    except ValueError as ve:
         return CompactacaoOutput(erro=str(ve))
    except Exception as e:
        print(f"Erro inesperado no cálculo de compactação: {e}")
        # Logar o traceback completo seria útil
        return CompactacaoOutput(erro=f"Erro interno no servidor: {type(e).__name__}")