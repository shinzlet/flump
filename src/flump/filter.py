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
        return

    @staticmethod
    @abstractmethod
    def default_params(self) -> dict[str, Any]:
        """
        Returns a dictionary of default parameters for the filter where a human-readable name is mapped
        to one of:
        - a tuple of 3 floats (min, max, default)
        - a boolean (default, but user could specify True or False)
        - a string (default, but user could specify any text)
        """
        return {}