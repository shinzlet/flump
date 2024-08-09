from PIL import Image, ImageOps
from typing import Any
from ..filter import Filter

class InvertLuminance(Filter):
    def name() -> str:
        return "Invert Luminance"

    def apply(image: Image.Image, params: dict[str, float | str | bool]) -> Image.Image:
        # Convert to LAB color space
        lab_image = image.convert('LAB')

        # Split into L, A, and B channels
        l, a, b = lab_image.split()

        # Invert the L channel (luminance)
        inverted_l = ImageOps.invert(l)

        # Merge the inverted L channel with original A and B channels
        inverted_lab = Image.merge('LAB', (inverted_l, a, b))

        # Convert back to RGB
        inverted_image = inverted_lab.convert('RGB')
        inverted_image.putalpha(image.getchannel('A'))

        return inverted_image

    def default_params() -> dict[str, Any]:
        return {}