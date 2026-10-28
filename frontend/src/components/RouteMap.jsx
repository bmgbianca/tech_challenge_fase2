import { MapContainer, TileLayer, CircleMarker, Popup, Polyline } from "react-leaflet";

const SP_CENTER = [-22.4, -48.8];

function toLatLng(city) {
  const [lon, lat] = city.coordinates;
  return [Number(lat), Number(lon)];
}

function toRoutePositions(routeNames, cities) {
  if (!routeNames || !cities.length) return [];

  const routeCities = routeNames
    .map((name) => cities.find((city) => city.name === name))
    .filter(Boolean);

  const positions = routeCities.map(toLatLng);
  if (positions.length > 1) {
    positions.push(positions[0]);
  }
  return positions;
}

export default function RouteMap({ cities, bestRoute, secondBestRoute, children }) {
  const routePositions = toRoutePositions(bestRoute, cities);
  const secondBestPositions = toRoutePositions(secondBestRoute, cities);

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

        {cities.map((city) => (
          <CircleMarker
            key={city.name}
            center={toLatLng(city)}
            radius={city.priority ? 8 : 6}
            pathOptions={{
              color: city.priority ? "#e32336" : "#002fa7",
              fillColor: city.priority ? "#e32336" : "#002fa7",
              fillOpacity: 0.9,
            }}
          >
            <Popup>
              <strong>{city.name}</strong>
              {city.priority ? " — entrega prioritária" : ""}
            </Popup>
          </CircleMarker>
        ))}

        {secondBestPositions.length > 1 && (
          <Polyline
            positions={secondBestPositions}
            pathOptions={{ color: "#8a93a6", weight: 2, dashArray: "6 6" }}
          />
        )}

        {routePositions.length > 1 && (
          <Polyline positions={routePositions} pathOptions={{ color: "#2457ff", weight: 4 }} />
        )}
      </MapContainer>

      {children}
    </div>
  );
}
