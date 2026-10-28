const API_BASE = "http://localhost:5001";

export async function fetchCities() {
  const response = await fetch(`${API_BASE}/api/cities`);
  if (!response.ok) {
    throw new Error("Não foi possível carregar as cidades.");
  }
  return response.json();
}

export async function searchCities(query) {
  const response = await fetch(
    `${API_BASE}/api/cities/search?q=${encodeURIComponent(query)}`
  );
  if (!response.ok) {
    throw new Error("Não foi possível buscar cidades.");
  }
  return response.json();
}

export async function geocodeCities(cities) {
  const response = await fetch(`${API_BASE}/api/geocode-cities`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ cities }),
  });

  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(
      data.error || "Falha ao calcular as coordenadas das cidades."
    );
  }

  return response.json();
}

export async function optimizeRoute({
  populationType,
  populationSize,
  mutationProbability,
  originCity,
  destinationCities,
}) {
  const response = await fetch(`${API_BASE}/api/optimized-route`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      population_type: populationType,
      population_size: populationSize,
      mutation_probability: mutationProbability,
      origin_city: originCity,
      destination_cities: destinationCities,
    }),
  });

  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(data.error || "Falha ao gerar a rota.");
  }

  return response.json();
}

export async function fetchRouteRuns() {
  const response = await fetch(`${API_BASE}/api/route-runs`);
  if (!response.ok) {
    throw new Error("Não foi possível carregar o histórico de rotas.");
  }
  return response.json();
}

export async function fetchComparativeReport(citySet) {
  const response = await fetch(`${API_BASE}/api/route-runs/comparative-report`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ city_set: citySet }),
  });

  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(data.error || "Falha ao gerar o relatório comparativo.");
  }

  return response.json();
}

export async function fetchProcessRecommendations() {
  const response = await fetch(`${API_BASE}/api/process-recommendations`, {
    method: "POST",
  });

  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(data.error || "Falha ao gerar as recomendações.");
  }

  return response.json();
}

export async function fetchDriverInstructions(route) {
  const response = await fetch(`${API_BASE}/api/driver-instructions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ route }),
  });

  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(data.error || "Falha ao gerar os direcionamentos.");
  }

  return response.json();
}
