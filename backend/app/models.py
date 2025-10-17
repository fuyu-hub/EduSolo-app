# backend/app/models.py
from pydantic import BaseModel, Field, validator
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
    # ... (inalterado) ...
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
    # ... (inalterado) ...
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
    volume_solidos_norm: Optional[float] = Field(None, description="Vs normalizado (Vs=1)")
    volume_agua_norm: Optional[float] = Field(None, description="Vw normalizado (para Vs=1)")
    volume_ar_norm: Optional[float] = Field(None, description="Va normalizado (para Vs=1)")
    peso_solidos_norm: Optional[float] = Field(None, description="Ws normalizado (para Vs=1, em g se γw_gcm3=1)")
    peso_agua_norm: Optional[float] = Field(None, description="Ww normalizado (para Vs=1, em g se γw_gcm3=1)")
    erro: Optional[str] = None

# --- Modelos Módulo 1: Limites de Consistência ---
class PontoEnsaioLL(BaseModel):
    # ... (inalterado) ...
    num_golpes: int = Field(..., gt=0)
    massa_umida_recipiente: float = Field(..., description="Massa do recipiente + solo úmido (g)")
    massa_seca_recipiente: float = Field(..., description="Massa do recipiente + solo seco (g)")
    massa_recipiente: float = Field(..., description="Massa do recipiente (g)")

class LimitesConsistenciaInput(BaseModel):
    # ... (inalterado) ...
    pontos_ll: List[PontoEnsaioLL] = Field(..., min_items=2, description="Lista de pontos do ensaio de LL (pelo menos 2)")
    massa_umida_recipiente_lp: float = Field(..., description="Massa do recipiente + solo úmido (g) - Ensaio LP")
    massa_seca_recipiente_lp: float = Field(..., description="Massa do recipiente + solo seco (g) - Ensaio LP")
    massa_recipiente_lp: float = Field(..., description="Massa do recipiente (g) - Ensaio LP")
    umidade_natural: Optional[float] = Field(None, description="Teor de umidade natural atual do solo in situ (%)")
    percentual_argila: Optional[float] = Field(None, ge=0, le=100, description="Percentual de argila (< 0.002mm) na amostra (%)")

class LimitesConsistenciaOutput(BaseModel):
    # ... (inalterado) ...
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
    # ... (inalterado) ...
    massa_umida_total: float = Field(..., description="Massa do solo úmido + molde (ex: g ou kg)")
    massa_molde: float = Field(..., description="Massa do molde (ex: g ou kg)")
    volume_molde: float = Field(..., gt=0, description="Volume do molde (ex: cm³ ou m³)")
    massa_umida_recipiente_w: float = Field(..., description="Massa do recipiente + amostra úmida para umidade (g)")
    massa_seca_recipiente_w: float = Field(..., description="Massa do recipiente + amostra seca para umidade (g)")
    massa_recipiente_w: float = Field(..., description="Massa do recipiente para umidade (g)")

class CompactacaoInput(BaseModel):
    # ... (inalterado) ...
    pontos_ensaio: List[PontoEnsaioCompactacao] = Field(..., min_items=3, description="Lista de pontos do ensaio (pelo menos 3)")
    Gs: Optional[float] = Field(None, gt=0, description="Densidade relativa dos grãos (Gs > 0), necessária para curva de saturação")
    peso_especifico_agua: float = Field(10.0, gt=0, description="Peso específico da água (γw) (ex: kN/m³)")

class CompactacaoOutput(BaseModel):
    # ... (inalterado) ...
    umidade_otima: Optional[float] = Field(None, description="w_ot (%)")
    peso_especifico_seco_max: Optional[float] = Field(None, description="γd,max (kN/m³)")
    pontos_curva_compactacao: Optional[List[PontoCurvaCompactacao]] = Field(None, description="Pontos (w, γd) calculados do ensaio")
    pontos_curva_saturacao_100: Optional[List[PontoCurvaCompactacao]] = Field(None, description="Pontos (w, γd) para a curva S=100%")
    erro: Optional[str] = None

# --- Modelos Módulo 3: Tensões Geostáticas ---
class CamadaSolo(BaseModel):
    # ... (inalterado) ...
    espessura: float = Field(..., gt=0, description="Espessura da camada (m)")
    gama_nat: Optional[float] = Field(None, description="Peso específico natural (kN/m³) - Acima do NA")
    gama_sat: Optional[float] = Field(None, description="Peso específico saturado (kN/m³) - Abaixo do NA")
    Ko: float = Field(0.5, ge=0, description="Coeficiente de empuxo em repouso (adimensional)")

class TensaoPonto(BaseModel):
    # ... (inalterado) ...
    profundidade: float
    tensao_total_vertical: Optional[float] = None
    pressao_neutra: Optional[float] = None
    tensao_efetiva_vertical: Optional[float] = None
    tensao_efetiva_horizontal: Optional[float] = None

