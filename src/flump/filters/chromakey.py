from PIL import Image
import numpy as np
from typing import Any
from ..filter import Filter

class ChromaKey(Filter):
    def name() -> str:
        return "Chroma Key"

    def apply(image: Image.Image, params: dict[str, float | str | bool]) -> Image.Image:
        # Given a key color hex string and a tolerance range, replace the key color with transparency
        # i.e. alpha = 0 if dist < tola, alpha interpolates from 0 to 1 if tola < dist < tolb, alpha = 1 if dist > tolb
        # return full frame of key color as demo:
        try:
            key = params['Key']
            key_l, key_a, key_b = [ch.getpixel((0, 0)) for ch in Image.new('RGB', (1, 1), color=key).convert('LAB').split()]
            tola = params['Strength']
            tolb = params['Feather']
            luminance_weight = params['Luminance Weight']

            lab_image = image.copy().convert('LAB')
            l, a, b = (np.array(ch, dtype=np.float32) for ch in lab_image.split())
            distance = np.sqrt(((luminance_weight * (l - key_l)) ** 2) + (a - key_a) ** 2 + (b - key_b) ** 2)
            distance -= np.min(distance)
            distance /= np.max(distance)
            
            r, g, b, alpha = image.convert('RGBA').split()
            alpha = np.array(alpha, dtype=np.float32) / 255
            if tolb == 0:
                alpha *= (distance >= tola).astype(np.float32)
            else:
                alpha *= np.maximum(0, np.minimum(1, (distance - tola) / tolb))
            
            alpha = Image.fromarray((alpha * 255).astype(np.uint8), mode='L')
            return Image.merge('RGBA', (r, g, b, alpha))
        except Exception as e:
            print(e.with_traceback(None))
            return image

    def default_params() -> dict[str, Any]:
        return {
            'Key': {"type": "color", "default": (100, 200, 50)},
            'Strength': {"type": "float", "min": 0, "max": 1, "default": 0.1},
            'Feather': {"type": "float", "min": 0, "max": 1, "default": 0.1},
            'Luminance Weight': {"type": "float", "min": 0, "max": 1, "default": 2},
        }