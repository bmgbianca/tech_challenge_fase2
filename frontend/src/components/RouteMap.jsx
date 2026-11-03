import { MapContainer, TileLayer, CircleMarker, Popup, Polyline } from "react-leaflet";
import { getVehicleColor, normalizeRoutes } from "../routes";

const SP_CENTER = [-22.4, -48.8];

function toLatLng(city) {
  const [lon, lat] = city.coordinates;
  return [Number(lat), Number(lon)];
}

// One list of positions per vehicle. Routes are open: the vehicle does not
// return to the origin, so the line is not closed.
function toVehiclesPositions(route, cities) {
  if (!cities.length) return [];

  return normalizeRoutes(route).map((vehicleNames) =>
    vehicleNames
      .map((name) => cities.find((city) => city.name === name))
      .filter(Boolean)
      .map(toLatLng)
  );
}

const ORIGIN_ID = 0;

export default function RouteMap({ cities, bestRoute, secondBestRoute, children }) {
  const vehiclesPositions = toVehiclesPositions(bestRoute, cities);
  const secondBestVehiclesPositions = toVehiclesPositions(secondBestRoute, cities);

  return (
    <div className="map-card">
      <div className="map-card__header">
        <span className="map-card__icon">💡</span>
        <div>
          <strong>Estado de São Paulo</strong>
          <div>Sua rota, do seu jeito.</div>
        </div>
      </div>

      <MapContainer center={SP_CENTER} zoom={7} className="map-container">
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        {cities.map((city) => {
          const isOrigin = city.id === ORIGIN_ID;
          const color = isOrigin ? "#1b8a3b" : city.priority ? "#e32336" : "#002fa7";

          return (
            <CircleMarker
              key={city.name}
              center={toLatLng(city)}
              radius={isOrigin ? 10 : city.priority ? 8 : 6}
              pathOptions={{ color, fillColor: color, fillOpacity: 0.9 }}
            >
              <Popup>
                <strong>{city.name}</strong>
                {isOrigin ? " — origem (saída de todos os veículos)" : ""}
                {city.priority ? " — entrega prioritária" : ""}
              </Popup>
            </CircleMarker>
          );
        })}

        {secondBestVehiclesPositions.map(
          (positions, index) =>
            positions.length > 1 && (
              <Polyline
                key={`second-best-${index}`}
                positions={positions}
                pathOptions={{ color: "#8a93a6", weight: 2, dashArray: "6 6" }}
              />
            )
        )}

        {vehiclesPositions.map(
          (positions, index) =>
            positions.length > 1 && (
              <Polyline
                key={`best-${index}`}
                positions={positions}
                pathOptions={{ color: getVehicleColor(index), weight: 4 }}
              />
            )
        )}
      </MapContainer>

      {vehiclesPositions.length > 0 && (
        <ul className="route-legend" aria-label="Legenda dos veículos">
          {vehiclesPositions.map((_, index) => (
            <li key={index} className="route-legend__item">
              <span
                className="route-legend__color"
                style={{ backgroundColor: getVehicleColor(index) }}
              />
              Veículo {index + 1}
            </li>
          ))}
        </ul>
      )}

      {children}
    </div>
  );
}
