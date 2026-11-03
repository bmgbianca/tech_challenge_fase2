# Otimização de Rotas para Distribuição de Medicamentos

Projeto de pós-graduação (Tech Challenge) que resolve um **problema de roteirização de veículos de rota aberta (open VRP)** — evolução do "caixeiro viajante médico" (TSP) — usando um **Algoritmo Genético**, com apoio de **LLM** para geração de instruções e relatórios. O objetivo é dividir um conjunto de cidades do estado de São Paulo entre **vários veículos** e encontrar as rotas mais curtas para entregar medicamentos e insumos, respeitando prazos de entrega para cidades com prioridade (ex: medicamentos críticos). As rotas são **abertas** (os veículos não voltam ao ponto de partida) e a **cidade de origem é opcional**: se informada, todos os veículos partem dela; se não, cada veículo começa na primeira cidade da sua rota.

O sistema tem duas formas de uso:

- **Aplicação web** (recomendada): frontend em React + backend em Flask, com seleção de cidades, visualização em mapa real, replay da evolução das gerações, geração de instruções/relatórios via LLM e histórico de execuções.
- **Demonstração standalone**: `backend/main.py`, uma janela Pygame que roda o algoritmo isoladamente, sem precisar do frontend nem do servidor web — útil para visualizar o algoritmo "puro" rodando em tempo real.

Para a arquitetura detalhada (diagramas, fluxo de dados), veja **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)**; para a documentação completa dos endpoints (requisições, respostas, erros e exemplos `curl`), veja **[docs/API.md](docs/API.md)**.

## Como o algoritmo genético funciona

O algoritmo evolui uma população de rotas candidatas ao longo de várias gerações:

Cada indivíduo é uma lista de rotas, uma por veículo (`List[List[CityEntity]]`). Quando há origem fixa (cidade com `id == 0`), ela é a primeira cidade de todas as rotas; as demais cidades aparecem em exatamente um veículo.

1. **População inicial** — gerada por uma entre três estratégias: aleatória, vizinho mais próximo (nearest neighbor) ou inserção mais barata (cheapest insertion). As cidades restantes vão para o veículo cuja última cidade está mais próxima (NN) ou de menor custo de inserção (CI). Pedir mais veículos do que cidades a visitar gera `ValueError`.
2. **Fitness** — soma das distâncias de todos os veículos. Uma solução só é válida se **todas** as cidades prioritárias de **todos** os veículos forem atendidas dentro do limite de 17h (`TIME_LIMIT` em `backend/constants/ga.py`). A duração da solução é a do veículo mais demorado.
3. **Seleção** — torneio de tamanho 2. Entre soluções válidas vence a de menor distância; entre inválidas vence a com menos prioridades fora do prazo, depois a de menor atraso total e, por fim, a de menor distância.
4. **Crossover** — order crossover (OX) aplicado à rota "achatada" (origem uma única vez); os filhos são divididos de volta nos veículos mantendo o tamanho da rota de cada veículo nos pais.
5. **Mutação** — sorteia **um** veículo e embaralha um segmento contíguo de 2 a 5 cidades dele, preservando a origem fixa (quando existe).
6. **Elitismo** — as 4 melhores soluções de cada geração são mantidas sem alteração.
7. **Parada** — ao atingir 3000 gerações ou quando a melhor solução fica estável por 500 gerações seguidas.

## Estrutura do projeto

```
backend/    Algoritmo genético, API Flask, integração com LLM e serviços externos
frontend/   Interface web em React (Vite)
docs/       Documentação de arquitetura e diagramas
```

Veja a tabela completa de pacotes/responsabilidades em [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md#estrutura-de-pastas).

## Setup

Requer **Python 3.11+**, **Node.js 18+** e duas chaves de API gratuitas:
- [OpenRouteService](https://openrouteservice.org/) (distâncias/durações entre cidades)
- [OpenAI](https://platform.openai.com/) (geração de instruções e relatórios via LLM)

### Backend

A partir da raiz do projeto:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
cp backend/.env.example backend/.env
# edite backend/.env e preencha OPENROUTESERVICE_API_KEY, OPENAI_API_KEY e OPENAI_MODEL
```

### Frontend

```bash
cd frontend
npm install
```

## Uso

### Aplicação web

Em dois terminais separados, a partir da raiz do projeto:

```bash
# Terminal 1 — backend (porta 5001)
source .venv/bin/activate
python -m backend.run

# Terminal 2 — frontend (porta 5173)
cd frontend
npm run dev
```

Acesse `http://localhost:5173`. A aba **Início** permite escolher a cidade de origem (opcional — limpe o campo para ficar "Sem origem fixa"), as cidades de destino/prioridade, o número de veículos e gerar as rotas otimizadas, com replay animado da evolução das gerações no mapa (uma cor por veículo). A busca de cidades ignora acentos e maiúsculas, e a cidade de origem não pode ser escolhida também como destino. O botão de instruções ao motorista gera um texto por veículo, exibido em abas "Motorista 1", "Motorista 2"… quando há mais de um veículo. As abas **Relatórios** e **Recomendações** mostram análises geradas por LLM sobre o histórico de execuções.

### Demonstração standalone (Pygame)

```bash
source .venv/bin/activate
python backend/main.py
```

Abre uma janela mostrando o mapa de São Paulo, as cidades (vermelho), a melhor solução (uma cor por veículo, rotas abertas) e a segunda melhor, além do gráfico de evolução do fitness, em tempo real. Pressione `Q` ou feche a janela para interromper antes da convergência. Usa sempre o conjunto fixo de 16 cidades, 3 veículos e parâmetros fixos definidos em `backend/constants/` — não depende do frontend nem do servidor Flask.

## Testes

A suíte de testes (pytest) cobre o algoritmo genético para múltiplos veículos (fitness, prazos, seleção, crossover, mutação e estratégias de população inicial), helpers, serviços e rotas da API Flask (histórico, otimização, instruções ao motorista, busca de cidades), a montagem dos dados/prompts da LLM e o cliente de API — com chamadas externas mockadas. O frontend não possui testes automatizados. Para rodar, a partir da raiz do projeto:

```bash
source .venv/bin/activate
pytest backend -v   # precisa de OPENROUTESERVICE_API_KEY definida (pode ser um valor qualquer)
```

## Licença

Este projeto está licenciado sob a [Licença MIT](LICENSE).
