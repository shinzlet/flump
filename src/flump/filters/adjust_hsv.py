from PIL import Image
from typing import Any
from ..filter import Filter

class AdjustHSV(Filter):
    def name() -> str:
        return "Adjust HSV"

    def apply(image: Image.Image, params: dict[str, float | str | bool]) -> Image.Image:
        h, s, v = image.convert("HSV").split()

        h = h.point(lambda i: i + params["Hue"])
        s = s.point(lambda i: i * params["Saturation"])
        v = v.point(lambda i: i * params["Value"])

        return Image.merge("HSV", (h, s, v)).convert("RGB")

    def default_params() -> dict[str, Any]:
        return {
            "Hue": {"type": "float", "min": -180, "max": 180, "default": 0},
            "Saturation": {"type": "float", "min": 0, "max": 2, "default": 1},
            "Value": {"type": "float", "min": 0, "max": 2, "default": 1}
        }