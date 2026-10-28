import Select from "react-select";
import AsyncSelect from "react-select/async";
import { searchCities } from "../api";

const POPULATION_TYPES = [
  { value: "random", label: "Randômico" },
  { value: "nearest_neighbor", label: "Vizinho mais próximo" },
  { value: "cheapest_insertion", label: "Inserção mais barata" },
];

const MIN_SEARCH_LENGTH = 2;

function getSelectStyles(hasError) {
  return {
    control: (base) => ({
      ...base,
      borderColor: hasError ? "#c0392b" : "#d7dbe3",
      minHeight: "38px",
      fontSize: "13px",
    }),
    menu: (base) => ({ ...base, fontSize: "13px", zIndex: 20 }),
  };
}

async function loadCityOptions(inputValue) {
  if (inputValue.trim().length < MIN_SEARCH_LENGTH) {
    return [];
  }

  const cities = await searchCities(inputValue);
  return cities.map((city) => ({ value: city.name, label: city.name }));
}

export default function RouteForm({ params, onChange, onSubmit, loading, errors = {} }) {
  return (
    <aside className="sidebar">
      <div className="sidebar__header">
        <span className="sidebar__icon">📋</span>
        <div>
          <h2>Planeje sua rota</h2>
          <p>
            Escolha as cidades da rota e configure os parâmetros do algoritmo genético para gerar uma
            rota otimizada para a sua viagem.
          </p>
        </div>
      </div>

      <div className="sidebar__form">
        <div className="field">
          <label>
            <span className="field__step">1</span>
            Escolha uma cidade de origem:
          </label>
          <AsyncSelect
            cacheOptions
            defaultOptions={false}
            loadOptions={loadCityOptions}
            value={params.originCity}
            onChange={(selected) => onChange({ ...params, originCity: selected })}
            placeholder="Digite ao menos 2 letras..."
            noOptionsMessage={({ inputValue }) =>
              inputValue.trim().length < MIN_SEARCH_LENGTH
                ? "Digite ao menos 2 letras para buscar"
                : "Nenhuma cidade encontrada"
            }
            isClearable
            styles={getSelectStyles(!!errors.originCity)}
          />
          {errors.originCity && (
            <small className="field__error">{errors.originCity}</small>
          )}
        </div>

        <div className="field">
          <label>
            <span className="field__step">2</span>
            Selecione as cidades que farão parte da sua rota:
          </label>
          <AsyncSelect
            isMulti
            cacheOptions
            defaultOptions={false}
            loadOptions={loadCityOptions}
            value={params.destinationCities}
            onChange={(selected) => {
              const destinationCities = selected ?? [];
              const destinationValues = destinationCities.map((city) => city.value);
              onChange({
                ...params,
                destinationCities,
                // Drop any priority city that's no longer a selected destination.
                priorityCities: params.priorityCities.filter((city) =>
                  destinationValues.includes(city.value)
                ),
              });
            }}
            placeholder="Digite ao menos 2 letras..."
            noOptionsMessage={({ inputValue }) =>
              inputValue.trim().length < MIN_SEARCH_LENGTH
                ? "Digite ao menos 2 letras para buscar"
                : "Nenhuma cidade encontrada"
            }
            styles={getSelectStyles(!!errors.destinationCities)}
          />
          {errors.destinationCities && (
            <small className="field__error">{errors.destinationCities}</small>
          )}
        </div>

        <div className="field">
          <label>
            <span className="field__step">3</span>
            <span className="field__label-text">
              Selecione quais cidades terão entrega prioritária:
              <small className="field__label-hint">
                (mesmo dia, até às 22h)
              </small>
            </span>
          </label>
          <Select
            isMulti
            options={params.destinationCities}
            value={params.priorityCities}
            onChange={(selected) =>
              onChange({ ...params, priorityCities: selected ?? [] })
            }
            placeholder="Selecione entre as cidades da rota..."
            noOptionsMessage={() =>
              params.destinationCities.length === 0
                ? "Selecione primeiro as cidades da rota"
                : "Nenhuma cidade disponível"
            }
            styles={getSelectStyles(false)}
          />
        </div>

        <div className="field">
          <label>
            <span className="field__step">4</span>
            Como você quer gerar sua população inicial?
          </label>
          <select
            value={params.populationType}
            onChange={(event) =>
              onChange({ ...params, populationType: event.target.value })
            }
            className={errors.populationType ? "field--error" : ""}
          >
            {POPULATION_TYPES.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
          {errors.populationType && (
            <small className="field__error">{errors.populationType}</small>
          )}
        </div>

        <div className="field">
          <label>
            <span className="field__step">5</span>
            Qual o tamanho desejado da população?
          </label>
          <input
            type="number"
            min={4}
            step={1}
            value={params.populationSize}
            onChange={(event) =>
              onChange({ ...params, populationSize: Number(event.target.value) })
            }
            className={errors.populationSize ? "field--error" : ""}
          />
          {errors.populationSize ? (
            <small className="field__error">{errors.populationSize}</small>
          ) : (
            <small>Valores recomendados: 50, 100, 500, 1000, 3000</small>
          )}
        </div>

        <div className="field">
          <label>
            <span className="field__step">6</span>
            Qual deve ser a probabilidade de mutação nas gerações?
          </label>
          <input
            type="number"
            min={0}
            max={1}
            step={0.1}
            value={params.mutationProbability}
            onChange={(event) => {
              const raw = Number(event.target.value);
              const clamped = Number.isNaN(raw)
                ? params.mutationProbability
                : Math.min(1, Math.max(0, raw));
              onChange({ ...params, mutationProbability: clamped });
            }}
            className={errors.mutationProbability ? "field--error" : ""}
          />
          {errors.mutationProbability ? (
            <small className="field__error">{errors.mutationProbability}</small>
          ) : (
            <small>Valores entre 0.0 e 1.0 (ex.: 0.1, 0.2, 0.3...)</small>
          )}
        </div>

        <button className="primary-button" onClick={onSubmit} disabled={loading}>
          {loading ? "Gerando rota..." : "🧬 Gerar rota"}
        </button>
      </div>
    </aside>
  );
}
