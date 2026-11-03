from dataclasses import dataclass

from ..common import Matrix, Individual, PopulationWithFitness


@dataclass
class SelectParentsArgs:
    duration_matrix: Matrix
    population_fitness: PopulationWithFitness


@dataclass
class SelectWinnerSolutionArgs:
    duration_matrix: Matrix
    solutions: PopulationWithFitness


@dataclass
class IsSolutionValidArgs:
    duration_matrix: Matrix
    solution: Individual


@dataclass
class SelectBestInvalidSolutionArgs:
    duration_matrix: Matrix
    solutions: PopulationWithFitness


@dataclass
class SortPopulationByFitnessArgs:
    duration_matrix: Matrix
    population_fitness: PopulationWithFitness
