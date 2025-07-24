# P1-Visualizer/effects/knight_rider.py
from .base_effect import Effects
from .converts import rgb_to_rgbw
from .schemas import KnightRiderParams


class KnightRiderEffect(Effects):
    params: KnightRiderParams
    fade_divider: int = 3
    position: int = 0
    moving_right: bool = True
    last_update: int = 0

    def get_next_frame(self):
        line_length = self.params.line_length # Gebruik line_length van params
        # Correctie: Toegang tot Color object attributen met '.'
        red = self.params.color[0].red
        green = self.params.color[0].green
        blue = self.params.color[0].blue

        frame = [[0, 0, 0, 0]] * self.num_leds
        brightness_factor = self.params.brightness / 100

        faded_r = int(red * brightness_factor)
        faded_g = int(green * brightness_factor)
        faded_b = int(blue * brightness_factor)
        red_out, green_out, blue_out, white_out = rgb_to_rgbw(faded_r, faded_g, faded_b)

        for line in range(line_length):
            led_pos = (self.position + line) % self.num_leds
            frame[led_pos] = [red_out, green_out, blue_out, white_out]

        fade_factor = 1
        fade_amount = line_length // self.fade_divider
        if fade_amount <= 0:
            fade_amount = 1

        for fade in range(1, fade_amount + 1):
            fade_factor = fade_factor * 0.8

            faded_r_extra = int(red * fade_factor * brightness_factor)
            faded_g_extra = int(green * fade_factor * brightness_factor)
            faded_b_extra = int(blue * fade_factor * brightness_factor)
            red_out, green_out, blue_out, white_out = rgb_to_rgbw(
                faded_r_extra, faded_g_extra, faded_b_extra
            )
            final_faded_color = [red_out, green_out, blue_out, white_out]

            prev_pos = self.position - fade
            if prev_pos >= 0:
                frame[prev_pos] = final_faded_color
            next_pos = self.position + line_length + fade - 1  # -1 to make it work
            if next_pos < self.num_leds:
                frame[next_pos] = final_faded_color

        if self.moving_right:
            if self.position + line_length >= self.num_leds:
                self.moving_right = False
                self.position = self.num_leds - line_length
            else:
                self.position += 1
        else:
            if self.position <= 0:
                self.moving_right = True
                self.position = 0
            else:
                self.position -= 1
        return frame
