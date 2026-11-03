// Sets the origin city in the form params. The origin cannot also be a
// destination (or a priority delivery), so it is removed from both lists.
export function applyOriginCity(params, originCity) {
  const originName = originCity?.value;
  const isNotOrigin = (city) => city.value !== originName;

  return {
    ...params,
    originCity,
    destinationCities: params.destinationCities.filter(isNotOrigin),
    priorityCities: params.priorityCities.filter(isNotOrigin),
  };
}