class TensoesGeostaticasInput(BaseModel):
    # ... (inalterado) ...
    camadas: List[CamadaSolo] = Field(..., min_items=1, description="Lista das camadas de solo, da superfície para baixo")
    profundidade_na: float = Field(..., ge=0, description="Profundidade do Nível d'Água (NA) a partir da superfície (m). Usar 0 se na superfície.")
    altura_capilar: float = Field(0.0, ge=0, description="Altura da franja capilar acima do NA (m)")
    peso_especifico_agua: float = Field(10.0, gt=0, description="Peso específico da água (γw) (kN/m³)")

class TensoesGeostaticasOutput(BaseModel):
    # ... (inalterado) ...
    pontos_calculo: List[TensaoPonto] = Field(...)
    erro: Optional[str] = None

# --- Modelos Módulo 4: Acréscimo de Tensões ---
class PontoInteresse(BaseModel):
    # ... (inalterado) ...
    x: float
    y: float
    z: float = Field(..., gt=0)

class CargaPontual(BaseModel):
    # ... (inalterado) ...
    x: float = Field(0.0)
    y: float = Field(0.0)
    P: float = Field(..., gt=0)

# NOVOS MODELOS PARA CARGAS ADICIONAIS
class CargaFaixa(BaseModel):
    """ Define uma carga em faixa infinita """
    largura: float = Field(..., gt=0, description="Largura da faixa (b) (ex: m)")
    intensidade: float = Field(..., gt=0, description="Pressão uniforme aplicada (p) (ex: kPa)")
    centro_x: float = Field(0.0, description="Coordenada X do centro da faixa na superfície") # Opcional, assume 0

class CargaCircular(BaseModel):
    """ Define uma carga circular uniforme """
    raio: float = Field(..., gt=0, description="Raio da área circular (R) (ex: m)")
    intensidade: float = Field(..., gt=0, description="Pressão uniforme aplicada (p) (ex: kPa)")
    centro_x: float = Field(0.0, description="Coordenada X do centro do círculo na superfície") # Opcional
    centro_y: float = Field(0.0, description="Coordenada Y do centro do círculo na superfície") # Opcional

# Adicionar CargaRetangular aqui quando implementar Newmark

class AcrescimoTensoesInput(BaseModel):
    """ Dados de entrada para cálculo de acréscimo de tensões (ATUALIZADO) """
    tipo_carga: str = Field(..., description="Tipo de carga ('pontual', 'faixa', 'circular')") # Adicionado 'faixa', 'circular'
    ponto_interesse: PontoInteresse = Field(...)
    carga_pontual: Optional[CargaPontual] = None
    carga_faixa: Optional[CargaFaixa] = None
    carga_circular: Optional[CargaCircular] = None
    # carga_retangular: Optional[CargaRetangular] = None

class AcrescimoTensoesOutput(BaseModel):
    # ... (inalterado) ...
    delta_sigma_v: Optional[float] = Field(None, description="Acréscimo de tensão vertical (Δσv) no ponto (ex: kPa)")
    metodo: Optional[str] = None
    erro: Optional[str] = None

# --- Modelos Módulo 5: Recalque por Adensamento Primário ---
class RecalqueAdensamentoInput(BaseModel):
    # ... (inalterado) ...
    espessura_camada: float = Field(..., gt=0)
    indice_vazios_inicial: float = Field(..., gt=0)
    Cc: float = Field(..., gt=0)
    Cr: float = Field(..., gt=0)
    tensao_efetiva_inicial: float = Field(..., gt=0)
    tensao_pre_adensamento: float = Field(..., gt=0)
    acrescimo_tensao: float = Field(..., ge=0)

class RecalqueAdensamentoOutput(BaseModel):
    # ... (inalterado) ...
    recalque_total_primario: Optional[float] = None
    deformacao_volumetrica: Optional[float] = None
    tensao_efetiva_final: Optional[float] = None
    estado_adensamento: Optional[str] = None
    RPA: Optional[float] = None
    erro: Optional[str] = None

# --- Modelos Módulo 6: Tempo de Adensamento ---
class TempoAdensamentoInput(BaseModel):
    # ... (inalterado) ...
    recalque_total_primario: float = Field(..., gt=0)
    coeficiente_adensamento: float = Field(..., gt=0)
    altura_drenagem: float = Field(..., gt=0)
    tempo: Optional[float] = Field(None, ge=0)
    grau_adensamento_medio: Optional[float] = Field(None, ge=0, le=100)

class TempoAdensamentoOutput(BaseModel):
    # ... (inalterado) ...
    tempo_calculado: Optional[float] = None
    recalque_no_tempo: Optional[float] = None
    grau_adensamento_medio_calculado: Optional[float] = None
    fator_tempo: Optional[float] = None
    erro: Optional[str] = None

# --- Modelos Módulo 7: Fluxo Hidráulico ---

