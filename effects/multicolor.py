# P1-Visualizer/effects/multicolor.py

import colorsys
from .base_effect import Effects
from .schemas import EffectModel, MulticolorParams
from utils import rgb_to_rgbw # Correcte import

class MulticolorEffect(Effects):
    """
    Multicolor effect dat een regenboog van kleuren door de LEDs fietst.
    """
    def __init__(self, model: EffectModel):
        super().__init__(model)
        if not isinstance(self.params, MulticolorParams):
            raise ValueError("Parameters for MulticolorEffect must be of type MulticolorParams")
            
        self.hue = 0.0 # Startkleur (rood in HSV)

    def get_next_frame(self, delta_time: float = 0.0):
        """
        Genereert het volgende frame voor het multicolor effect.
        """
        brightness_factor = self.params.brightness / 100.0
        
        # Snelheid (1-5) schaalt de basis snelheid van kleurverandering.
        hue_change_per_second = 0.1 
        self.hue = (self.hue + hue_change_per_second * self.speed * delta_time) % 1.0
        
        # Converteer de huidige HSV-kleur naar RGB
        r_float, g_float, b_float = colorsys.hsv_to_rgb(self.hue, 1.0, 1.0)
        
        # Pas helderheid toe en converteer naar 0-255 integer waarden
        red = int(r_float * 255 * brightness_factor)
        green = int(g_float * 255 * brightness_factor)
        blue = int(b_float * 255 * brightness_factor)
        
        # Converteer naar RGBW en stuur naar alle LEDs
        return [rgb_to_rgbw(red, green, blue)] * self.num_leds