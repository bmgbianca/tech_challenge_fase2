// One color per vehicle, reused cyclically when there are more vehicles than colors.
export const VEHICLE_COLORS = [
  "#2457ff",
  "#e67e22",
  "#1b9e77",
  "#9b59b6",
  "#c0392b",
  "#16a5b8",
  "#8e6c1a",
  "#d63384",
];

export function getVehicleColor(index) {
  return VEHICLE_COLORS[index % VEHICLE_COLORS.length];
}

// The backend sends one list of city names per vehicle ([["A", "B"], ["A", "C"]]).
// A flat list of names (older runs, single route) is treated as a single vehicle.
export function normalizeRoutes(route) {
  if (!route || route.length === 0) return [];
  return Array.isArray(route[0]) ? route : [route];
}

// Distinct cities of a run: the origin appears in every vehicle route.
export function getCitySet(run) {
  if (run.city_set) return run.city_set;
  return [...new Set(normalizeRoutes(run.best_route).flat())].sort();
}
