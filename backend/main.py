import itertools
from pathlib import Path
import pygame
from pygame.locals import *
import sys
from typing import List

from .config.constants import (
    BLACK,
    FPS,
    GRAY,
    HEIGHT,
    KLEIN_BLUE,
    MUTATION_PROBABILITY,
    NODE_RADIUS,
    POPULATION_SIZE,
    RED,
    WIDTH,
)
from .config.interfaces import CityEntity
from .data import sao_paulo_cities
from .ga import (
    calculate_critical_duration,
    calculate_routes,
    calculate_fitness,
    order_crossover,
    generate_initial_population,
    segment_shuffle_mutation,
    select_parents,
    sort_population_by_fitness,
)
from .llm import prepare_route_data
from .viz.draw_functions import draw_paths, draw_plot, draw_cities

# Path to map image:
ASSETS_DIR = Path(__file__).resolve().parent / "assets"

# Initialize pygame
pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption(
    "Buscando a melhor rota para o TSP da entrega de medicamentos"
)
map = pygame.image.load(str(ASSETS_DIR / "mapa.webp"))
clock = pygame.time.Clock()

# Pre-calculate distances and durations for all city pairs:
calculated_routes = calculate_routes(sao_paulo_cities)
calculated_distances = calculated_routes["cities_distances"]
calculated_durations = calculated_routes["cities_durations"]

# Create initial population
population = generate_initial_population(
    "nearest_neighbor",
    calculated_distances,
    POPULATION_SIZE,
    sao_paulo_cities,
    "São Paulo",
)

# Start generation counter at 1
generation_counter = itertools.count(start=1)

best_fitness_values = []
best_solutions = []
chosen_solution: List[CityEntity]

# Main game loop
running = True

while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_q:
                running = False

    screen.fill(GRAY)
    screen.blit(map, (330, -60))

    generation = next(generation_counter)

    # For all population, dictionary with solution and its fitness value:
    population_with_fitness = [
        {
            "individual": individual,
            "total_distance": calculate_fitness(calculated_distances, individual),
            "critical_duration": calculate_critical_duration(
                calculated_durations, individual
            ),
        }
        for individual in population
    ]

    # Same as above but sorted according to restrictions and best fitness (distance):
    sorted_population_with_fitness = sort_population_by_fitness(
        calculated_durations, population_with_fitness
    )

    best_individual = sorted_population_with_fitness[0]

    best_solution = best_individual["individual"]
    best_solution_fitness = best_individual["total_distance"]
    best_solution_critical_duration = best_individual["critical_duration"]

    best_fitness_values.append(best_solution_fitness)
    best_solutions.append(best_solution)
    chosen_solution = best_individual

    draw_plot(
        screen,
        list(range(len(best_fitness_values))),
        best_fitness_values,
        y_label="Fitness - Distance (pxls)",
    )

    draw_cities(screen, sao_paulo_cities, RED, NODE_RADIUS)
    draw_paths(screen, best_solution, KLEIN_BLUE, width=4)

    # Also draws second best solution for every generation:
    draw_paths(screen, sorted_population_with_fitness[1]["individual"], BLACK, width=2)

    # Keeps the four best individuals for ELITISM:
    new_population = [
        sorted_population_with_fitness[0]["individual"],
        sorted_population_with_fitness[1]["individual"],
        sorted_population_with_fitness[2]["individual"],
        sorted_population_with_fitness[3]["individual"],
    ]

    while len(new_population) < POPULATION_SIZE:

        parents = select_parents(calculated_durations, population_with_fitness)

        children = order_crossover(parents)
        child1 = segment_shuffle_mutation(children[0], MUTATION_PROBABILITY, True)
        child2 = segment_shuffle_mutation(children[1], MUTATION_PROBABILITY, True)

        new_population.append(child1)
        new_population.append(child2)

    population = new_population

    stability_reached = len(best_fitness_values) > 500 and all(
        best_fitness == best_fitness_values[-500]
        for best_fitness in best_fitness_values[len(best_fitness_values) - 100 :]
    )

    if len(best_fitness_values) > 3000 or stability_reached:
        running = False

    pygame.display.flip()
    clock.tick(FPS)

if not running:
    prepare_route_data(calculated_routes, chosen_solution)

# exit software
pygame.quit()
sys.exit()
