from PIL import Image
from typing import Any
from ..filter import Filter

class AdjustRGB(Filter):
    def name() -> str:
        return "Adjust RGB"

    def apply(image: Image.Image, params: dict[str, float | str | bool]) -> Image.Image:
        r, g, b, a = image.split()

        def create_modulator(channel: str) -> int:
            scale = params[channel]
            def modulator(intensity):
                if scale == 0:
                    return 0
                normalized_intensity = intensity / 255
                mapped_intensity = normalized_intensity ** (1 / scale - 1)
                return int(mapped_intensity * 255)
            return modulator

        r = r.point(create_modulator("Red"))
        g = g.point(create_modulator("Green"))
        b = b.point(create_modulator("Blue"))

        return Image.merge("RGBA", (r, g, b, a))
    
    def default_params() -> dict[str, Any]:
        return {
            "Red": {"type": "float", "min": 0, "max": 1, "default": 0.5},
            "Green": {"type": "float", "min": 0, "max": 1, "default": 0.5},
            "Blue": {"type": "float", "min": 0, "max": 1, "default": 0.5}
        }