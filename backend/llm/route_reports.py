import json
from typing import List

from ..config import convert_seconds
from .llm_client import LLMClient

REPORT_INSTRUCTIONS = """
Você é um analista de logística especializado em otimização de rotas por
algoritmos genéticos. Sua tarefa é escrever, em português brasileiro, um
relatório comparativo objetivo sobre um conjunto de execuções do mesmo
algoritmo para o mesmo conjunto de cidades.

REGRAS ABSOLUTAS (quebrar qualquer uma delas invalida o relatório):
1. Baseie TODAS as afirmações exclusivamente nos dados fornecidos. Nunca
   invente, estime, deduza ou arredonde um valor que não esteja presente
   nos dados.
2. Toda comparação numérica (ex.: "rota 23% mais curta", "economia de 40
   minutos") deve ser calculada a partir dos números exatos fornecidos.
   Sempre apresente o resultado já calculado e simplificado (ex.: "23%"),
   nunca como uma fração não resolvida (ex.: nunca escreva algo como
   "(75900/284692)%" — calcule o valor final antes de escrever).
3. Se o campo duration tiver 0 no segundo valor (minutos), escreva apenas
   a quantidade de horas (ex.: "3 horas"); nunca escreva "3 horas e 0
   minutos".
4. Se a lista de execuções tiver apenas 1 item, não produza comparação
   nenhuma: diga explicitamente que ainda não há execuções suficientes
   para uma análise comparativa e apenas descreva essa única execução.
5. Não opine sobre cidades, prioridades, restrições ou cenários que não
   estejam presentes nos dados recebidos.
6. Não repita o JSON bruto no relatório. Escreva em prosa e listas, não em
   formato de dados.

ESTRUTURA OBRIGATÓRIA DO RELATÓRIO (use estes títulos, nesta ordem):
1. Visão geral — quantas execuções existem, o período coberto (primeira e
   última data) e quais parâmetros (population_type, population_size,
   mutation_probability) foram usados em cada uma.
2. Eficiência das rotas — compare as distâncias (distance_km) entre as
   execuções: identifique a melhor e a pior, com a diferença percentual
   entre elas.
3. Economia de tempo — compare as durações totais (duration) entre as
   execuções, destacando a maior economia de tempo observada.
4. Economia de recursos computacionais — compare generations_run e
   population_size entre as execuções, apontando quais configurações
   atingiram bons resultados (menor distância) com menor custo
   computacional (menos gerações e/ou população menor).
5. Recomendação — com base exclusivamente nos dados, qual configuração
   teve o melhor equilíbrio entre qualidade da rota e custo
   computacional, e por quê.

FORMATO DOS DADOS DE ENTRADA:
Uma lista de execuções, cada uma com os campos: date (data/hora em UTC),
population_type (estratégia de geração da população inicial),
population_size, mutation_probability, generations_run (quantas gerações
o algoritmo rodou até convergir), distance_km (distância total da rota em
km), duration (par de números: horas e minutos estimados de viagem),
stops_count (número de cidades na rota). Os dados fornecidos pelo
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


def generate_comparative_report(runs: List[dict]) -> str:
    if not runs:
        raise ValueError(
            "Nenhuma execução foi fornecida para gerar o relatório comparativo."
        )

    data = prepare_comparative_report_data(runs)

    llm = LLMClient()

    prompt = (
        "Gere o relatório comparativo com base nestas execuções, da mais "
        "antiga para a mais recente:\n\n"
        f"{json.dumps(data, ensure_ascii=False, indent=2)}"
    )

    return llm.generate_response(instructions=REPORT_INSTRUCTIONS, prompt=prompt)
