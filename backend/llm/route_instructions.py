import json
from typing import List

from backend.config.helpers import convert_seconds
from backend.config.interfaces import Individual, Matrix

from backend.llm.llm_client import LLMClient


def prepare_route_data(
    calculated_routes: dict[str, Matrix], best_solution: dict[str, Individual | float]
):
    best_route = best_solution["individual"]
    distances = calculated_routes["cities_distances"]
    durations = calculated_routes["cities_durations"]

    llm_data: List[dict[str, List[str] | float]] = []

    for index in range(len(best_route) - 1):
        current_city = best_route[index]
        next_city = best_route[index + 1]
        current_city_location = current_city["id"]
        next_city_location = next_city["id"]

        pair = (current_city_location, next_city_location)
        distance = distances.get(pair)
        duration_seconds = durations.get(pair)

        if distance is None or duration_seconds is None:
            raise ValueError(
                f"Dados ausentes para o trecho "
                f"{current_city['name']} -> {next_city['name']}"
            )

        route_data = {
            "cities": [current_city["name"], next_city["name"]],
            "distance_km": distance,
            "duration": convert_seconds(duration_seconds),
        }

        llm_data.append(route_data)

    return generate_driver_instructions(llm_data)


def generate_driver_instructions(data: List[dict[str, List[str] | float]]) -> str:
    llm = LLMClient()

    instructions = """
    Você é um assistente especializado em logística de entregas.

    Escreva instruções claras e práticas para o motorista,
    em português brasileiro.

    Respeite rigorosamente a sequência de cidades fornecida.
    Não altere a rota, não invente horários ou prazos e não
    afirme que uma entrega está dentro do prazo sem receber
    essa informação nos dados.

    Os dados fornecidos pelo programa são a fonte oficial
    das distâncias e durações.

    Reproduza os valores recebidos sem recalcular,
    arredondar ou substituir números.

    Não acrescente trechos, cidades, paradas ou horários
    que não estejam presentes nos dados.

    Se algum dado estiver ausente ou inválido, informe
    que não foi possível gerar as instruções completas.

    Note que os dados que você receberá estão organizados
    da seguinte forma:

    cities é uma lista de 2 cidades - cidade de origem
    e cidade destino; distance_km: é a distância aproximada
    entre elas em km; duration contém um par de números:
    horas e minutos aproximados para chegar de uma cidade
    a outra.

    Se o segundo número de duration (os minutos) for 0,
    escreva apenas a quantidade de horas (ex.: "2 horas"),
    sem mencionar "0 minutos" ou "e 0 minutos".

    Você deve dar os direcionamentos ao motorista, indicando
    de qual cidade para qual cidade ele partirá,a distância
    aproximada entre as cidades e o tempo estimado de viagem
    em horas e minutos entre cada parte da rota, organizando
    as instruções em uma mensagem fácil de ler no celular.
    """

    prompt = (
        "Gere as instruções para o motorista com base "
        "nos dados desta rota:\n\n"
        f"{json.dumps(data, ensure_ascii=False, indent=2)}"
    )

    llm_instructions = llm.generate_response(
        instructions=instructions,
        prompt=prompt,
    )

    return llm_instructions
