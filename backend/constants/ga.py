from typing import Literal, get_args

from ..data import sao_paulo_cities

N_CITIES = 16
CITIES = sao_paulo_cities
ORIGIN = "São Paulo"
POPULATION_SIZE = 1000
MIN_POPULATION_SIZE = 50
MUTATION_PROBABILITY = 0.5
MAX_GENERATIONS = 3000
PLATEAU_WINDOW = 500
VEHICLES_NUMBER = 3
PopulationType = Literal["random", "nearest_neighbor", "cheapest_insertion"]
VALID_POPULATION_TYPES = set(get_args(PopulationType))

"""TIME RESTRICTION:
Truck leaves at 5A.M and must arrive in priority cities until 10P.M
Therefore, truck has 17 hours to arrive in all priority cities
TIME_LIMIT constant represent 17 hours in seconds
"""
TIME_LIMIT = 61200
