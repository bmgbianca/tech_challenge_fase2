// The LLM is asked to start the text of each vehicle with its number between
// brackets ("[1]", "[2]", ...). The markers are removed and used only to
// split the text into one item per vehicle.
const MARKER = /\[(\d+)\]/g;

// Returns one text per vehicle. If the markers don't match the vehicles
// (missing, repeated or out of order), they can't be trusted and the whole
// text is returned as a single item, with the markers removed.
export function splitDriverInstructions(instructions, vehiclesCount) {
  if (!instructions) return [];

  const markers = [...instructions.matchAll(MARKER)];
  const fullText = instructions.replace(MARKER, "").trim();

  const isInOrder =
    markers.length === vehiclesCount &&
    markers.every((marker, index) => Number(marker[1]) === index + 1);

  if (vehiclesCount > 1 && isInOrder) {
    const texts = instructions
      .split(MARKER)
      .filter((_, index) => index % 2 === 0)
      .map((text) => text.trim())
      .slice(1);

    if (texts.every(Boolean)) return texts;
  }

  return [fullText];
}
