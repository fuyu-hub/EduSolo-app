import math
import os
import sys

# Ajusta o caminho para permitir importações do pacote 'app'
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import post_analisar_fluxo  # noqa: E402
from app.models import CamadaFluxo, FluxoHidraulicoInput  # noqa: E402


def test_fluxo_hidraulico_fs_liquefacao_finito_sem_erros():
    dados_entrada = FluxoHidraulicoInput(
        camadas=[
            CamadaFluxo(espessura=2.0, k=1e-5, n=0.35, gamma_sat=18.5),
            CamadaFluxo(espessura=3.0, k=5e-6, n=0.38, gamma_sat=19.6),
        ],
        direcao_permeabilidade_equivalente="vertical",
        gradiente_hidraulico_aplicado=0.8,
        profundidades_tensao=[0.0, 2.0, 5.0],
        profundidade_na_entrada=6.0,
        profundidade_na_saida=1.0,
        direcao_fluxo_vertical="ascendente",
        peso_especifico_agua=10.0,
    )

    resultado = post_analisar_fluxo(dados_entrada)

    assert resultado.fs_liquefacao is not None
    assert math.isfinite(resultado.fs_liquefacao)
    assert resultado.erro in (None, "")
