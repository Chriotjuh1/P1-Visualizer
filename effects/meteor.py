# P1-Visualizer/effects/meteor.py

import random
from .base_effect import Effects
from .schemas import EffectModel, MeteorParams
from .converts import rgb_to_rgbw

class MeteorEffect(Effects):
    """
    Een effect dat een "meteoor" simuleert die over de LED-strip beweegt,
    met een vervagende staart en optionele vonken.
    """
    def __init__(self, model: EffectModel):
        super().__init__(model)
        # Type checking for parameters
        if not isinstance(self.params, MeteorParams):
            raise ValueError("Parameters for MeteorEffect must be of type MeteorParams")

        self.max_sparkle_duration = 100 # Maximale levensduur van een vonk
        self.current_frame = 0.0 # Initialiseer current_frame als float voor nauwkeurigere animatie
        self._on_num_leds_change() # Roep deze aan om de initiële positie en vonken in te stellen

    def _on_num_leds_change(self):
        """Reset de status wanneer het aantal LEDs verandert."""
        # Start de meteoor aan het einde van de strip
        self.position = float(self.num_leds - 1)
        self.sparkles = {} # {led_index: remaining_duration}

    def get_next_frame(self):
        """
        Retourneert het volgende frame voor het Meteor effect.
        """
        # --- State Update Logic (throttled by speed/fps) ---
        
        # De visualizer's timer draait op ~33 FPS (30ms).
        # self.fps is de doelsnelheid van de slider (bijv. 6 tot 150).
        # Bereken hoeveel stappen de animatie deze frame moet vooruitgaan.
        advance_steps = self.fps / 33.0
        self.current_frame += advance_steps

        if self.current_frame >= 1.0:
            steps_to_take = int(self.current_frame)
            self.current_frame -= steps_to_take
            
            for _ in range(steps_to_take):
                self.position -= 1 # Beweeg de meteoor één stap naar links

                # Reset logica: reset als de meteoor + staart volledig van het scherm is
                if self.position + self.params.meteor_width < -self.max_sparkle_duration:
                    self.position = float(self.num_leds - 1)
                    self.sparkles.clear() # Wis alle vonken bij reset

                # Sparkle creatie
                # Een vonk verschijnt aan het einde van de meteoor
                sparkle_index = int(self.position) + self.params.meteor_width
                if 0 <= sparkle_index < self.num_leds:
                    if random.randint(0, 100) < self.params.spark_intensity:
                        self.sparkles[sparkle_index] = self.max_sparkle_duration # Geef de vonk een volledige levensduur

        # --- Drawing Logic (elke frame) ---
        frame = [[0, 0, 0, 0]] * self.num_leds # Start met een leeg (zwart) frame
        brightness_factor = self.params.brightness / 100.0
        r_base = self.params.color[0].red
        g_base = self.params.color[0].green
        b_base = self.params.color[0].blue

        # Teken de meteoor (hoofdgedeelte)
        for i in range(self.params.meteor_width):
            led_index = int(self.position) + i
            if 0 <= led_index < self.num_leds:
                r = int(r_base * brightness_factor)
                g = int(g_base * brightness_factor)
                b = int(b_base * brightness_factor)
                frame[led_index] = rgb_to_rgbw(r, g, b)

        # Teken en fade vonken
        keys_to_delete = []
        for key, value in list(self.sparkles.items()): # Gebruik list() om RuntimeError te voorkomen bij wijzigen tijdens iteratie
            value -= 2 # Fade elke frame (snelheid van vervagen)
            if value <= 0:
                keys_to_delete.append(key)
                continue
            
            sparkle_brightness = value / self.max_sparkle_duration
            sparkle_color_factor = brightness_factor * sparkle_brightness
            
            r = int(r_base * sparkle_color_factor)
            g = int(g_base * sparkle_color_factor)
            b = int(b_base * sparkle_color_factor)
            
            # Zorg ervoor dat de vonk geen helderder deel van de meteoor overschrijft
            if 0 <= key < self.num_leds and (frame[key][0] < r or sum(frame[key][:3]) == 0):
                frame[key] = rgb_to_rgbw(r, g, b)

            self.sparkles[key] = value # Update de resterende levensduur

        # Verwijder vonken die volledig zijn vervaagd
        for key in keys_to_delete:
            if key in self.sparkles:
                del self.sparkles[key]

        return frame
