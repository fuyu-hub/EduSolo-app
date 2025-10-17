from pydantic import BaseModel, Field
from typing import Optional, List

# --- Modelos Gerais ---

class PontoCurva(BaseModel):
    """ Representa um ponto (x, y) genérico para gráficos """
    x: float
    y: float

class PontoCurvaCompactacao(BaseModel):
    """ Representa um ponto (umidade, peso_especifico_seco) para gráficos de compactação """
    umidade: float
    peso_especifico_seco: float

# --- Modelos Módulo 1: Índices Físicos ---

class IndicesFisicosInput(BaseModel):
    """
    Define os dados de entrada para o cálculo de Índices Físicos.
    Permite diferentes combinações de entradas.
    """
    peso_total: Optional[float] = Field(None, description="Peso total da amostra (ex: g)")
    volume_total: Optional[float] = Field(None, description="Volume total da amostra (ex: cm³)")
    peso_solido: Optional[float] = Field(None, description="Peso dos sólidos (seco) (ex: g)")
    peso_especifico_solidos: Optional[float] = Field(None, description="Peso específico dos grãos/sólidos (Gs * γw) (ex: g/cm³ ou kN/m³)")
    Gs: Optional[float] = Field(None, description="Densidade relativa dos grãos (adimensional)")
    umidade: Optional[float] = Field(None, description="Teor de umidade (w) em porcentagem (%)")
    indice_vazios: Optional[float] = Field(None, description="Índice de vazios (e) (adimensional)")
    porosidade: Optional[float] = Field(None, description="Porosidade (n) em porcentagem (%)")
    grau_saturacao: Optional[float] = Field(None, description="Grau de saturação (S) em porcentagem (%)")
    peso_especifico_natural: Optional[float] = Field(None, description="Peso específico natural (γnat) (ex: kN/m³)")
    peso_especifico_seco: Optional[float] = Field(None, description="Peso específico seco (γd) (ex: kN/m³)")
    peso_especifico_agua: float = Field(10.0, description="Peso específico da água (γw) (ex: kN/m³)")

class IndicesFisicosOutput(BaseModel):
    """
    Define a estrutura de dados para os resultados dos Índices Físicos.
    Retorna todos os índices calculáveis, com unidades consistentes (kN/m³ ou adimensional/%).
    """
    peso_especifico_natural: Optional[float] = Field(None, description="γnat (kN/m³)")
    peso_especifico_seco: Optional[float] = Field(None, description="γd (kN/m³)")
    peso_especifico_saturado: Optional[float] = Field(None, description="γsat (kN/m³)")
    peso_especifico_submerso: Optional[float] = Field(None, description="γsub ou γ' (kN/m³)")
    peso_especifico_solidos: Optional[float] = Field(None, description="γs (kN/m³)")
    Gs: Optional[float] = Field(None, description="Densidade relativa dos grãos (adimensional)")
    indice_vazios: Optional[float] = Field(None, description="e (adimensional)")
    porosidade: Optional[float] = Field(None, description="n (%)")
    grau_saturacao: Optional[float] = Field(None, description="S (%)")
    umidade: Optional[float] = Field(None, description="w (%)")
    # Componentes para diagrama de fases normalizado (Vs=1)
    volume_solidos_norm: Optional[float] = Field(None, description="Vs normalizado (Vs=1)")
    volume_agua_norm: Optional[float] = Field(None, description="Vw normalizado (para Vs=1)")
    volume_ar_norm: Optional[float] = Field(None, description="Va normalizado (para Vs=1)")
    peso_solidos_norm: Optional[float] = Field(None, description="Ws normalizado (para Vs=1, em g se γw_gcm3=1)")
    peso_agua_norm: Optional[float] = Field(None, description="Ww normalizado (para Vs=1, em g se γw_gcm3=1)")
    erro: Optional[str] = None # Para mensagens de erro

# --- Modelos Módulo 1: Limites de Consistência ---

class PontoEnsaioLL(BaseModel):
    """ Dados de um ponto do ensaio de Limite de Liquidez (Casagrande) """
    num_golpes: int = Field(..., gt=0)
    massa_umida_recipiente: float = Field(..., description="Massa do recipiente + solo úmido (g)")
    massa_seca_recipiente: float = Field(..., description="Massa do recipiente + solo seco (g)")
    massa_recipiente: float = Field(..., description="Massa do recipiente (g)")

class LimitesConsistenciaInput(BaseModel):
    """ Dados de entrada para cálculo dos Limites de Atterberg """
    pontos_ll: List[PontoEnsaioLL] = Field(..., min_items=2, description="Lista de pontos do ensaio de LL (pelo menos 2)")
    massa_umida_recipiente_lp: float = Field(..., description="Massa do recipiente + solo úmido (g) - Ensaio LP")
    massa_seca_recipiente_lp: float = Field(..., description="Massa do recipiente + solo seco (g) - Ensaio LP")
    massa_recipiente_lp: float = Field(..., description="Massa do recipiente (g) - Ensaio LP")
    umidade_natural: Optional[float] = Field(None, description="Teor de umidade natural atual do solo in situ (%)")
    percentual_argila: Optional[float] = Field(None, ge=0, le=100, description="Percentual de argila (< 0.002mm) na amostra (%)")

