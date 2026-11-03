import json
from typing import List

from backend.helpers import convert_seconds
from backend.models import IndividualWithFitness, Matrix

from backend.llm import LLMClient


VehicleRouteData = dict[str, list[dict[str, List[str] | float]] | tuple]


def prepare_route_data(
    calculated_routes: dict[str, Matrix], best_solution: IndividualWithFitness
):
    best_route = best_solution["individual"]
    distances = calculated_routes["cities_distances"]
    durations = calculated_routes["cities_durations"]

    llm_data: List[VehicleRouteData] = []

    for vehicle in best_route:
        current_vehicle = []
        total_duration_seconds = 0

        for index in range(len(vehicle) - 1):
            current_city = vehicle[index]
            next_city = vehicle[index + 1]
            current_city_id = current_city["id"]
            next_city_id = next_city["id"]

            pair = (current_city_id, next_city_id)
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
            current_vehicle.append(route_data)
            total_duration_seconds += duration_seconds

        llm_data.append(
            {
                "stretches": current_vehicle,
                "total_duration": convert_seconds(total_duration_seconds),
            }
        )

    return generate_driver_instructions(llm_data)


def generate_driver_instructions(data: List[VehicleRouteData]) -> str:
    llm = LLMClient()

    instructions = """
    Você é um assistente especializado em logística de entregas.

    Escreva instruções claras e práticas para motoristas,
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

    Se o primeiro número da tupla duration (as horas) for 0, escreva
    apenas os minutos. Por exemplo: "41 minutos", e nunca "0 horas e 
    41 minutos". Se o segundo número de duration (os minutos) for 0,
    escreva apenas a quantidade de horas (ex.: "2 horas"),
    sem mencionar "0 minutos" ou "e 0 minutos". Os números das horas
    e dos minutos devem ser sempre um número inteiro, nunca um número
    decimal.

    Você receberá uma lista com n itens, um para cada veículo
    (cada um com um motorista próprio e distinto); apenas um item
    significa que há somente um veículo. Cada item contém:
    stretches, a lista dos trechos do veículo, na ordem em que
    devem ser percorridos (cada trecho no formato descrito acima);
    e total_duration, a duração total da rota daquele veículo, já
    calculada pelo programa somando a duração de todos os seus
    trechos, também como um par de números (horas e minutos).
    Use total_duration exatamente como recebido, seguindo as mesmas
    regras de escrita de horas e minutos de duration. Nunca
    calcule, some ou estime você mesmo a duração total.

    Você deve escrever um texto em prosa, dando os direcionamentos 
    para cada motorista, mas não comece nunca seu texto indicando o 
    motorista, pois essa separação já será feita por nós. Indico
    usar linguagem markdown para indicar destaques em negrito no texto,
    como o nome das cidades e o tempo de duração da rota.
    Cada texto de instruções deve indicar de qual cidade para qual 
    cidade o motorista partirá, a distância aproximada entre as cidades
    e o tempo estimado de viagem em horas e minutos entre cada parte 
    da rota, organizando as instruções em uma mensagem fácil de ler 
    no celular.
    O texto de cada veículo deve começar obrigatoriamente com o
    número do veículo entre colchetes, seguindo a ordem dos itens
    (o primeiro texto começa com [1], o segundo com [2] e assim por
    diante), seguido do texto em si. Esse marcador é usado pelo
    programa para separar os textos; não use colchetes com números
    em nenhum outro lugar, nem escreva "Motorista" junto do número.
    Encerre cada texto indicando a cidade final da rota e a
    duração total da mesma, informada em total_duration.

    Atenção: as rotas são abertas e não deve haver volta à cidade de
    partida. A última cidade de cada rota é de fato o fim da rota.
    Não acrescente nenhuma volta para qualquer outra cidade.

    Pode ocorrer de os veículos partirem da mesma cidade ou de
    cidades diferentes, pois nem sempre há uma origem fixa. Cada
    veículo parte da primeira cidade dos seus stretches. Não presuma
    uma origem comum a todos os veículos, não mencione uma "cidade
    de origem" que não esteja nos dados e não invente deslocamentos
    até a cidade de partida de outro veículo.
    """

    prompt = (
        "Gere as instruções para os motoristas com base "
        "nos dados destas rotas:\n\n"
        f"{json.dumps(data, ensure_ascii=False, indent=2)}"
    )

    llm_instructions = llm.generate_response(
        instructions=instructions,
        prompt=prompt,
    )

    return llm_instructions
