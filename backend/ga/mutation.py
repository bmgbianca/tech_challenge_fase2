import copy
import random

from ..config import Individual


def segment_shuffle_mutation(
    individual: Individual,
    mutation_probability: float,
    fixed_first_index: bool | None = None,
) -> Individual:

    if random.random() < mutation_probability:
        individual_length = len(individual)

        """Defines the intensity of mutation, i.e.,
        how many cities will be shuffled: """
        max_mutation_intensity = 5 if individual_length > 5 else individual_length - 1
        mutation_intensity = random.randint(2, max_mutation_intensity)

        initial_start_index_range = 1 if fixed_first_index else 0

        start_index = random.randint(
            initial_start_index_range, len(individual) - mutation_intensity
        )
        end_index = start_index + mutation_intensity

        mutation_segment = individual[start_index:end_index]
        mutation_indices = [i for i in range(start_index, end_index)]
        shuffled_mutation_indices = copy.deepcopy(mutation_indices)

        while mutation_indices == shuffled_mutation_indices:
            random.shuffle(shuffled_mutation_indices)

        cities_positions = zip(shuffled_mutation_indices, mutation_segment)

        for position, city in cities_positions:
            individual[position] = city

    return individual