class LimitesConsistenciaOutput(BaseModel):
    """ Resultados dos Limites de Atterberg e índices derivados """
    ll: Optional[float] = Field(None, description="Limite de Liquidez (%)")
    lp: Optional[float] = Field(None, description="Limite de Plasticidade (%)")
    ip: Optional[float] = Field(None, description="Índice de Plasticidade (%)")
    ic: Optional[float] = Field(None, description="Índice de Consistência (adimensional)")
    classificacao_plasticidade: Optional[str] = None
    classificacao_consistencia: Optional[str] = None
    atividade_argila: Optional[float] = Field(None, description="Índice de Atividade (Ia) (adimensional)")
    classificacao_atividade: Optional[str] = None
    pontos_grafico_ll: Optional[List[PontoCurva]] = Field(None, description="Pontos (log_golpes, umidade) calculados para gráfico LL")
    erro: Optional[str] = None

# --- Modelos Módulo 2: Compactação ---

class PontoEnsaioCompactacao(BaseModel):
    """ Dados de um ponto do ensaio de compactação """
    massa_umida_total: float = Field(..., description="Massa do solo úmido + molde (ex: g ou kg)")
    massa_molde: float = Field(..., description="Massa do molde (ex: g ou kg)")
    volume_molde: float = Field(..., gt=0, description="Volume do molde (ex: cm³ ou m³)")
    # Dados para cálculo da umidade
    massa_umida_recipiente_w: float = Field(..., description="Massa do recipiente + amostra úmida para umidade (g)")
    massa_seca_recipiente_w: float = Field(..., description="Massa do recipiente + amostra seca para umidade (g)")
    massa_recipiente_w: float = Field(..., description="Massa do recipiente para umidade (g)")

class CompactacaoInput(BaseModel):
    """ Dados de entrada para análise do Ensaio de Compactação """
    pontos_ensaio: List[PontoEnsaioCompactacao] = Field(..., min_items=3, description="Lista de pontos do ensaio (pelo menos 3)")
    Gs: Optional[float] = Field(None, gt=0, description="Densidade relativa dos grãos (Gs > 0), necessária para curva de saturação")
    peso_especifico_agua: float = Field(10.0, gt=0, description="Peso específico da água (γw) (ex: kN/m³)")

class CompactacaoOutput(BaseModel):
    """ Resultados da análise de Compactação """
    umidade_otima: Optional[float] = Field(None, description="w_ot (%)")
    peso_especifico_seco_max: Optional[float] = Field(None, description="γd,max (kN/m³)")
    pontos_curva_compactacao: Optional[List[PontoCurvaCompactacao]] = Field(None, description="Pontos (w, γd) calculados do ensaio")
    pontos_curva_saturacao_100: Optional[List[PontoCurvaCompactacao]] = Field(None, description="Pontos (w, γd) para a curva S=100%")
    # Adicionar curvas S=90%, S=80% etc. se necessário
    # pontos_curva_saturacao_90: Optional[List[PontoCurvaCompactacao]] = None
    # pontos_curva_saturacao_80: Optional[List[PontoCurvaCompactacao]] = None
    erro: Optional[str] = None

# --- Modelos Módulo 3: Tensões Geostáticas ---

class CamadaSolo(BaseModel):
    """ Define as propriedades de uma camada de solo """
    espessura: float = Field(..., gt=0, description="Espessura da camada (m)")
    gama_nat: Optional[float] = Field(None, description="Peso específico natural (kN/m³) - Acima do NA")
    gama_sat: Optional[float] = Field(None, description="Peso específico saturado (kN/m³) - Abaixo do NA")
    Ko: float = Field(0.5, ge=0, description="Coeficiente de empuxo em repouso (adimensional)") # Valor default comum

class TensaoPonto(BaseModel):
    """ Armazena os valores de tensão em uma profundidade específica """
    profundidade: float
    tensao_total_vertical: Optional[float] = None
    pressao_neutra: Optional[float] = None
    tensao_efetiva_vertical: Optional[float] = None
    tensao_efetiva_horizontal: Optional[float] = None

class TensoesGeostaticasInput(BaseModel):
    """ Dados de entrada para o cálculo de Tensões Geostáticas """
    camadas: List[CamadaSolo] = Field(..., min_items=1, description="Lista das camadas de solo, da superfície para baixo")
    profundidade_na: float = Field(..., ge=0, description="Profundidade do Nível d'Água (NA) a partir da superfície (m). Usar 0 se na superfície.")
    altura_capilar: float = Field(0.0, ge=0, description="Altura da franja capilar acima do NA (m)")
    peso_especifico_agua: float = Field(10.0, gt=0, description="Peso específico da água (γw) (kN/m³)")

class TensoesGeostaticasOutput(BaseModel):
    """ Resultados do cálculo de Tensões Geostáticas """
    pontos_calculo: List[TensaoPonto] = Field(..., description="Lista de tensões calculadas em profundidades chave")
    erro: Optional[str] = None

