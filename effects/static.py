# P1-Visualizer/effects/static.py
from .base_effect import Effects
from .converts import rgb_to_rgbw
from .schemas import StaticParams


class StaticEffect(Effects):
    params: StaticParams

    def get_next_frame(self):
        brightness_factor = self.params.brightness / 100
        # Correctie: Toegang tot Color object attributen met '.'
        red, green, blue, white = rgb_to_rgbw(
            self.params.color[0].red * brightness_factor,
            self.params.color[0].green * brightness_factor,
            self.params.color[0].blue * brightness_factor,
        )
        frame = [[red, green, blue, white]] * self.num_leds
        return frame
