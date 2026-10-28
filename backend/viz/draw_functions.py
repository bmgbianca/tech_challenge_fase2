import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_agg import FigureCanvasAgg
import numpy as np
import pygame
from typing import List, Tuple

from backend.config.constants import HEIGHT
from backend.config.interfaces import CityEntity


# Draw a plot on a Pygame screen using Matplotlib:
def draw_plot(
    screen: pygame.Surface,
    x_axis: list,
    y_axis: list,
    x_label: str = "Generation",
    y_label: str = "Fitness",
) -> None:

    fig, ax = plt.subplots(figsize=(5.5, 5.5), dpi=100)
    ax.plot(x_axis, y_axis)

    ax.set_ylabel(y_label)
    ax.set_xlabel(x_label)
    plt.tight_layout()

    canvas = FigureCanvasAgg(fig)
    canvas.draw()
    renderer = canvas.get_renderer()
    raw_data = renderer.tostring_argb()

    size = canvas.get_width_height()
    surf = pygame.image.fromstring(raw_data, size, "ARGB")
    screen.blit(surf, (20, 85))


# Draws circles representing cities on the given Pygame screen:
def draw_cities(
    screen: pygame.Surface,
    cities: List[CityEntity],
    rgb_color: Tuple[int, int, int],
    node_radius: int,
) -> None:

    for city in cities:
        pygame.draw.circle(screen, rgb_color, city["map_location"], node_radius)


# Draw best solution paths on Pygame screen:
def draw_paths(
    screen: pygame.Surface,
    solution: List[CityEntity],
    rgb_color: Tuple[int, int, int],
    width: int = 1,
):
    path = [city["map_location"] for city in solution]
    pygame.draw.lines(screen, rgb_color, True, path, width=width)
