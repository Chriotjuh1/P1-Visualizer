# multicolor.py
# Gebruik relatieve imports, ervan uitgaande dat 'effects.py', 'schemas.py' en 'converts.py'
# zich in dezelfde map bevinden als dit bestand (binnen de 'effects' map).
from .effects import Effects
from .schemas import MulticolorParams
from .converts import rgb_to_rgbw
import colorsys


class MulticolorEffect(Effects):
    params: MulticolorParams
    initial_hsv_color: list = [0.0, 1.0, 1.0]
    color_index: int = 0

    def get_next_frame(self):
        frame = [[0, 0, 0, 0]] * self.num_leds
        brightness_factor = self.params.brightness / 100

        red_hsv, green_hsv, blue_hsv = colorsys.hsv_to_rgb(*self.initial_hsv_color)
        self.initial_hsv_color[0] = round(self.initial_hsv_color[0] + 0.002, 3)
        if self.initial_hsv_color[0] > 1:
            self.initial_hsv_color[0] = 0

        red = int(red_hsv * 255 * brightness_factor)
        green = int(green_hsv * 255 * brightness_factor)
        blue = int(blue_hsv * 255 * brightness_factor)

        red, green, blue, white = rgb_to_rgbw(red, green, blue)

        frame = [[red, green, blue, white]] * self.num_leds
        print(frame)
        return frame