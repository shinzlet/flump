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
            key = params['key']
            key_l, key_a, key_b = [ch.getpixel((0, 0)) for ch in Image.new('RGB', (1, 1), color=key).convert('LAB').split()]
            tola = params['tola']
            tolb = params['tolb']
            luminance_weight = params['Luminance Weight']
            if tola >= tolb:
                return image
            r, g, b, src_alpha = image.copy().convert('RGBA').split()
            image = image.convert('LAB')
            # image = np.array(image).astype(np.float32)
            l, a, b = (np.array(ch, dtype=np.float32) for ch in image.split())
            distance = np.sqrt(((luminance_weight * (l - key_l)) ** 2) + (a - key_a) ** 2 + (b - key_b) ** 2)
            distance -= np.min(distance)
            abs_tol = np.max(distance) * tola
            
            # print(abs_tol)
            # print(distance[:4, :4], distance[:4, :4] > abs_tol)
            alpha = ((distance - np.min(distance)) >= abs_tol).astype(np.float32) * np.array(src_alpha, dtype=np.float32) / 255
            alpha = Image.fromarray((alpha * 255).astype(np.uint8), mode='L')
            
            return Image.merge('RGBA', (r, g, b, alpha))
        except Exception as e:
            # print stack trace
            print("Error in ChromaKey filter:")
            #   
            raise e
            print(e)
            return image

    def default_params() -> dict[str, Any]:
        return {
            'tola': {"type": "float", "min": 0, "max": 1, "default": 0.1},
            'tolb': {"type": "float", "min": 0, "max": 1, "default": 0.1},
            'Luminance Weight': {"type": "float", "min": 0, "max": 1, "default": 2},
            'key': {"type": "color", "default": (100, 200, 50)}
        }