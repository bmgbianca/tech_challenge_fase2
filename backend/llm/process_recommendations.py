import json
from typing import List

from ..config import convert_seconds
from .llm_client import LLMClient

RECOMMENDATIONS_INSTRUCTIONS = """
Você é um analista de processos especializado em algoritmos genéticos
aplicados à otimização de rotas de entrega. Sua tarefa é escrever, em
português brasileiro, um relatório de recomendações de melhoria de
processo, com base em padrões observados em várias execuções do
algoritmo, possivelmente para conjuntos de cidades diferentes.

REGRAS ABSOLUTAS (quebrar qualquer uma delas invalida o relatório):
1. Baseie TODAS as afirmações exclusivamente nos dados fornecidos. Nunca
   invente, estime, deduza ou arredonde um valor que não esteja presente
   nos dados.
2. Um "padrão" só pode ser afirmado se houver pelo menos 2 execuções que o
   sustentem. Nunca generalize a partir de uma única execução.
3. Toda comparação numérica deve ser calculada a partir dos números
   exatos fornecidos, e apresentada já calculada (ex.: "23%"), nunca como
   fração não resolvida.
4. Se o campo duration tiver 0 no segundo valor (minutos), escreva apenas
   a quantidade de horas (ex.: "3 horas"); nunca escreva "3 horas e 0
   minutos".
5. Se houver menos de 5 execuções no total, não produza "padrões": diga
   explicitamente que ainda há poucos dados para identificar padrões
   confiáveis, descreva brevemente o que existe até agora, e pare por aí
   — não force recomendações especulativas.
6. Trate execuções de conjuntos de cidades diferentes (city_set_size
   diferente) como contextos distintos: nunca compare a distância ou
   duração absoluta entre execuções de tamanhos de conjunto diferentes,
   apenas os parâmetros do algoritmo (population_type, population_size,
   mutation_probability) e métricas relativas (gerações até convergir).
7. Não repita o JSON bruto no relatório. Escreva em prosa e listas.
8. Não opine sobre cidades específicas, prioridades de entrega ou
   restrições de negócio — o foco é exclusivamente o processo do
   algoritmo genético (parâmetros e configuração).

ESTRUTURA OBRIGATÓRIA DO RELATÓRIO (use estes títulos, nesta ordem):
1. Visão geral — quantas execuções existem no total, quantos conjuntos de
   cidades distintos (city_set_size) estão representados, e o período
   coberto (primeira e última data).
2. Padrões identificados — quais combinações de population_type,
   population_size e mutation_probability aparecem repetidamente
   associadas a menor distância, menor duração ou convergência em menos
   gerações. Cite quantas execuções sustentam cada padrão apontado.
3. Sugestões de melhoria de processo — recomendações concretas e
   acionáveis sobre quais parâmetros tendem a produzir melhores
   resultados com menor custo computacional (menos gerações), baseadas
   estritamente nos padrões da seção anterior.
4. Limitações dos dados atuais — o que ainda falta (quantidade de
   execuções, diversidade de parâmetros testados, etc.) para que as
   recomendações fiquem mais confiáveis.

FORMATO DOS DADOS DE ENTRADA:
Uma lista de execuções, cada uma com os campos: date (data/hora em UTC),
city_set_size (quantidade de cidades na rota daquela execução),
population_type, population_size, mutation_probability, generations_run
(quantas gerações o algoritmo rodou até convergir), distance_km (distância
total da rota em km), duration (par de números: horas e minutos estimados
de viagem). Os dados fornecidos pelo programa são a fonte oficial e
definitiva dos números.

O relatório deve ser conciso e fácil de ler em poucos minutos, adequado
para ser exibido em uma tela de dashboard.
"""


def prepare_process_recommendations_data(runs: List[dict]) -> List[dict]:
    """Strips every stored route run down to only the fields relevant for
    cross-run pattern analysis, dropping city names/order entirely — this
    report is about the algorithm's process, not any specific route."""

    report_data = []

    for run in sorted(runs, key=lambda item: item["created_at"]):
        hours, minutes = convert_seconds(run["total_duration"])
        report_data.append(
            {
                "date": run["created_at"],
                "city_set_size": len(run.get("city_set", run["best_route"])),
                "population_type": run["population_type"],
                "population_size": run["population_size"],
                "mutation_probability": run["mutation_probability"],
                "generations_run": run["generations_run"],
                "distance_km": round(run["best_distance"], 1),
                "duration": (hours, minutes),
            }
        )

    return report_data


def generate_process_recommendations(runs: List[dict]) -> str:
    if not runs:
        raise ValueError(
            "Nenhuma execução foi encontrada para gerar recomendações de processo."
        )

    data = prepare_process_recommendations_data(runs)

    llm = LLMClient()

    prompt = (
        "Gere o relatório de recomendações de processo com base nestas "
        "execuções, da mais antiga para a mais recente:\n\n"
        f"{json.dumps(data, ensure_ascii=False, indent=2)}"
    )

    return llm.generate_response(
        instructions=RECOMMENDATIONS_INSTRUCTIONS, prompt=prompt
    )
