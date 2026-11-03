from typing import TypedDict

from ..common import Individual


class SegmentShuffleMutationArgs(TypedDict):
    individual: Individual
    mutation_probability: float
    is_origin: bool | None
