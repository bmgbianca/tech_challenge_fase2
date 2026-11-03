"""Disclaimer: this file runs backend representation for the
genetic algorithm. Here, the idea is to keep all constant values
really constants. For experimenting different cities, population
sizes, priorities, etc, it's recommended to use the web app version
"""

import itertools
from pathlib import Path
import pygame
from pygame.locals import *
import sys

from .constants import (
    CITIES,
    FPS,
    ASH_GRAY,
    CHARCOAL_GRAY,
    GRAY,
    SLATE_GRAY,
    HEIGHT,
    DODGER_BLUE,
    KLEIN_BLUE,
    PACIFIC_BLUE,
    MUTATION_PROBABILITY,
    NODE_RADIUS,
    ORIGIN,
    POPULATION_SIZE,
    RED,
    TIME_LIMIT,
    VEHICLES_NUMBER,
    WIDTH,
)
from .data import sao_paulo_cities
from .models import SelectParentsArgs, SortPopulationByFitnessArgs
from .ga import (
    are_priorities_on_time,
    calculate_routes,
    calculate_fitness,
    order_crossover,
    generate_initial_population,
    InitialPopulationArgs,
    segment_shuffle_mutation,
    select_parents,
    sort_population_by_fitness,
)
from .viz.draw_functions import draw_paths, draw_plot, draw_cities

# Path to map image:
ASSETS_DIR = Path(__file__).resolve().parent / "assets"

# Initialize pygame
pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption(
    "Buscando as melhores rotas para o VRP da entrega de medicamentos"
)
map = pygame.image.load(str(ASSETS_DIR / "mapa.webp"))
clock = pygame.time.Clock()

# Pre-calculate distances and durations for all city pairs:
calculated_routes = calculate_routes(sao_paulo_cities)
calculated_distances = calculated_routes["cities_distances"]
calculated_durations = calculated_routes["cities_durations"]

# Create initial population
population = generate_initial_population(
    InitialPopulationArgs(
        population_strategy="nearest_neighbor",  # este argumento pode ser alterado aqui (opções: "random", "nearest_neighbor", "cheapest_insertion")
        distances_matrix=calculated_distances,
        population_size=POPULATION_SIZE,
        cities=CITIES,
        origin_city_name=ORIGIN,
        vehicles_number=VEHICLES_NUMBER,
    )
)

# Start generation counter at 1
generation_counter = itertools.count(start=1)

best_fitness_values = []
best_solutions = []
chosen_solution: dict

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

    """ For all population, dictionary with solution (individual), 
    its fitness value (total_distance) and a boolean for if
    priorities cities are being visited on time:"""
    population_with_fitness = [
        {
            "individual": individual,
            "total_distance": calculate_fitness(calculated_distances, individual),
            "priorities_on_time": are_priorities_on_time(
                calculated_durations, individual, TIME_LIMIT
            ),
        }
        for individual in population
    ]

    # Same as above but sorted according to restrictions and
    # best fitness (distance):
    sorted_population_with_fitness = sort_population_by_fitness(
        SortPopulationByFitnessArgs(
            duration_matrix=calculated_durations,
            population_fitness=population_with_fitness,
        )
    )

    best_solution = sorted_population_with_fitness[0]

    best_individual = best_solution["individual"]
    best_solution_fitness = best_solution["total_distance"]

    best_fitness_values.append(best_solution_fitness)
    best_solutions.append(best_solution)
    chosen_solution = best_solution

    draw_plot(
        screen,
        list(range(len(best_fitness_values))),
        best_fitness_values,
        y_label="Fitness - Distance (pxls)",
    )

    draw_cities(screen, sao_paulo_cities, RED, NODE_RADIUS)

    # Draws best solution route for every generation:
    draw_paths(
        screen, best_individual, [KLEIN_BLUE, DODGER_BLUE, PACIFIC_BLUE], width=4
    )

    # Also draws second best solution route for every generation:
    draw_paths(
        screen,
        sorted_population_with_fitness[1]["individual"],
        [ASH_GRAY, CHARCOAL_GRAY, SLATE_GRAY],
        width=2,
    )

    print(f"Generation {generation}: {best_solution_fitness}")

    # Keeps the four best individuals for ELITISM:
    new_population = [
        sorted_population_with_fitness[0]["individual"],
        sorted_population_with_fitness[1]["individual"],
        sorted_population_with_fitness[2]["individual"],
        sorted_population_with_fitness[3]["individual"],
    ]

    while len(new_population) < POPULATION_SIZE:

        parents = select_parents(
            SelectParentsArgs(
                duration_matrix=calculated_durations,
                population_fitness=population_with_fitness,
            )
        )

        children = order_crossover({"parents": parents, "is_origin": True})
        child1 = segment_shuffle_mutation(
            {
                "individual": children[0],
                "mutation_probability": MUTATION_PROBABILITY,
                "is_origin": True,
            }
        )
        child2 = segment_shuffle_mutation(
            {
                "individual": children[1],
                "mutation_probability": MUTATION_PROBABILITY,
                "is_origin": True,
            }
        )

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
        # Summary of the final solution (the web app is the one that asks the
        # LLM for driver instructions, so this demo spends no OpenAI credits):
        print("\nMelhor solução encontrada:")
        for number, vehicle in enumerate(chosen_solution["individual"], start=1):
            print(f"Veículo {number}: " + " -> ".join(city["name"] for city in vehicle))
        print(f"Distância total: {chosen_solution['total_distance']:.1f}")
        print(
            "Prioridades dentro do prazo: "
            + ("sim" if chosen_solution["priorities_on_time"] else "NÃO")
        )

# exit software
pygame.quit()
sys.exit()
