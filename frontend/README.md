# Frontend

Interface web (React + Vite) do projeto de otimização de rotas. Veja o [README principal](../README.md) para visão geral do projeto e instruções de setup, e [docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md) para a arquitetura detalhada.

## Rodando localmente

```bash
npm install
npm run dev
```

Requer o backend rodando em `http://localhost:5001` (veja o README principal).

## Estrutura

- `src/pages/` — Início (planejamento e mapa), Relatórios (agrupados por cidades + veículos, com filtro de período), Recomendações.
- `src/components/` — formulário (origem opcional, destinos, nº de veículos), mapa com uma cor por veículo, resumo (totais e cartão por veículo com distância, duração, paradas, rota e status das prioridades), log e modal de instruções com abas "Motorista N".
- `src/api.js` — chamadas HTTP; `src/routes.js`, `src/routeParams.js`, `src/instructions.js` — funções auxiliares puras (rotas por veículo, regra origem × destinos, separação das instruções pelos marcadores `[1]`, `[2]`…).

Não há testes automatizados no frontend; `npm run lint` roda o ESLint.
