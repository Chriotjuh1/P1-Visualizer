# P1-Visualizer/effects/christmas_snow.py

import random
from .base_effect import Effects
from .schemas import EffectModel, ChristmasSnowParams
from utils import rgb_to_rgbw

class ChristmasSnowEffect(Effects):
    """
    Een effect dat vallende sneeuwvlokken simuleert, met optionele rode en donkergroene lichten
    voor een kerstsfeer.
    """
    def __init__(self, model: EffectModel):
        # Attributen EERST definiëren
        self.bg_r, self.bg_g, self.bg_b = 0, 120, 0
        self.sparkle_brightness = 255
        self.fade_speed = 10
        self.star_density = 20 # Basisdichtheid
        self.led_states = []
        
        # DAARNA de superclass initialiseren
        super().__init__(model)

    def _on_num_leds_change(self):
        """Reset de status wanneer het aantal LEDs verandert."""
        self.led_states = [[[self.bg_r, self.bg_g, self.bg_b], 0] for _ in range(self.num_leds)]

    def handle_green_red(self, color, led_index):
        """Verwerkt het vervagen van lichten terug naar de achtergrondkleur."""
        r, g, b = color
        red = max(self.bg_r, r - self.fade_speed) if r > self.bg_r else min(self.bg_r, r + self.fade_speed)
        green = max(self.bg_g, g - self.fade_speed) if g > self.bg_g else min(self.bg_g, g + self.fade_speed)
        blue = max(self.bg_b, b - self.fade_speed) if b > self.bg_b else min(self.bg_b, b + self.fade_speed)
        
        self.led_states[led_index][0] = [red, green, blue]

        if abs(red - self.bg_r) < 10 and abs(green - self.bg_g) < 10 and abs(blue - self.bg_b) < 10:
            self.led_states[led_index] = [[self.bg_r, self.bg_g, self.bg_b], 0]
        return red, green, blue

    def get_next_frame(self, delta_time: float = 0.0):
        """
        Retourneert het volgende frame voor het Christmas Snow effect.
        """
        frame = []
        
        # SNELHEIDSBEREKENING MET SELF.SPEED:
        # De snelheid van de slider (1-5) beïnvloedt de kans op nieuwe vlokken.
        dynamic_star_density = self.star_density * (self.speed / 3.0) # Normaliseer rond de middensnelheid (3)

        for led_index in range(self.num_leds):
            color, light_type = self.led_states[led_index]

            if light_type == 0:
                red, green, blue = self.bg_r, self.bg_g, self.bg_b
            else:
                red, green, blue = self.handle_green_red(color, led_index)

            if self.led_states[led_index][1] == 0 and random.randint(0, 1000) < dynamic_star_density:
                faded_green = self.bg_g - random.randint(60, 120)
                red_color_state = [[self.sparkle_brightness, 0, 0], 1]
                dark_green_color_state = [[0, faded_green, 0], 2]
                white_color_state = [[self.sparkle_brightness, self.sparkle_brightness, self.sparkle_brightness], 3]
                
                white_chance = 100 - self.params.red_chance - self.params.dark_green_chance
                if white_chance < 0: white_chance = 0

                try:
                    self.led_states[led_index] = random.choices(
                        [red_color_state, dark_green_color_state, white_color_state],
                        weights=[self.params.red_chance, self.params.dark_green_chance, white_chance],
                    )[0]
                except ValueError:
                       self.led_states[led_index] = [[self.bg_r, self.bg_g, self.bg_b], 0]

            brightness_mod = self.params.brightness / 100.0
            adjusted_red = int(red * brightness_mod)
            adjusted_green = int(green * brightness_mod)
            adjusted_blue = int(blue * brightness_mod)
            
            frame.append(rgb_to_rgbw(adjusted_red, adjusted_green, adjusted_blue))
        return frame