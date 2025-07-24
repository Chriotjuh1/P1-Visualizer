# P1-Visualizer/effects/running_line.py
from .converts import rgb_to_rgbw
from .base_effect import Effects
from .schemas import RunningLineParams


class RunningLineEffect(Effects):
    params: RunningLineParams
    pos: int = 0

    def get_next_frame(self):
        line_width = self.params.line_width
        background = self.params.background_color
        gap = self.num_leds // self.params.number_of_lines
        # Correctie: Toegang tot Color object attributen met '.'
        bg_r = background.red
        bg_g = background.green
        bg_b = background.blue

        foreground = self.params.color[0]
        # Correctie: Toegang tot Color object attributen met '.'
        foreground_r = foreground.red
        foreground_g = foreground.green
        foreground_b = foreground.blue

        bg_r, bg_g, bg_b, bg_w = rgb_to_rgbw(bg_r, bg_g, bg_b)

        foreground_r, foreground_g, foreground_b, foreground_w = rgb_to_rgbw(
            foreground_r, foreground_g, foreground_b
        )

        frame = [[bg_r, bg_g, bg_b, bg_w]] * self.num_leds
        for i in range(self.params.number_of_lines):
            current_gap = gap * i
            for width in range(line_width):
                idx = (self.pos + current_gap + width) % self.num_leds
                frame[idx] = [foreground_r, foreground_g, foreground_b, foreground_w]
        self.pos += 1
        if self.pos >= self.num_leds:
            self.pos = 0
        return frame
