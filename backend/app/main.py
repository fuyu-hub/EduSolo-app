# backend/app/main.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.models import (
    IndicesFisicosInput, IndicesFisicosOutput,
    LimitesConsistenciaInput, LimitesConsistenciaOutput,
    CompactacaoInput, CompactacaoOutput,
    TensoesGeostaticasInput, TensoesGeostaticasOutput,
    AcrescimoTensoesInput, AcrescimoTensoesOutput,
    # Novos imports
    RecalqueAdensamentoInput, RecalqueAdensamentoOutput,
    TempoAdensamentoInput, TempoAdensamentoOutput
)
# Importa as funções de cálculo de cada módulo
from app.modules.indices_fisicos import calcular_indices_fisicos
from app.modules.limites_consistencia import calcular_limites_consistencia
from app.modules.compactacao import calcular_compactacao
from app.modules.tensoes_geostaticas import calcular_tensoes_geostaticas
from app.modules.acrescimo_tensoes import calcular_acrescimo_tensoes
# Novos imports
from app.modules.recalque_adensamento import calcular_recalque_adensamento
from app.modules.tempo_adensamento import calcular_tempo_adensamento

app = FastAPI(
    title="EduSolo API",
    description="Backend para cálculos de Mecânica dos Solos.",
    version="0.2.0" # Versão incrementada
)

# Configuração do CORS (mantida)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Endpoints ---

@app.get("/", tags=["Root"])
def read_root():
    """ Endpoint raiz para verificar se a API está online. """
    return {"message": "Bem-vindo à API do EduSolo v0.2.0"}

# --- Módulos Anteriores (mantidos) ---
@app.post("/calcular/indices-fisicos", response_model=IndicesFisicosOutput, tags=["Módulo 1: Índices Físicos"])
# ... (código do endpoint inalterado) ...
def post_calcular_indices(dados_entrada: IndicesFisicosInput):
    resultados = calcular_indices_fisicos(dados_entrada)
    if resultados.erro:
        raise HTTPException(status_code=400, detail=resultados.erro)
    return resultados

@app.post("/calcular/limites-consistencia", response_model=LimitesConsistenciaOutput, tags=["Módulo 1: Limites de Consistência"])
# ... (código do endpoint inalterado) ...
def post_calcular_limites(dados_entrada: LimitesConsistenciaInput):
    resultados = calcular_limites_consistencia(dados_entrada)
    if resultados.erro:
        raise HTTPException(status_code=400, detail=resultados.erro)
    return resultados

@app.post("/calcular/compactacao", response_model=CompactacaoOutput, tags=["Módulo 2: Compactação"])
# ... (código do endpoint inalterado) ...
def post_calcular_compactacao(dados_entrada: CompactacaoInput):
    resultados = calcular_compactacao(dados_entrada)
    if resultados.erro:
        raise HTTPException(status_code=400, detail=resultados.erro)
    return resultados

@app.post("/calcular/tensoes-geostaticas", response_model=TensoesGeostaticasOutput, tags=["Módulo 3: Tensões Geostáticas"])
# ... (código do endpoint inalterado) ...
def post_calcular_tensoes_geostaticas(dados_entrada: TensoesGeostaticasInput):
    resultados = calcular_tensoes_geostaticas(dados_entrada)
    if resultados.erro:
        raise HTTPException(status_code=400, detail=resultados.erro)
    return resultados

@app.post("/calcular/acrescimo-tensoes", response_model=AcrescimoTensoesOutput, tags=["Módulo 4: Acréscimo de Tensões"])
# ... (código do endpoint inalterado) ...
def post_calcular_acrescimo_tensoes(dados_entrada: AcrescimoTensoesInput):
    tipos_carga_presentes = [dados_entrada.carga_pontual is not None]
    if sum(tipos_carga_presentes) != 1:
        raise HTTPException(status_code=400, detail="Exatamente um tipo de dados de carga (ex: carga_pontual) deve ser fornecido.")
    resultados = calcular_acrescimo_tensoes(dados_entrada)
    if resultados.erro:
        raise HTTPException(status_code=400, detail=resultados.erro)
    return resultados

# --- Novos Módulos: Adensamento ---

@app.post("/calcular/recalque-adensamento", response_model=RecalqueAdensamentoOutput, tags=["Módulo 5: Recalque por Adensamento"])
def post_calcular_recalque(dados_entrada: RecalqueAdensamentoInput):
    """
    Calcula o recalque total por adensamento primário (ΔH) para uma camada
    compressível, considerando o estado de adensamento (NA ou PA).
    """
    resultados = calcular_recalque_adensamento(dados_entrada)
    if resultados.erro:
        raise HTTPException(status_code=400, detail=resultados.erro)
    return resultados

@app.post("/calcular/tempo-adensamento", response_model=TempoAdensamentoOutput, tags=["Módulo 6: Tempo de Adensamento"])
def post_calcular_tempo_adensamento(dados_entrada: TempoAdensamentoInput):
    """
    Analisa o tempo de adensamento primário.
    Recebe recalque total, Cv, Hd e OU tempo (t) OU grau de adensamento (Uz).
    Retorna o tempo para atingir Uz ou o recalque/Uz atingido no tempo t.
    """
    resultados = calcular_tempo_adensamento(dados_entrada)
    if resultados.erro:
        raise HTTPException(status_code=400, detail=resultados.erro)
    return resultados


# --- Para executar (na pasta backend): uvicorn app.main:app --reload ---