from typing import List
import random

from ..config import Individual

""" Perform order crossover (OX) between two parent sequences to
create two child sequences. """


def order_crossover(parents: List[Individual]) -> List[Individual]:

    parent1 = parents[0]
    parent2 = parents[1]
    cities_length = len(parent1)

    """Used cities_lenght - 2 to avoid the last city being selected
    as the start index."""

    start_index = random.randint(0, cities_length - 2)

    """Used cities_lenght to allow the last city to be
    included in the range."""
    end_index = random.randint(start_index + 1, cities_length)

    child1 = [None] * cities_length
    child2 = [None] * cities_length

    child1[start_index:end_index] = parent1[start_index:end_index]
    child2[start_index:end_index] = parent2[start_index:end_index]

    remaining_positions = [
        i for i in range(cities_length) if i < start_index or i >= end_index
    ]

    child_1_remaining_genes = [gene for gene in parent2 if gene not in child1]
    child_2_remaining_genes = [gene for gene in parent1 if gene not in child2]

    for position, gene in zip(remaining_positions, child_1_remaining_genes):
        child1[position] = gene

    for position, gene in zip(remaining_positions, child_2_remaining_genes):
        child2[position] = gene

    return [child1, child2]
