# Otimização de Rotas para Distribuição de Medicamentos

Projeto de pós-graduação (Tech Challenge) que resolve uma variação do problema do caixeiro viajante (TSP) — o "caixeiro viajante médico" — usando um **Algoritmo Genético**, com apoio de **LLM** para geração de instruções e relatórios. O objetivo é encontrar a rota mais curta para um veículo entregar medicamentos e insumos a um conjunto de cidades do estado de São Paulo, respeitando prazos de entrega para cidades com prioridade (ex: medicamentos críticos).

O sistema tem duas formas de uso:

- **Aplicação web** (recomendada): frontend em React + backend em Flask, com seleção de cidades, visualização em mapa real, replay da evolução das gerações, geração de instruções/relatórios via LLM e histórico de execuções.
- **Demonstração standalone**: `backend/main.py`, uma janela Pygame que roda o algoritmo isoladamente, sem precisar do frontend nem do servidor web — útil para visualizar o algoritmo "puro" rodando em tempo real.

Para a arquitetura detalhada (diagramas, fluxo de dados, referência de API), veja **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)**.

## Como o algoritmo genético funciona

O algoritmo evolui uma população de rotas candidatas ao longo de várias gerações:

1. **População inicial** — gerada por uma entre três estratégias: aleatória, vizinho mais próximo (nearest neighbor) ou inserção mais barata (cheapest insertion), sempre partindo de uma cidade de origem fixa.
2. **Fitness** — a distância total da rota. Rotas que não entregam a tempo nas cidades prioritárias (dentro do limite de 17h definido em `config/constants.py`) são tratadas como inválidas e penalizadas na seleção.
3. **Seleção** — torneio de tamanho 2, priorizando rotas válidas com menor distância; entre rotas inválidas, vence a que atende mais entregas prioritárias no prazo.
4. **Crossover** — order crossover (OX), que preserva um segmento de um dos pais e completa o restante com a ordem de visitação do outro pai.
5. **Mutação** — embaralha um segmento contíguo de 2 a 5 cidades da rota, preservando a cidade de origem.
6. **Elitismo** — as 4 melhores rotas de cada geração são mantidas sem alteração.
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

Acesse `http://localhost:5173`. A aba **Início** permite escolher cidades de origem/destino/prioridade e gerar a rota otimizada, com replay animado da evolução das gerações no mapa. As abas **Relatórios** e **Recomendações** mostram análises geradas por LLM sobre o histórico de execuções.

### Demonstração standalone (Pygame)

```bash
source .venv/bin/activate
python backend/main.py
```

Abre uma janela mostrando o mapa de São Paulo, as cidades (vermelho), a melhor rota (azul) e a segunda melhor (preto), além do gráfico de evolução do fitness, em tempo real. Pressione `Q` ou feche a janela para interromper antes da convergência. Usa sempre o conjunto fixo de 16 cidades e parâmetros fixos definidos em `config/constants.py` — não depende do frontend nem do servidor Flask.

## Testes

A suíte de testes (pytest) cobre a lógica pura do algoritmo genético — fitness, cálculo de prazos, validação de solução, crossover, mutação e as estratégias de população inicial — além do cliente de API (com chamadas de rede mockadas). Para rodar, a partir da raiz do projeto:

```bash
source .venv/bin/activate
pytest backend -v
```

## Licença

Este projeto está licenciado sob a [Licença MIT](LICENSE).
