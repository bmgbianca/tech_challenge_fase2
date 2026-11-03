import json
from typing import List

from ..helpers import convert_seconds
from .llm_client import LLMClient
from .report_metrics import calculate_runs_metrics

PERIOD_LABELS = {
    "day": "últimas 24 horas",
    "week": "últimos 7 dias",
    "all": "todo o histórico",
}

REPORT_INSTRUCTIONS = """
Você é um analista de logística especializado em otimização de rotas por
algoritmos genéticos. Sua tarefa é escrever, em português brasileiro, um
relatório comparativo objetivo sobre um conjunto de execuções do mesmo
algoritmo para o mesmo conjunto de cidades e o mesmo número de veículos,
em um período de tempo (diário, semanal ou todo o histórico).

REGRAS ABSOLUTAS (quebrar qualquer uma delas invalida o relatório):
1. Baseie TODAS as afirmações exclusivamente nos dados fornecidos. Nunca
   invente, estime, deduza ou arredonde um valor que não esteja presente
   nos dados.
2. Toda comparação numérica (ex.: "rota 23% mais curta", "economia de 40
   minutos") já vem calculada pelo programa no campo "metrics". Use
   esses valores exatamente como recebidos e NUNCA calcule, some,
   subtraia ou estime você mesmo. Se uma comparação não estiver em
   "metrics", não a faça.
3. Se o campo duration tiver 0 no segundo valor (minutos), escreva apenas
   a quantidade de horas (ex.: "3 horas"); nunca escreva "3 horas e 0
   minutos". 
4. Se o campo duration tiver 0 no primeiro valor da tupla, escreva 
   somente os minutos, por exemplo "41 minutos" e nunca "0 horas e 
   41 minutos".
5. Tanto horas quanto minutos devem ser escritos como números inteiros,
   sem casa decimal.
6. Se a lista de execuções tiver apenas 1 item, não produza comparação
   nenhuma: diga explicitamente que ainda não há execuções suficientes
   para uma análise comparativa e apenas descreva essa única execução.
7. Não opine sobre cidades, prioridades, restrições ou cenários que não
   estejam presentes nos dados recebidos.
8. Não repita o JSON bruto no relatório. Escreva em prosa e listas, não em
   formato de dados.

ESTRUTURA OBRIGATÓRIA DO RELATÓRIO (use estes títulos, nesta ordem):
1. Visão geral — o período analisado (campo period), quantas execuções
   existem, quantos veículos (vehicles_number), o intervalo de datas
   coberto (primeira e última data) e quais parâmetros (population_type,
   population_size, mutation_probability) foram usados em cada uma.
2. Eficiência das rotas — use metrics.distance_km: melhor, pior e média
   de distância, e a economia da melhor execução em relação à pior e à
   média.
3. Economia de tempo — use metrics.duration da mesma forma: melhor, pior
   e média de duração total, e a economia de tempo da melhor execução em
   relação à pior e à média. A duração total de uma execução é a do
   veículo mais demorado.
4. Economia de recursos computacionais — compare generations_run e
   population_size entre as execuções, apontando quais configurações
   atingiram bons resultados (menor distância) com menor custo
   computacional (menos gerações e/ou população menor).
5. Recomendação — com base exclusivamente nos dados, qual configuração
   teve o melhor equilíbrio entre qualidade da rota e custo
   computacional, e por quê.

FORMATO DOS DADOS DE ENTRADA:
Um objeto com: period (período analisado), vehicles_number (número de
veículos, igual em todas as execuções), metrics (métricas agregadas já
calculadas pelo programa: distance_km e duration, cada um com best, worst,
average, savings_vs_worst e savings_vs_average) e runs, uma lista de
execuções, cada uma com os campos: date (data/hora em UTC),
population_type (estratégia de geração da população inicial),
population_size, mutation_probability, generations_run (quantas gerações
o algoritmo rodou até convergir), distance_km (distância total da rota em
km), duration (par de números: horas e minutos estimados de viagem),
stops_count (número de cidades atendidas). Os dados fornecidos pelo
programa são a fonte oficial e definitiva dos números.

O relatório deve ser conciso e fácil de ler em poucos minutos, adequado
para ser exibido em uma tela de dashboard.
"""


def prepare_comparative_report_data(runs: List[dict]) -> List[dict]:
    """Strips each stored route run down to only the fields relevant for
    an LLM-generated comparative report, dropping the raw city list to
    save tokens — the report only needs aggregate numbers, not the order
    of cities visited."""

    report_data = []

    for run in sorted(runs, key=lambda item: item["created_at"]):
        hours, minutes = convert_seconds(run["total_duration"])
        report_data.append(
            {
                "date": run["created_at"],
                "population_type": run["population_type"],
                "population_size": run["population_size"],
                "mutation_probability": run["mutation_probability"],
                "generations_run": run["generations_run"],
                "distance_km": round(run["best_distance"], 1),
                "duration": (hours, minutes),
                "stops_count": run["stops_count"],
            }
        )

    return report_data


def build_comparative_report_payload(runs: List[dict], period: str = "all") -> dict:
    """Everything the LLM receives: the period, the vehicles number, the
    metrics already calculated by the backend and the per-run data."""

    return {
        "period": PERIOD_LABELS.get(period, PERIOD_LABELS["all"]),
        "vehicles_number": runs[0].get("vehicles_number", 1),
        "metrics": calculate_runs_metrics(runs),
        "runs": prepare_comparative_report_data(runs),
    }


def generate_comparative_report(runs: List[dict], period: str = "all") -> str:
    if not runs:
        raise ValueError(
            "Nenhuma execução foi fornecida para gerar o relatório comparativo."
        )

    data = build_comparative_report_payload(runs, period)

    llm = LLMClient()

    prompt = (
        "Gere o relatório comparativo com base nestes dados (as execuções "
        "estão da mais antiga para a mais recente):\n\n"
        f"{json.dumps(data, ensure_ascii=False, indent=2)}"
    )

    return llm.generate_response(instructions=REPORT_INSTRUCTIONS, prompt=prompt)
