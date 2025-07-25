# P1-Visualizer/effects/christmas_snow.py

import random
from .base_effect import Effects
from .schemas import EffectModel, ChristmasSnowParams
from .converts import rgb_to_rgbw

class ChristmasSnowEffect(Effects):
    """
    Een effect dat vallende sneeuwvlokken simuleert, met optionele rode en donkergroene lichten
    voor een kerstsfeer.
    """
    def __init__(self, model: EffectModel):
        super().__init__(model)
        # Type checking for parameters
        if not isinstance(self.params, ChristmasSnowParams):
            raise ValueError("Parameters for ChristmasSnowEffect must be of type ChristmasSnowParams")

        self.bg_r, self.bg_g, self.bg_b = 0, 120, 0 # Basis donkergroene achtergrond
        self.sparkle_brightness = 255 # Maximale helderheid voor sneeuwvlokken
        self.fade_speed = 10 # Snelheid waarmee sneeuwvlokken vervagen
        self.star_density = 20 # Kans op een nieuwe sneeuwvlok (lager = minder)
        self.led_states = [] # [ [r, g, b], type ] voor elke LED
        self.current_frame = 0.0 # Initialiseer current_frame als float voor nauwkeurigere animatie

        self._on_num_leds_change() # Roep deze aan om de initiële LED-statussen in te stellen

    def _on_num_leds_change(self):
        """Reset de status wanneer het aantal LEDs verandert."""
        # Initialiseer alle LED's naar de achtergrondkleur en type 0 (geen actieve sneeuwvlok)
        self.led_states = [[[self.bg_r, self.bg_g, self.bg_b], 0] for _ in range(self.num_leds)]

    def handle_green_red(self, color, led_index):
        """
        Verwerkt het vervagen van rode en donkergroene lichten terug naar de achtergrondkleur.
        """
        r, g, b = color
        # Vervaag kleuren geleidelijk terug naar de achtergrondkleur
        red = max(self.bg_r, r - self.fade_speed) if r > self.bg_r else min(self.bg_r, r + self.fade_speed)
        green = max(self.bg_g, g - self.fade_speed) if g > self.bg_g else min(self.bg_g, g + self.fade_speed)
        blue = max(self.bg_b, b - self.fade_speed) if b > self.bg_b else min(self.bg_b, b + self.fade_speed)
        
        self.led_states[led_index][0] = [red, green, blue] # Update de kleur in de staat

        # Als de kleur dicht genoeg bij de achtergrond is, reset dan de staat
        if abs(red - self.bg_r) < 10 and abs(green - self.bg_g) < 10 and abs(blue - self.bg_b) < 10:
            self.led_states[led_index] = [[self.bg_r, self.bg_g, self.bg_b], 0]
        return red, green, blue

    def get_next_frame(self):
        """
        Retourneert het volgende frame voor het Christmas Snow effect.
        """
        frame = []
        
        # Update de frame teller
        # Dit zorgt voor de animatie van de sneeuwval
        self.current_frame += (self.fps / 33.0) * 1.0 # Pas de snelheid aan op basis van FPS

        for led_index in range(self.num_leds):
            color, light_type = self.led_states[led_index]

            if light_type == 0: # Als het een 'lege' (achtergrond) LED is
                red, green, blue = self.bg_r, self.bg_g, self.bg_b
            else: # Als het een actieve sneeuwvlok of kerstlicht is
                red, green, blue = self.handle_green_red(color, led_index)

            # Nieuwe sneeuwvlokken genereren
            # De kans is gebaseerd op star_density en de huidige frame
            if self.led_states[led_index][1] == 0 and random.randint(0, 100) < self.star_density:
                # Bepaal de kleuren voor de verschillende soorten lichten
                # Faded green voor de achtergrond, rode en witte lichten voor kerst
                faded_green = self.bg_g - random.randint(60, 120) # Maak donkergroen iets donkerder
                red_color_state = [[self.sparkle_brightness, 0, 0], 1]
                dark_green_color_state = [[0, faded_green, 0], 2]
                white_color_state = [[self.sparkle_brightness, self.sparkle_brightness, self.sparkle_brightness], 3]
                
                # Bereken de kans voor wit, zodat de som van de kansen 100 is
                white_chance = 100 - self.params.red_chance - self.params.dark_green_chance
                if white_chance < 0: white_chance = 0 # Zorg voor een niet-negatieve kans

                try:
                    # Kies willekeurig een kleur op basis van de ingestelde kansen
                    self.led_states[led_index] = random.choices(
                        [red_color_state, dark_green_color_state, white_color_state],
                        weights=[self.params.red_chance, self.params.dark_green_chance, white_chance],
                    )[0]
                except ValueError: # Vang de fout op als alle gewichten nul zijn
                       self.led_states[led_index] = [[self.bg_r, self.bg_g, self.bg_b], 0] # Val terug op achtergrond

            # Pas de globale helderheid toe
            brightness_mod = self.params.brightness / 100.0
            adjusted_red = int(red * brightness_mod)
            adjusted_green = int(green * brightness_mod)
            adjusted_blue = int(blue * brightness_mod)
            
            # Converteer naar RGBW en voeg toe aan het frame
            r, g, b, w = rgb_to_rgbw(adjusted_red, adjusted_green, adjusted_blue)
            frame.append([r, g, b, w])
        return frame
