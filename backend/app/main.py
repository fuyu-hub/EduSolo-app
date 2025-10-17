from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.models import (
    IndicesFisicosInput, IndicesFisicosOutput,
    LimitesConsistenciaInput, LimitesConsistenciaOutput,
    CompactacaoInput, CompactacaoOutput,
    TensoesGeostaticasInput, TensoesGeostaticasOutput,
    AcrescimoTensoesInput, AcrescimoTensoesOutput
)
# Importa as funções de cálculo de cada módulo
from app.modules.indices_fisicos import calcular_indices_fisicos
from app.modules.limites_consistencia import calcular_limites_consistencia
from app.modules.compactacao import calcular_compactacao
from app.modules.tensoes_geostaticas import calcular_tensoes_geostaticas
from app.modules.acrescimo_tensoes import calcular_acrescimo_tensoes

app = FastAPI(
    title="EduSolo API",
    description="Backend para cálculos de Mecânica dos Solos - MVP.",
    version="0.1.0" # Versão inicial
)

# Configuração do CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Em produção, restrinja para o domínio do frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Endpoints ---

@app.get("/", tags=["Root"])
def read_root():
    """ Endpoint raiz para verificar se a API está online. """
    return {"message": "Bem-vindo à API do EduSolo"}

# --- Módulo 1: Índices Físicos e Limites de Consistência ---

@app.post("/calcular/indices-fisicos", response_model=IndicesFisicosOutput, tags=["Módulo 1: Índices Físicos"])
def post_calcular_indices(dados_entrada: IndicesFisicosInput):
    """
    Recebe dados de entrada (pelo menos uma combinação válida) e retorna
    os Índices Físicos calculados. As unidades de entrada devem ser consistentes
    (ex: g e cm³ ou kN e m³). A saída será em kN/m³, adimensional ou %.
    """
    resultados = calcular_indices_fisicos(dados_entrada)
    if resultados.erro:
        # Retorna um erro HTTP 400 (Bad Request) se houver erro de cálculo/validação
        raise HTTPException(status_code=400, detail=resultados.erro)
    return resultados

@app.post("/calcular/limites-consistencia", response_model=LimitesConsistenciaOutput, tags=["Módulo 1: Limites de Consistência"])
def post_calcular_limites(dados_entrada: LimitesConsistenciaInput):
    """
    Recebe os dados dos ensaios de LL e LP (e opcionais w_nat, %argila)
    e retorna os Limites de Atterberg e índices derivados.
    """
    resultados = calcular_limites_consistencia(dados_entrada)
    if resultados.erro:
        raise HTTPException(status_code=400, detail=resultados.erro)
    return resultados

# --- Módulo 2: Compactação ---

@app.post("/calcular/compactacao", response_model=CompactacaoOutput, tags=["Módulo 2: Compactação"])
def post_calcular_compactacao(dados_entrada: CompactacaoInput):
    """
    Recebe os dados dos pontos do ensaio de compactação (Proctor)
    e retorna a umidade ótima (w_ot), peso específico seco máximo (γd,max)
    e os pontos para as curvas de compactação e saturação (S=100%).
    """
    resultados = calcular_compactacao(dados_entrada)
    if resultados.erro:
        raise HTTPException(status_code=400, detail=resultados.erro)
    return resultados

# --- Módulo 3: Tensões Geostáticas ---

@app.post("/calcular/tensoes-geostaticas", response_model=TensoesGeostaticasOutput, tags=["Módulo 3: Tensões Geostáticas"])
def post_calcular_tensoes_geostaticas(dados_entrada: TensoesGeostaticasInput):
    """
    Calcula o perfil de tensões totais, neutras e efetivas (vertical e horizontal)
    para um solo estratificado, considerando o NA e capilaridade.
    Retorna os valores em pontos chave (superfície, interfaces, NA, base).
    """
    resultados = calcular_tensoes_geostaticas(dados_entrada)
    if resultados.erro:
        raise HTTPException(status_code=400, detail=resultados.erro)
    return resultados

# --- Módulo 4: Acréscimo de Tensões ---

@app.post("/calcular/acrescimo-tensoes", response_model=AcrescimoTensoesOutput, tags=["Módulo 4: Acréscimo de Tensões"])
def post_calcular_acrescimo_tensoes(dados_entrada: AcrescimoTensoesInput):
    """
    Calcula o acréscimo de tensão vertical (Δσv) em um ponto de interesse
    devido a uma carga aplicada na superfície.
    MVP: Suporta apenas tipo_carga='pontual' (Boussinesq).
    """
    # Validação extra: Garante que apenas um tipo de carga seja fornecido
    tipos_carga_presentes = [
        dados_entrada.carga_pontual is not None,
        # dados_entrada.carga_retangular is not None, # Descomentar quando implementar
        # dados_entrada.carga_circular is not None,
        # dados_entrada.carga_faixa is not None,
    ]
    if sum(tipos_carga_presentes) != 1:
        raise HTTPException(status_code=400, detail="Exatamente um tipo de dados de carga (ex: carga_pontual) deve ser fornecido.")

    resultados = calcular_acrescimo_tensoes(dados_entrada)
    if resultados.erro:
        raise HTTPException(status_code=400, detail=resultados.erro)
    return resultados


# --- Para executar (na pasta backend): uvicorn app.main:app --reload ---