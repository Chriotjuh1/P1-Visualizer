# P1-Visualizer/effects/meteor.py
import random
import time
from .base_effect import Effects
from .schemas import MeteorParams
from .converts import rgb_to_rgbw

class MeteorEffect(Effects):
    params: MeteorParams
    meteor_position: float = 0.0
    sparks: list = []
    sparkle_brightness: int = 255

    def __init__(self, model):
        super().__init__(model)
        self.params = model.params
        self.num_leds = model.num_leds # Haal num_leds uit het model
        self.fps = model.fps # Haal fps uit het model
        self.last_frame_time = time.time()

        # Time accumulator voor frame-onafhankelijke animatie
        self.time_accumulator = 0.0
        self.frame_duration = 1.0 / self.fps if self.fps > 0 else 0.0

        # Initialiseer de interne staat van de meteor
        self._initialize_state()

    def _initialize_state(self):
        """
        Initialiseert of reset de interne staat van de meteor.
        Dit wordt aangeroepen bij __init__ en wanneer num_leds of fps verandert.
        """
        self.meteor_position = 0.0 # Reset meteor positie
        self.sparks = [] # Wis bestaande vonken

        # BELANGRIJK: Zorg ervoor dat frame_buffer de juiste grootte heeft
        self.frame_buffer = [[0, 0, 0, 0] for _ in range(self.num_leds)]
        
        # Zorg ervoor dat frame_duration correct is bij herinitialisatie
        self.frame_duration = 1.0 / self.fps if self.fps > 0 else 0.0
        self.time_accumulator = 0.0 # Reset time accumulator

    def get_next_frame(self) -> list[list[int]]:
        # BELANGRIJK: Controleer of num_leds of fps is gewijzigd en initialiseer/update indien nodig
        # Dit is de cruciale controle die de IndexError voorkomt.
        if len(self.frame_buffer) != self.num_leds or self.fps != self.model.fps:
            self.num_leds = self.model.num_leds # Update num_leds van het model
            self.fps = self.model.fps # Update fps van het model
            self._initialize_state() # Roep de initialisatiemethode aan

        current_time = time.time()
        delta_time = current_time - self.last_frame_time
        self.last_frame_time = current_time

        self.time_accumulator += delta_time

        # Update de interne staat van de meteor alleen als er genoeg tijd is verstreken
        # Dit zorgt voor frame-onafhankelijke beweging
        while self.time_accumulator >= self.frame_duration:
            # Beweeg meteor kop met 1 logische stap per frame
            self.meteor_position = (self.meteor_position + 1) % self.num_leds

            # Genereer vonken (als spark_intensity is ingesteld)
            if self.params.spark_intensity > 0:
                # Hoe groter spark_intensity, hoe groter de kans op een vonk
                if random.randint(0, 100) < self.params.spark_intensity:
                    spark_pos = random.randint(0, self.num_leds - 1)
                    spark_color_rgb = (self.params.color[0].red, self.params.color[0].green, self.params.color[0].blue)
                    spark_color_rgbw = rgb_to_rgbw(spark_color_rgb[0], spark_color_rgb[1], spark_color_rgb[2])
                    self.sparks.append([spark_pos, list(spark_color_rgbw), self.sparkle_brightness])
            
            # Vervaag vonken (dit gebeurt nu ook per logische frame)
            new_sparks = []
            for spark_data in self.sparks:
                s_pos, s_color_rgbw, s_intensity = spark_data
                fade_amount = 20 # Hoe snel vonken vervagen (kan een parameter worden)
                s_intensity = max(0, s_intensity - fade_amount)
                if s_intensity > 0:
                    new_sparks.append([s_pos, s_color_rgbw, s_intensity])
            self.sparks = new_sparks

            self.time_accumulator -= self.frame_duration

        # Begin met een leeg (zwart) frame voor de huidige iteratie
        # BELANGRIJK: Initialiseer 'frame' hier altijd met de juiste grootte
        frame = [[0, 0, 0, 0] for _ in range(self.num_leds)]

        # Teken meteor spoor op basis van de huidige (mogelijk geüpdatete) positie
        for i in range(self.params.meteor_width):
            # Bereken de index van de huidige LED in het spoor
            idx = (int(self.meteor_position) - i + self.num_leds) % self.num_leds
            
            # Zorg ervoor dat de index binnen de geldige grenzen valt
            if 0 <= idx < self.num_leds:
                brightness_factor = (self.params.meteor_width - i) / self.params.meteor_width
                r, g, b = self.params.color[0].red, self.params.color[0].green, self.params.color[0].blue
                adjusted_r = int(r * brightness_factor)
                adjusted_g = int(g * brightness_factor)
                adjusted_b = int(b * brightness_factor)
                rgbw = rgb_to_rgbw(adjusted_r, adjusted_g, adjusted_b)
                
                for k in range(4): # Iterate through R, G, B, W components
                    frame[idx][k] = max(rgbw[k], frame[idx][k])

        # Teken vonken op het frame (op basis van hun huidige intensiteit)
        for spark_data in self.sparks:
            s_pos, s_color_rgbw, s_intensity = spark_data
            if 0 <= s_pos < self.num_leds:
                intensity_factor = s_intensity / self.sparkle_brightness
                adjusted_spark_color = [int(c * intensity_factor) for c in s_color_rgbw]
                for k in range(4):
                    frame[s_pos][k] = max(frame[s_pos][k], adjusted_spark_color[k])


        # Pas de algemene helderheid van de parameters toe op het hele frame
        brightness_mod = self.params.brightness / 100
        final_frame = []
        for rgbw_color in frame:
            r, g, b, w = rgbw_color
            adjusted_r = int(r * brightness_mod)
            adjusted_g = int(g * brightness_mod)
            adjusted_b = int(b * brightness_mod)
            adjusted_w = int(w * brightness_mod) # Pas ook toe op wit component
            final_frame.append([adjusted_r, adjusted_g, adjusted_b, adjusted_w])

        return final_frame
