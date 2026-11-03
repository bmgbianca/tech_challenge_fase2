# Documentação da API

API HTTP (Flask) usada pelo frontend. Para a visão geral da arquitetura, veja [ARCHITECTURE.md](ARCHITECTURE.md).

- **URL base (desenvolvimento):** `http://localhost:5001` (`python -m backend.run`)
- **Formato:** JSON (`Content-Type: application/json`) em requisições com corpo e em todas as respostas.
- **Autenticação:** nenhuma. As chaves do OpenRouteService e da OpenAI ficam no servidor (`backend/.env`).
- **Erros:** respostas de erro têm o formato `{"error": "mensagem"}`.

| Método | Rota | Descrição |
|---|---|---|
| `GET` | [`/api/cities`](#get-apicities) | Dataset fixo de 16 cidades |
| `GET` | [`/api/cities/search`](#get-apicitiessearch) | Busca de municípios de SP |
| `POST` | [`/api/geocode-cities`](#post-apigeocode-cities) | Coordenadas de municípios |
| `POST` | [`/api/optimized-route`](#post-apioptimized-route) | Roda o algoritmo genético |
| `GET` | [`/api/route-runs`](#get-apiroute-runs) | Histórico de execuções |
| `POST` | [`/api/route-runs/comparative-report`](#post-apiroute-runscomparative-report) | Relatório comparativo (LLM) |
| `POST` | [`/api/process-recommendations`](#post-apiprocess-recommendations) | Recomendações de processo (LLM) |
| `POST` | [`/api/driver-instructions`](#post-apidriver-instructions) | Instruções para motoristas (LLM) |

## Objetos comuns

**Cidade** (`CityEntity`), usada nas requisições de rota:

```json
{
  "name": "Campinas",
  "id": 1,
  "coordinates": ["-47.06083", "-22.90556"],
  "priority": false
}
```

- `coordinates` é `[longitude, latitude]`, como strings.
- `id` identifica a cidade na matriz de distâncias. A cidade de **origem** tem sempre `id` igual a `0`; as de destino usam ids a partir de 1.
- `priority: true` marca uma entrega prioritária, que precisa chegar dentro do prazo de 17h.

**Rotas por veículo:** onde aparece `best_route` ou `route`, é uma lista de listas de **nomes** de cidades, uma lista por veículo, na ordem de visita. As rotas são abertas (o veículo não volta ao ponto de partida).

```json
[["São Paulo", "Campinas", "Ribeirão Preto"], ["São Paulo", "Santos"]]
```

**Duração:** em `total_duration` é um número em **segundos**, e corresponde ao veículo mais demorado.

---

## GET /api/cities

Devolve o dataset fixo de 16 cidades de São Paulo, usado para pré-preencher o formulário do frontend.

```bash
curl http://localhost:5001/api/cities
```

**200** — lista de cidades:

```json
[
  {
    "name": "São Paulo",
    "id": 0,
    "coordinates": ["-46.6388", "-23.5489"],
    "map_location": [1060, 480],
    "priority": false
  }
]
```

`map_location` é a posição no mapa da demo Pygame e pode ser ignorada.

---

## GET /api/cities/search

Busca municípios do estado de SP (645, lista do IBGE embutida no repositório) cujo nome contém o texto, **ignorando acentos e maiúsculas**.

| Parâmetro | Tipo | Descrição |
|---|---|---|
| `q` | query string | Texto buscado. Com menos de 2 caracteres, a resposta é uma lista vazia. |

```bash
curl "http://localhost:5001/api/cities/search?q=sao"
```

**200:**

```json
[
  { "id": 3550308, "name": "São Paulo" },
  { "id": 3549904, "name": "São José dos Campos" }
]
```

---

## POST /api/geocode-cities

Resolve nomes de municípios em coordenadas aproximadas (geocodificação da OpenRouteService, restrita ao estado de SP), com cache local.

**Corpo:**

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `cities` | lista de strings | sim | Nomes dos municípios |

```bash
curl -X POST http://localhost:5001/api/geocode-cities \
  -H "Content-Type: application/json" \
  -d '{"cities": ["Campinas", "Santos"]}'
```

**200:**

```json
{
  "coordinates": {
    "Campinas": [-47.0609, -22.9056],
    "Santos": [-46.3336, -23.9608]
  }
}
```

Cada valor é `[longitude, latitude]`.

**Erros:**

| Código | Quando |
|---|---|
| 400 | `cities` ausente ou vazio, ou município inexistente |
| 500 | Falha inesperada (por exemplo, OpenRouteService fora do ar) |

---

## POST /api/optimized-route

Roda o algoritmo genético para um problema de roteamento de veículos de rota aberta e devolve a melhor solução e o histórico das gerações. Salva a execução no histórico.

**Corpo** (todos os campos são obrigatórios, mas `origin_city` pode ser `null`):

| Campo | Tipo | Descrição |
|---|---|---|
| `origin_city` | Cidade ou `null` | Origem fixa (`id` igual a 0). Com `null`, não há origem fixa e cada veículo começa na primeira cidade da sua rota. |
| `destination_cities` | lista de Cidade | Cidades a visitar (sem a origem) |
| `population_type` | string | `random`, `nearest_neighbor` ou `cheapest_insertion` |
| `population_size` | inteiro | Tamanho da população (mínimo 50) |
| `mutation_probability` | número | Probabilidade de mutação, de 0 a 1 |
| `vehicles_number` | inteiro | Número de veículos. Não pode ser maior que o número de cidades a visitar. |

```bash
curl -X POST http://localhost:5001/api/optimized-route \
  -H "Content-Type: application/json" \
  -d '{
    "origin_city": {"name": "São Paulo", "id": 0, "coordinates": ["-46.6388", "-23.5489"], "priority": false},
    "destination_cities": [
      {"name": "Campinas", "id": 1, "coordinates": ["-47.06083", "-22.90556"], "priority": true},
      {"name": "Santos", "id": 2, "coordinates": ["-46.3336", "-23.9608"], "priority": false},
      {"name": "Sorocaba", "id": 3, "coordinates": ["-47.4526", "-23.5015"], "priority": false}
    ],
    "population_type": "nearest_neighbor",
    "population_size": 100,
    "mutation_probability": 0.5,
    "vehicles_number": 2
  }'
```

**200:**

```json
{
  "cities": [ "...as cidades usadas na execução (destinos e origem)..." ],
  "vehicles_number": 2,
  "best_route": [["São Paulo", "Campinas"], ["São Paulo", "Santos", "Sorocaba"]],
  "best_distance": 412.7,
  "total_duration": 18240.0,
  "priorities_on_time": true,
  "stops_count": 4,
  "vehicles_summary": [
    {
      "vehicle": 1,
      "route": ["São Paulo", "Campinas"],
      "distance_km": 99.5,
      "duration_seconds": 6000.0,
      "stops_count": 1,
      "priority_cities_count": 1,
      "priorities_on_time": true
    }
  ],
  "fitness_history": [530.2, 498.1, 412.7],
  "snapshots": [
    {
      "generation": 0,
      "best_distance": 530.2,
      "best_duration": 21000.0,
      "priorities_on_time": true,
      "route": [["São Paulo", "Campinas"], ["São Paulo", "Santos", "Sorocaba"]],
      "second_best_distance": 541.0,
      "second_best_route": [["São Paulo", "Santos"], ["São Paulo", "Campinas", "Sorocaba"]]
    }
  ]
}
```

| Campo | Descrição |
|---|---|
| `cities` | Cidades da execução, com coordenadas (o frontend as usa no mapa e nas instruções ao motorista) |
| `best_route` | Melhor solução: uma rota (nomes) por veículo |
| `best_distance` | Soma das distâncias de todos os veículos, em km |
| `total_duration` | Duração da solução, em segundos (a do veículo mais demorado) |
| `priorities_on_time` | `true` se todas as cidades prioritárias chegam dentro de 17h |
| `stops_count` | Cidades distintas atendidas (a origem conta uma vez) |
| `vehicles_summary` | Resumo por veículo (mesma ordem de `best_route`): `distance_km`, `duration_seconds`, `stops_count` (sem contar a origem), `priority_cities_count` e `priorities_on_time` (prioridades do veículo dentro de 17h) |
| `fitness_history` | Melhor distância de cada geração |
| `snapshots` | Estado de gerações selecionadas, para o replay no mapa: melhor e segunda melhor rota e distância |

**Erros:**

| Código | Quando |
|---|---|
| 400 | Campo obrigatório ausente (a mensagem lista todos), `population_type` inválido, `population_size` menor que 50, `mutation_probability` fora do intervalo de 0 a 1 ou mais veículos do que cidades a visitar |

---

## GET /api/route-runs

Devolve o histórico completo das execuções do algoritmo (arquivo `backend/data/route_runs.json`).

```bash
curl http://localhost:5001/api/route-runs
```

**200:** lista de execuções, da mais antiga para a mais recente.

```json
[
  {
    "id": "8f1c0f2e-6e0a-4d6e-9a53-2d6a3b1d9c11",
    "created_at": "2026-11-03T14:22:10.123456+00:00",
    "population_type": "nearest_neighbor",
    "population_size": 100,
    "mutation_probability": 0.5,
    "best_distance": 412.7,
    "total_duration": 18240.0,
    "priorities_on_time": true,
    "stops_count": 4,
    "vehicles_number": 2,
    "best_route": [["São Paulo", "Campinas"], ["São Paulo", "Santos", "Sorocaba"]],
    "city_set": ["Campinas", "Santos", "Sorocaba", "São Paulo"],
    "generations_run": 640
  }
]
```

`city_set` é a lista ordenada de cidades distintas da execução. Execuções antigas podem não ter `vehicles_number` (equivale a 1 veículo).

---

## POST /api/route-runs/comparative-report

Gera, com a LLM, um relatório comparativo das execuções de **um mesmo conjunto de cidades e número de veículos**, num período. O backend calcula as métricas (melhor, pior e média de distância e duração, e a economia); a LLM só as interpreta. O resultado é guardado em cache.

**Corpo:**

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `city_set` | lista de strings | sim | Nomes das cidades do conjunto (a ordem não importa) |
| `vehicles_number` | inteiro | não | Só compara execuções com esse número de veículos. Sem o campo, não filtra por veículos. |
| `period` | string | não | `day` (últimas 24h), `week` (últimos 7 dias) ou `all` (padrão) |

```bash
curl -X POST http://localhost:5001/api/route-runs/comparative-report \
  -H "Content-Type: application/json" \
  -d '{"city_set": ["Campinas", "Santos", "Sorocaba", "São Paulo"], "vehicles_number": 2, "period": "week"}'
```

**200:**

```json
{ "report": "## Visão geral\n...", "cached": false }
```

`report` é texto em markdown. `cached` indica se o texto veio do cache (o conjunto de execuções e o período eram os mesmos de um relatório anterior, e a LLM não foi chamada).

**Erros:**

| Código | Quando |
|---|---|
| 400 | `city_set` ausente ou `period` inválido |
| 404 | Nenhuma execução corresponde ao conjunto de cidades, número de veículos e período |
| 500 | Falha ao gerar o relatório (por exemplo, erro da LLM) |

---

## POST /api/process-recommendations

Gera, com a LLM, recomendações de melhoria de processo (parâmetros do algoritmo) a partir de **todo** o histórico. Não recebe corpo. O resultado é cacheado enquanto o histórico não mudar.

```bash
curl -X POST http://localhost:5001/api/process-recommendations
```

**200:**

```json
{ "report": "## Visão geral\n...", "cached": true }
```

**Erros:**

| Código | Quando |
|---|---|
| 404 | O histórico está vazio |
| 500 | Falha ao gerar as recomendações |

Com menos de 5 execuções, a LLM é instruída a avisar que ainda há poucos dados para identificar padrões.

---

## POST /api/driver-instructions

Gera, com a LLM, instruções em linguagem natural para os motoristas de uma rota. As distâncias e durações dos trechos são calculadas pelo backend (OpenRouteService) e a duração total de cada veículo também; a LLM só redige.

**Corpo:**

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `route` | lista de listas de strings | sim | Rota por veículo (nomes). Uma lista simples de nomes é aceita e tratada como um único veículo. |
| `cities` | lista de Cidade | sim | Cidades com coordenadas. Toda cidade de `route` precisa estar aqui. |

```bash
curl -X POST http://localhost:5001/api/driver-instructions \
  -H "Content-Type: application/json" \
  -d '{
    "route": [["São Paulo", "Campinas"], ["São Paulo", "Santos"]],
    "cities": [
      {"name": "São Paulo", "id": 0, "coordinates": ["-46.6388", "-23.5489"], "priority": false},
      {"name": "Campinas", "id": 1, "coordinates": ["-47.06083", "-22.90556"], "priority": true},
      {"name": "Santos", "id": 2, "coordinates": ["-46.3336", "-23.9608"], "priority": false}
    ]
  }'
```

**200:**

```json
{ "driver_instructions": "[1] Saia de **São Paulo** ...\n\n[2] Saia de **São Paulo** ..." }
```

Com mais de um veículo, o texto de cada motorista começa com o marcador `[N]` (`[1]`, `[2]`, ...), que o frontend usa para separar as abas "Motorista N" e remove da exibição.

**Erros:**

| Código | Quando |
|---|---|
| 400 | `route` ou `cities` ausente, ou cidade da rota que não está em `cities` |
| 500 | Falha ao calcular os trechos (OpenRouteService) ou ao gerar o texto (LLM) |
