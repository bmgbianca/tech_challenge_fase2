import random
from operator import itemgetter

from ..models import Individual, SegmentShuffleMutationArgs


def segment_shuffle_mutation(arg: SegmentShuffleMutationArgs) -> Individual:
    individual, mutation_probability, is_origin = itemgetter(
        "individual", "mutation_probability", "is_origin"
    )(arg)

    will_mutation_happen = random.random() < mutation_probability
    vehicles_prone_to_mutation = []
    fixed_cities = 1 if is_origin else 0

    """A vehicle can only be mutated if it has at least two cities that
    are not fixed (otherwise there is nothing to shuffle):"""
    for index, vehicle in enumerate(individual):
        if len(vehicle) - fixed_cities >= 2:
            vehicles_prone_to_mutation.append(index)

    if not will_mutation_happen or len(vehicles_prone_to_mutation) == 0:
        return individual

    vehicle_to_mutate_index = random.choice(vehicles_prone_to_mutation)
    mutation_vehicle = list(individual[vehicle_to_mutate_index])

    vehicle_length = len(mutation_vehicle)
    mutable_cities = vehicle_length - fixed_cities

    """Defines the intensity of mutation, i.e.,
    how many cities will be shuffled: """
    max_mutation_intensity = min(5, mutable_cities)
    mutation_intensity = random.randint(2, max_mutation_intensity)

    start_index = random.randint(fixed_cities, vehicle_length - mutation_intensity)
    end_index = start_index + mutation_intensity

    mutation_segment = mutation_vehicle[start_index:end_index]
    mutation_indices = [i for i in range(start_index, end_index)]
    shuffled_mutation_indices = list(mutation_indices)

    while mutation_indices == shuffled_mutation_indices:
        random.shuffle(shuffled_mutation_indices)

    cities_positions = zip(shuffled_mutation_indices, mutation_segment)

    for position, city in cities_positions:
        mutation_vehicle[position] = city

    new_individual = list(individual)
    new_individual[vehicle_to_mutate_index] = mutation_vehicle
    return new_individual
