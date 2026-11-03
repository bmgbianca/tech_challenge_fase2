import { useEffect, useRef, useState } from "react";
import RouteForm from "../components/RouteForm";
import RouteMap from "../components/RouteMap";
import RightPanel from "../components/RightPanel";
import LoadingOverlay from "../components/LoadingOverlay";
import RouteReplayControls from "../components/RouteReplayControls";
import { fetchCities, geocodeCities, optimizeRoute } from "../api";

const REPLAY_INTERVAL_MS = 400;
const DEFAULT_LOADING_MESSAGE =
  "Estamos trabalhando para encontrar a melhor rota.";
const GEOCODING_MESSAGE =
  "Calculando as coordenadas das cidades selecionadas...";
const OPTIMIZING_MESSAGE =
  "Calculando as melhores rotas para a sua necessidade...";

function toOption(city) {
  return { value: city.name, label: city.name };
}

// The numeric inputs keep what the user typed as text (so that clearing the
// field leaves it empty instead of forcing a 0 that would turn "2" into "02").
// An empty field becomes NaN, which fails every validation below.
function toNumber(value) {
  return value === "" || value === null || value === undefined
    ? NaN
    : Number(value);
}

function validateParams(params) {
  const errors = {};
  const vehiclesNumber = toNumber(params.vehiclesNumber);
  const populationSize = toNumber(params.populationSize);
  const mutationProbability = toNumber(params.mutationProbability);

  if (!params.destinationCities || params.destinationCities.length === 0) {
    errors.destinationCities = "Selecione ao menos uma cidade de destino.";
  }
  if (!Number.isInteger(vehiclesNumber) || vehiclesNumber < 1) {
    errors.vehiclesNumber = "Informe um número inteiro de veículos (mínimo 1).";
  } else if (
    params.destinationCities &&
    vehiclesNumber > params.destinationCities.length
  ) {
    errors.vehiclesNumber = `O número de veículos não pode ser maior que o de cidades de destino (${params.destinationCities.length}).`;
  }
  if (!params.populationType) {
    errors.populationType = "Selecione uma estratégia de população.";
  }
  if (!Number.isInteger(populationSize) || populationSize < 4) {
    errors.populationSize = "Informe um tamanho de população de pelo menos 4.";
  }
  if (
    Number.isNaN(mutationProbability) ||
    mutationProbability < 0 ||
    mutationProbability > 1
  ) {
    errors.mutationProbability = "Informe um valor entre 0.0 e 1.0.";
  }

  return errors;
}

