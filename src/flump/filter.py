from abc import ABC, abstractmethod
from PIL import Image
from typing import Any

class Filter(ABC):
    @staticmethod
    def name() -> str:
        return __class__.__name__

    @staticmethod
    @abstractmethod
    def apply(image: Image.Image, params: dict[str, float | str | bool]) -> Image.Image:
        """
        Applies the filter to the given image with the given parameters and returns the result. params is a dictionary
        of parameter names mapped to their values. The keys of the dictionary are the same as the keys of the dictionary
        returned by default_params. The values of the dictionary are floats, strings, booleans, or 3-tuples of integers
        representing RGB colors, as specified by the default_params method.
        """
        return

    @staticmethod
    @abstractmethod
    def default_params(self) -> dict[str, Any]:
        """
        Returns a dictionary of default parameters for the filter where a human-readable name is mapped
        to one of:
        - a float specifier: {"type": "float", "min": min, "max": max, "default": default}
        - a boolean specifier: {"type": "bool", "default": default}
        - a string specifier: {"type": "str", "default": default}
        - a color specifier: {"type": "color", "default": (r, g, b)}
        """
        return {}