class CamadaFluxo(BaseModel):
    """ Propriedades de uma camada para análise de fluxo """
    espessura: float = Field(..., gt=0)
    k: float = Field(..., ge=0, description="Coeficiente de permeabilidade (kx ou kz, ex: m/s)")
    n: Optional[float] = Field(None, gt=0, lt=1, description="Porosidade (0 < n < 1)")
    gamma_sat: Optional[float] = Field(None, gt=0, description="Peso específico saturado (kN/m³)")

class FluxoHidraulicoInput(BaseModel):
    """ Dados de entrada para análise de fluxo hidráulico 1D """
    camadas: List[CamadaFluxo] = Field(..., min_items=1)
    # Para permeabilidade equivalente
    direcao_permeabilidade_equivalente: Optional[str] = Field(None, description="'horizontal' ou 'vertical'")
    # Para cálculo de velocidades
    gradiente_hidraulico_aplicado: Optional[float] = Field(None, ge=0, description="Gradiente hidráulico médio (i)")
    # Para tensões com fluxo
    profundidades_tensao: Optional[List[float]] = Field(None, description="Lista de profundidades para calcular tensões (m)")
    profundidade_na_entrada: Optional[float] = Field(None, ge=0, description="Profundidade do NA a montante (m)")
    profundidade_na_saida: Optional[float] = Field(None, ge=0, description="Profundidade do NA a jusante (m)")
    direcao_fluxo_vertical: Optional[str] = Field(None, description="'ascendente' ou 'descendente'")
    peso_especifico_agua: float = Field(10.0, gt=0, description="γw (kN/m³)")

class TensaoPontoFluxo(BaseModel):
    """ Armazena os valores de tensão e carga num ponto sob fluxo """
    profundidade: float
    tensao_total_vertical: Optional[float] = None
    pressao_neutra: Optional[float] = None
    tensao_efetiva_vertical: Optional[float] = None
    carga_hidraulica_total: Optional[float] = None # ht = u/gamma_w + Z_elev

class FluxoHidraulicoOutput(BaseModel):
    """ Resultados da análise de fluxo hidráulico 1D """
    permeabilidade_equivalente: Optional[float] = Field(None, description="Coeficiente de permeabilidade equivalente (k_eq)")
    velocidade_descarga: Optional[float] = Field(None, description="Velocidade de descarga (v = ki)")
    velocidade_fluxo: Optional[float] = Field(None, description="Velocidade de fluxo/percolação (vf = v/n)")
    gradiente_critico: Optional[float] = Field(None, description="Gradiente hidráulico crítico (icrit = γ'/γw)")
    fs_liquefacao: Optional[float] = Field(None, description="Fator de segurança contra liquefação (FS = icrit / i_ascendente)")
    pontos_tensao_fluxo: Optional[List[TensaoPontoFluxo]] = Field(None, description="Tensões calculadas em diferentes profundidades sob fluxo")
    erro: Optional[str] = None

# --- Modelos Módulo 8: Classificação USCS ---

class ClassificacaoUSCSInput(BaseModel):
    """ Dados de entrada para classificação USCS """
    pass_peneira_200: float = Field(..., ge=0, le=100, description="% passando na peneira #200 (0.075mm)")
    pass_peneira_4: float = Field(..., ge=0, le=100, description="% passando na peneira #4 (4.75mm)")
    ll: Optional[float] = Field(None, ge=0, description="Limite de Liquidez (%)")
    ip: Optional[float] = Field(None, ge=0, description="Índice de Plasticidade (%)")
    Cu: Optional[float] = Field(None, ge=0, description="Coeficiente de Uniformidade (D60/D10)")
    Cc: Optional[float] = Field(None, ge=0, description="Coeficiente de Curvatura (D30²/ (D10*D60))")
    is_organico_fino: bool = Field(False, description="Indica se é solo fino orgânico (OL/OH)")
    is_altamente_organico: bool = Field(False, description="Indica se é Turfa (Pt)")

    @validator('ip')
    def check_ip_ll(cls, ip, values):
        ll = values.get('ll')
        if ll is not None and ip is not None and ip > ll:
            #raise ValueError("Índice de Plasticidade (IP) não pode ser maior que o Limite de Liquidez (LL).")
             # Permitir IP > LL para capturar o erro na lógica de classificação se necessário,
             # ou pode levantar erro aqui. O módulo de limites já deve prevenir IP<0.
             pass
        return ip

    @validator('pass_peneira_200')
    def check_p200_p4(cls, p200, values):
         p4 = values.get('pass_peneira_4')
         if p4 is not None and p200 > p4:
              raise ValueError("Percentagem passando na #200 não pode ser maior que a #4.")
         return p200

class ClassificacaoUSCSOutput(BaseModel):
    """ Resultado da classificação USCS """
    classificacao: Optional[str] = Field(None, description="Símbolo do grupo USCS (ex: SW, CL, GP-GC)")
    descricao: Optional[str] = Field(None, description="Descrição do grupo (ex: Areia bem graduada, Argila de baixa plasticidade)")
    erro: Optional[str] = None