export default function HomePage() {
  const [cities, setCities] = useState([]);
  const [params, setParams] = useState({
    originCity: null,
    destinationCities: [],
    priorityCities: [],
    vehiclesNumber: 3,
    populationType: "random",
    populationSize: 500,
    mutationProbability: 0.5,
  });
  const [fieldErrors, setFieldErrors] = useState({});
  const [loading, setLoading] = useState(false);
  const [loadingMessage, setLoadingMessage] = useState(DEFAULT_LOADING_MESSAGE);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const [snapshotIndex, setSnapshotIndex] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [playbackSpeed, setPlaybackSpeed] = useState(1);
  const intervalRef = useRef(null);

  useEffect(() => {
    fetchCities()
      .then((fetchedCities) => {
        setCities(fetchedCities);

        // Pre-fill the form with the default fixed dataset: São Paulo as
        // origin, every other city as destination, and the ones flagged
        // priority:true already selected as priority deliveries.
        const origin = fetchedCities.find((city) => city.name === "São Paulo");
        const destinations = fetchedCities.filter(
          (city) => city.name !== "São Paulo"
        );
        const priorities = destinations.filter((city) => city.priority);

        setParams((current) => ({
          ...current,
          originCity: origin ? toOption(origin) : current.originCity,
          destinationCities: destinations.map(toOption),
          priorityCities: priorities.map(toOption),
        }));
      })
      .catch((err) => setError(err.message));
  }, []);

  useEffect(() => {
    if (!isPlaying || !result?.snapshots) return undefined;

    intervalRef.current = setInterval(() => {
      setSnapshotIndex((current) => {
        const lastIndex = result.snapshots.length - 1;
        if (current >= lastIndex) {
          setIsPlaying(false);
          return lastIndex;
        }
        return current + 1;
      });
    }, REPLAY_INTERVAL_MS / playbackSpeed);

    return () => clearInterval(intervalRef.current);
  }, [isPlaying, result, playbackSpeed]);

  async function handleGenerateRoute() {
    const errors = validateParams(params);
    setFieldErrors(errors);
    if (Object.keys(errors).length > 0) {
      return;
    }

    setLoading(true);
    setError(null);
    setIsPlaying(false);

    const originCityName = params.originCity?.value ?? null;
    const destinationCityNames = params.destinationCities.map(
      (city) => city.value
    );
    const selectedCityNames = [
      ...new Set([originCityName, ...destinationCityNames].filter(Boolean)),
    ];

    const priorityCityNames = new Set(
      params.priorityCities.map((city) => city.value)
    );

    try {
      setLoadingMessage(GEOCODING_MESSAGE);
      const geocoded = await geocodeCities(selectedCityNames);

      // Same dict shape as the entries in sao_paulo_cities, minus
      // map_location (only needed for the Pygame demo drawing) — id is
      // what the GA actually uses as the unique key for each city.
      const toCityEntity = (name, id) => {
        const [lon, lat] = geocoded.coordinates[name];
        return {
          id,
          name,
          coordinates: [String(lon), String(lat)],
          priority: priorityCityNames.has(name),
        };
      };

      // Without a fixed origin, originCity is null: no city gets id 0 and
      // the vehicles start from different cities.
      const originCity = originCityName ? toCityEntity(originCityName, 0) : null;
      const destinationCities = destinationCityNames.map((name, index) =>
        toCityEntity(name, index + 1)
      );

      // Redraw the map markers for the newly chosen set of cities right
      // away, before the optimization call even starts — the route lines
      // then get drawn on top of this same set once it comes back.
      setCities([originCity, ...destinationCities].filter(Boolean));

      setLoadingMessage(OPTIMIZING_MESSAGE);
      const data = await optimizeRoute({
        ...params,
        vehiclesNumber: Number(params.vehiclesNumber),
        populationSize: Number(params.populationSize),
        mutationProbability: Number(params.mutationProbability),
        originCity,
        destinationCities,
      });
      setResult(data);
      setSnapshotIndex(0);
      setIsPlaying(data.snapshots?.length > 1);
    } catch (err) {
      setError(err.message);
      setResult(null);
    } finally {
      setLoading(false);
      setLoadingMessage(DEFAULT_LOADING_MESSAGE);
    }
  }

  function handleTogglePlay() {
    const lastIndex = (result?.snapshots?.length ?? 1) - 1;
    if (!isPlaying && snapshotIndex >= lastIndex) {
      setSnapshotIndex(0);
    }
    setIsPlaying((playing) => !playing);
  }

  const currentSnapshot = result?.snapshots?.[snapshotIndex];
  const currentSnapshotRoute = currentSnapshot?.route ?? result?.best_route;
  const currentSecondBestRoute = currentSnapshot?.second_best_route;

  return (
    <>
      <main className={`app__body${loading ? " app__body--locked" : ""}`}>
        <RouteForm
          params={params}
          onChange={(nextParams) => {
            setParams(nextParams);
            setFieldErrors({});
          }}
          onSubmit={handleGenerateRoute}
          loading={loading}
          errors={fieldErrors}
        />
        <RouteMap
          cities={cities}
          bestRoute={currentSnapshotRoute}
          secondBestRoute={currentSecondBestRoute}
        >
          <RouteReplayControls
            snapshots={result?.snapshots}
            currentIndex={snapshotIndex}
            isPlaying={isPlaying}
            onChangeIndex={(index) => {
              setIsPlaying(false);
              setSnapshotIndex(index);
            }}
            onTogglePlay={handleTogglePlay}
            playbackSpeed={playbackSpeed}
            onChangeSpeed={setPlaybackSpeed}
          />
        </RouteMap>
        <RightPanel
          snapshots={result?.snapshots}
          currentIndex={snapshotIndex}
          error={error}
          result={result}
        />
      </main>
      <LoadingOverlay visible={loading} message={loadingMessage} />
    </>
  );
}
