# P1-Visualizer/effects/flag.py
from .base_effect import Effects
from .schemas import FlagParams
from .converts import rgb_to_rgbw


class FlagEffect(Effects):
    params: FlagParams
    position: int = 0

    def get_next_frame(self):
        brightness_factor = self.params.brightness / 100
        background = self.params.background_color
        color = self.params.color
        width = self.params.width

        # Correctie: Toegang tot Color object attributen met '.'
        bg_red = background.red * brightness_factor
        bg_green = background.green * brightness_factor
        bg_blue = background.blue * brightness_factor

        bg_red, bg_green, bg_blue, bg_white = rgb_to_rgbw(bg_red, bg_green, bg_blue)

        frame = [[bg_red, bg_green, bg_blue, bg_white]] * self.num_leds

        current_segment_start = self.position

        for idx, color_input in enumerate(color):
            flag_width = width[idx]
            # Correctie: Toegang tot Color object attributen met '.'
            scaled_red = color_input.red * brightness_factor
            scaled_green = color_input.green * brightness_factor
            scaled_blue = color_input.blue * brightness_factor

            red, green, blue, white = rgb_to_rgbw(scaled_red, scaled_green, scaled_blue)
            rgbw = [red, green, blue, white]

            for led_offset in range(flag_width):
                index = (current_segment_start + led_offset) % self.num_leds
                frame[index] = rgbw
            current_segment_start = (current_segment_start + flag_width) % self.num_leds

        self.position = (self.position + 1) % self.num_leds
        return frame