# --- Modelos Módulo 4: Acréscimo de Tensões ---

class PontoInteresse(BaseModel):
    """ Coordenadas (x, y, z) de um ponto onde se quer calcular o acréscimo de tensão """
    x: float
    y: float
    z: float = Field(..., gt=0, description="Profundidade (deve ser > 0)") # Z positivo para baixo

class CargaPontual(BaseModel):
    """ Define uma carga pontual """
    x: float = Field(0.0, description="Coordenada X da carga na superfície")
    y: float = Field(0.0, description="Coordenada Y da carga na superfície")
    P: float = Field(..., gt=0, description="Magnitude da carga pontual (ex: kN)")

# --- Modelos Módulo 5: Recalque por Adensamento Primário ---

class RecalqueAdensamentoInput(BaseModel):
    """ Dados de entrada para o cálculo do Recalque por Adensamento Primário """
    espessura_camada: float = Field(..., gt=0, description="Espessura inicial da camada compressível (H0) em metros")
    indice_vazios_inicial: float = Field(..., gt=0, description="Índice de vazios inicial (e0) no centro da camada")
    Cc: float = Field(..., gt=0, description="Índice de Compressão (adimensional)")
    Cr: float = Field(..., gt=0, description="Índice de Recompressão (ou Expansão, Cs) (adimensional)")
    tensao_efetiva_inicial: float = Field(..., gt=0, description="Tensão efetiva vertical inicial no centro da camada (σ'v0) em kPa")
    tensao_pre_adensamento: float = Field(..., gt=0, description="Tensão de pré-adensamento no centro da camada (σ'vm ou σ'p) em kPa")
    acrescimo_tensao: float = Field(..., ge=0, description="Acréscimo de tensão efetiva vertical no centro da camada (Δσ'v) em kPa")

class RecalqueAdensamentoOutput(BaseModel):
    """ Resultados do cálculo de Recalque por Adensamento Primário """
    recalque_total_primario: Optional[float] = Field(None, description="Recalque total calculado (ΔH) em metros")
    deformacao_volumetrica: Optional[float] = Field(None, description="Deformação volumétrica vertical (εv) em decimal")
    tensao_efetiva_final: Optional[float] = Field(None, description="Tensão efetiva vertical final (σ'vf) em kPa")
    estado_adensamento: Optional[str] = Field(None, description="Classificação (Normalmente Adensado, Pré-Adensado)")
    RPA: Optional[float] = Field(None, description="Razão de Pré-Adensamento (OCR)")
    erro: Optional[str] = None

# --- Modelos Módulo 6: Tempo de Adensamento ---

class TempoAdensamentoInput(BaseModel):
    """ Dados de entrada para análise do Tempo de Adensamento """
    recalque_total_primario: float = Field(..., gt=0, description="Recalque total primário (ΔH) calculado previamente (metros)")
    coeficiente_adensamento: float = Field(..., gt=0, description="Coeficiente de adensamento vertical (Cv) (ex: m²/ano ou m²/s)")
    altura_drenagem: float = Field(..., gt=0, description="Maior percurso da água até uma camada drenante (Hd) (metros)")
    tempo: Optional[float] = Field(None, ge=0, description="Tempo decorrido desde a aplicação da carga (mesma unidade de tempo de Cv)")
    grau_adensamento_medio: Optional[float] = Field(None, ge=0, le=100, description="Grau de adensamento médio desejado (Uz) em %")

class TempoAdensamentoOutput(BaseModel):
    """ Resultados da análise de Tempo de Adensamento """
    tempo_calculado: Optional[float] = Field(None, description="Tempo calculado para atingir Uz (mesma unidade de tempo de Cv)")
    recalque_no_tempo: Optional[float] = Field(None, description="Recalque ocorrido no tempo t (metros)")
    grau_adensamento_medio_calculado: Optional[float] = Field(None, description="Grau de adensamento médio (Uz) atingido no tempo t (%)")
    fator_tempo: Optional[float] = Field(None, description="Fator tempo (Tv) adimensional")
    erro: Optional[str] = None

class AcrescimoTensoesInput(BaseModel):
    """ Dados de entrada para cálculo de acréscimo de tensões """
    tipo_carga: str = Field(..., description="Tipo de carga ('pontual', 'retangular', 'circular', 'faixa')")
    ponto_interesse: PontoInteresse = Field(..., description="Ponto onde calcular o acréscimo")
    # Apenas um dos tipos de carga deve ser fornecido
    carga_pontual: Optional[CargaPontual] = None
    # carga_retangular: Optional[CargaRetangular] = None
    # carga_circular: Optional[CargaCircular] = None
    # carga_faixa: Optional[CargaFaixa] = None

class AcrescimoTensoesOutput(BaseModel):
    """ Resultado do cálculo de acréscimo de tensão vertical """
    delta_sigma_v: Optional[float] = Field(None, description="Acréscimo de tensão vertical (Δσv) no ponto (ex: kPa)")
    metodo: Optional[str] = None
    erro: Optional[str] = None