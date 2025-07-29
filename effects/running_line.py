# P1-Visualizer/effects/running_line.py

from .base_effect import Effects
from .schemas import EffectModel, RunningLineParams
from utils import rgb_to_rgbw

class RunningLineEffect(Effects):
    """
    Een effect dat meerdere 'lopende lijnen' of strepen over de LED-strip simuleert.
    Deze versie is bijgewerkt om met delta_time te werken voor soepele animatie.
    """
    def __init__(self, model: EffectModel):
        super().__init__(model)
        if not isinstance(self.params, RunningLineParams):
            raise ValueError("Parameters for RunningLineEffect must be of type RunningLineParams")
        
        # current_frame wordt al geïnitialiseerd in de base class

    def get_next_frame(self, delta_time: float = 0.0):
        """
        Retourneert het volgende frame voor het Running Line effect.
        """
        line_width = self.params.line_width
        number_of_lines = self.params.number_of_lines

        bg_r, bg_g, bg_b = self.params.background_color.red, self.params.background_color.green, self.params.background_color.blue
        bg_rgbw = rgb_to_rgbw(bg_r, bg_g, bg_b)

        fg_r, fg_g, fg_b = self.params.color[0].red, self.params.color[0].green, self.params.color[0].blue
        brightness_factor = self.params.brightness / 100.0
        fg_rgbw = rgb_to_rgbw(
            int(fg_r * brightness_factor),
            int(fg_g * brightness_factor),
            int(fg_b * brightness_factor)
        )

        frame = [bg_rgbw] * self.num_leds

        # --- NIEUWE SNELHEIDSBEREKENING MET DELTA_TIME ---
        # De 'speed' (1-5 van de slider) wordt vermenigvuldigd met de verstreken tijd.
        # De vermenigvuldigingsfactor (bv. 100.0) bepaalt de basissnelheid.
        speed_multiplier = 100.0
        self.current_frame += self.speed * delta_time * speed_multiplier

        if number_of_lines > 0:
            spacing = self.num_leds / number_of_lines

            for i in range(number_of_lines):
                start_pos = int((self.current_frame + i * spacing)) % self.num_leds

                for width_offset in range(line_width):
                    idx = (start_pos + width_offset) % self.num_leds
                    if 0 <= idx < self.num_leds:
                        frame[idx] = fg_rgbw
        
        return frame