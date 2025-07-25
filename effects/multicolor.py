# P1-Visualizer/effects/multicolor.py

import colorsys
from .base_effect import Effects
from .schemas import EffectModel, MulticolorParams
from .converts import rgb_to_rgbw

class MulticolorEffect(Effects):
    """
    Een effect dat de LED's door een regenboog van kleuren laat lopen.
    """
    def __init__(self, model: EffectModel):
        super().__init__(model)
        # Type checking for parameters
        if not isinstance(self.params, MulticolorParams):
            raise ValueError("Parameters for MulticolorEffect must be of type MulticolorParams")

        self.initial_hsv_color = [0.0, 1.0, 1.0] # Hue, Saturation, Value
        self.current_frame = 0 # Initialize current_frame to 0

    def get_next_frame(self):
        """
        Retourneert het volgende frame voor het Multicolor effect.
        De kleuren lopen cyclisch door de HSV-kleurenruimte.
        """
        brightness_factor = self.params.brightness / 100.0

        # Update de hue voor de volgende frame
        # De snelheid van de kleurverandering kan worden aangepepast door de 0.01 te wijzigen
        # of door een snelheidsparameter toe te voegen aan MulticolorParams.
        self.initial_hsv_color[0] = (self.initial_hsv_color[0] + (self.fps / 33.0) * 0.005) % 1.0 # Adjust speed based on FPS

        red_hsv, green_hsv, blue_hsv = colorsys.hsv_to_rgb(*self.initial_hsv_color)

        red = int(red_hsv * 255 * brightness_factor)
        green = int(green_hsv * 255 * brightness_factor)
        blue = int(blue_hsv * 255 * brightness_factor)

        # Zorg ervoor dat de kleuren binnen het 0-255 bereik blijven
        red = max(0, min(255, red))
        green = max(0, min(255, green))
        blue = max(0, min(255, blue))

        # Converteer naar RGBW indien nodig en retourneer het frame
        return [rgb_to_rgbw(red, green, blue)] * self.num_leds

    # Helper function to get color from a color wheel (if needed for more complex multicolor)
    def _wheel(self, pos):
        """
        Generates a color from a color wheel.
        0-84: Red to Green
        85-169: Green to Blue
        170-255: Blue to Red
        """
        if pos < 85:
            return rgb_to_rgbw(pos * 3, 255 - pos * 3, 0)
        elif pos < 170:
            pos -= 85
            return rgb_to_rgbw(255 - pos * 3, 0, pos * 3)
        else:
            pos -= 170
            return rgb_to_rgbw(0, pos * 3, 255 - pos * 3)

