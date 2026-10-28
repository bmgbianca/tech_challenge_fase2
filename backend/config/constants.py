# constants for pygame rendering:
WIDTH, HEIGHT = 1300, 700
NODE_RADIUS = 10
FPS = 30
PLOT_X_OFFSET = 450

# constants for colors in our visual representation:
BLACK = (35, 35, 35)
GRAY = (219, 219, 219)
RED = (227, 38, 54)
KLEIN_BLUE = (0, 47, 167)

# constants for genetic algorithm:
N_CITIES = 16
POPULATION_SIZE = 1000
MIN_POPULATION_SIZE = 50
MUTATION_PROBABILITY = 0.5
MAX_GENERATIONS = 3000
PLATEAU_WINDOW = 500
SNAPSHOT_EVERY = 50
VALID_POPULATION_TYPES = {"random", "nearest_neighbor", "cheapest_insertion"}

"""TIME RESTRICTION:
Truck leaves at 5A.M and must arrive in priority cities until 10P.M
Therefore, truck has 17 hours to arrive in all priority cities
TIME_LIMIT constant represent 17 hours in seconds
"""
TIME_LIMIT = 61200
