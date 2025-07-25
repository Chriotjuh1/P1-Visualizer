# P1-Visualizer/effects/breathing.py

import math
from .base_effect import Effects
from .schemas import EffectModel, BreathingParams
from .converts import rgb_to_rgbw

class BreathingEffect(Effects):
    """
    Een effect dat de helderheid van de LED's geleidelijk laat pulseren,
    simulerend een 'ademend' effect.
    """
    def __init__(self, model: EffectModel):
        super().__init__(model)
        # Type checking for parameters
        if not isinstance(self.params, BreathingParams):
            raise ValueError("Parameters for BreathingEffect must be of type BreathingParams")

        self.current_frame = 0.0 # Initialiseer current_frame als float voor nauwkeurigere animatie
        self.current_breathing_factor = 0.0
        self.rising = True

    def get_next_frame(self):
        """
        Retourneert het volgende frame voor het Breathing effect.
        De helderheid pulseert met een sinusgolf.
        """
        brightness = self.params.brightness / 100.0

        # Update de frame teller
        # De snelheid van de puls kan worden aangepast door de factor 0.05 te wijzigen
        # of door een snelheidsparameter toe te voegen aan BreathingParams.
        # Gebruik self.fps om de animatie consistent te maken over verschillende FPS instellingen
        self.current_frame += (self.fps / 33.0) * 1.0 # Pas de snelheid aan op basis van FPS

        # Gebruik een sinusfunctie voor een vloeiende ademhaling
        # De periode van de sinusgolf kan worden aangepast (bijv. door 0.05 te wijzigen)
        # De output van sin() is tussen -1 en 1, dus we schalen het naar 0-1
        normalized_factor = (math.sin(self.current_frame * 0.05) + 1) / 2.0

        r_base, g_base, b_base = self.params.color[0].red, self.params.color[0].green, self.params.color[0].blue
        
        # Pas de helderheid toe
        red = int(r_base * normalized_factor * brightness)
        green = int(g_base * normalized_factor * brightness)
        blue = int(b_base * normalized_factor * brightness)

        # Zorg ervoor dat de kleuren binnen het 0-255 bereik blijven
        red = max(0, min(255, red))
        green = max(0, min(255, green))
        blue = max(0, min(255, blue))

        # Converteer naar RGBW indien nodig en retourneer het frame
        return [rgb_to_rgbw(red, green, blue)] * self.num_leds
