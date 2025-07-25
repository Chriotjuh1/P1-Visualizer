# P1-Visualizer/effects/breathing.py
from .base_effect import Effects
from .converts import rgb_to_rgbw
from .schemas import BreathingParams


class BreathingEffect(Effects):
    params: BreathingParams
    current_breathing_factor: int = 0
    rising: bool = True

    def get_next_frame(self):
        brightness = self.params.brightness / 100.0

        if self.current_breathing_factor >= 255.0:
            self.rising = False
        elif self.current_breathing_factor <= 0:
            self.rising = True

        self.current_breathing_factor += 1 if self.rising else -1

        current_breathing_factor = self.current_breathing_factor / 255

        # Correctie: Toegang tot Color object attributen met '.'
        r_breath = self.params.color[0].red * current_breathing_factor
        g_breath = self.params.color[0].green * current_breathing_factor
        b_breath = self.params.color[0].blue * current_breathing_factor

        red = int(r_breath * brightness)
        green = int(g_breath * brightness)
        blue = int(b_breath * brightness)

        red, green, blue, white = rgb_to_rgbw(red, green, blue)

        final_color = [red, green, blue, white]
        frame = [final_color] * self.num_leds
        return frame