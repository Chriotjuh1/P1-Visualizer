# P1-Visualizer/effects/christmas_snow.py
import random
import time # Importeer time voor last_frame_time
from .base_effect import Effects
from .schemas import ChristmasSnowParams
from .converts import rgb_to_rgbw


class ChristmasSnowEffect(Effects):
    params: ChristmasSnowParams
    star_density: int = 20
    fade_speed: int = 10
    sparkle_brightness: int = 255
    bg_r: int = 0
    bg_g: int = 120
    bg_b: int = 0
    led_states: list[list[int] | int] = [] # Deze type hint is niet helemaal correct voor de inhoud, maar functioneel

    def __init__(self, model):
        super().__init__(model)
        # Initialiseer de parameters van het effect op basis van het model
        self.params = model.params
        self.num_leds = model.num_leds
        self.fps = model.fps
        self.fade_speed = 10 # Hoe snel een vonk vervaagt
        # Achtergrondkleur (donkergroen, geen wit component in RGBW)
        self.bg_r = 0
        self.bg_g = 120
        self.bg_b = 0
        self.sparkle_brightness = 255 # Helderheid van de vonken
        self.star_density = self.params.red_chance + self.params.dark_green_chance # Gebruik density van params

        self.last_frame_time = time.time()
        self.led_states = [] # Lijst om (kleur, type) voor elke LED bij te houden
        self._initialize_led_states() # Initialiseer de LED-toestanden bij de start

    def _initialize_led_states(self):
        """
        Initialiseert of reset de interne staat van de LED's.
        Elke LED krijgt een starttoestand: [RGB-kleur, type].
        Type 0: achtergrondkleur (uitgegaan of vervaagd)
        Type 1: rood vonk
        Type 2: groen vonk
        Type 3: wit vonk
        """
        self.led_states = []
        for _ in range(self.num_leds):
            self.led_states.append([[self.bg_r, self.bg_g, self.bg_b], 0]) # Initialiseer alle LED's als achtergrondkleur

    def handle_green_red(self, color, led):
        """
        Verwerkt het vervagen van rode/groene/witte vonken terug naar de achtergrondkleur.
        """
        r, g, b = color

        # Vervaag rood
        red = (
            max(self.bg_r, r - self.fade_speed)
            if r > self.bg_r
            else min(self.bg_r, r + self.fade_speed)
        )
        # Vervaag groen
        green = (
            max(self.bg_g, g - self.fade_speed)
            if g > self.bg_g
            else min(self.bg_g, g + self.fade_speed)
        )
        # Vervaag blauw
        blue = (
            max(self.bg_b, b - self.fade_speed)
            if b > self.bg_b
            else min(self.bg_b, b + self.fade_speed)
        )

        self.led_states[led][0] = [red, green, blue] # Update de kleur van de LED

        # Als de kleur dicht genoeg bij de achtergrondkleur is, reset dan naar achtergrondtype
        if (
            abs(red - self.bg_r) < self.fade_speed
            and abs(green - self.bg_g) < self.fade_speed
            and abs(blue - self.bg_b) < self.fade_speed
        ):
            self.led_states[led] = [[self.bg_r, self.bg_g, self.bg_b], 0] # Reset naar achtergrondtoestand
        return red, green, blue

    def get_next_frame(self):
        # Controleer of het aantal LED's is gewijzigd en initialiseer opnieuw indien nodig
        if len(self.led_states) != self.num_leds:
            self._initialize_led_states()

        frame = []

        # Update de star_density van de parameters
        self.star_density = self.params.red_chance + self.params.dark_green_chance

        for led in range(self.num_leds):
            color, type = self.led_states[led] # Haal de huidige kleur en type van de LED op
            
            # Bepaal de basiskleur voor de huidige LED
            if type == 0: # Achtergrondkleur
                red, green, blue = self.bg_r, self.bg_g, self.bg_b
            else: # Vonk die vervaagt
                red, green, blue = self.handle_green_red(color, led)

            # Als de LED in achtergrondtoestand is (type 0) en een willekeurige kans treedt op,
            # initialiseer dan een nieuwe vonk.
            if self.led_states[led][1] == 0 and random.randint(0, 100) < self.star_density:
                faded_green = self.bg_g - random.randint(60, 120) # Maak een donkerdere groene tint voor groene vonk

                # Definieer de mogelijke vonkkleuren met hun types
                red_color = [[self.sparkle_brightness, 0, 0], 1]
                green_color = [[0, faded_green, 0], 2]
                white_color = [
                    [self.sparkle_brightness, self.sparkle_brightness, self.sparkle_brightness],
                    3,
                ]
                
                # Bereken de kans voor witte vonken
                # Zorg ervoor dat de som van kansen niet meer dan 100 is
                white_chance = max(0, 100 - self.params.red_chance - self.params.dark_green_chance)

                # Kies willekeurig een vonkkleur op basis van de ingestelde kansen
                self.led_states[led] = random.choices(
                    [red_color, green_color, white_color],
                    weights=[self.params.red_chance, self.params.dark_green_chance, white_chance],
                )[0]
                # Update de huidige kleur en type van de LED naar de zojuist gekozen vonk
                red, green, blue = self.led_states[led][0]
                type = self.led_states[led][1]

            # Pas de helderheid van het effect toe
            brightness_mod = self.params.brightness / 100
            adjusted_red = int(red * brightness_mod)
            adjusted_green = int(green * brightness_mod)
            adjusted_blue = int(blue * brightness_mod)

            # Converteer de RGB-kleur naar RGBW en voeg toe aan het frame
            red, green, blue, white = rgb_to_rgbw(adjusted_red, adjusted_green, adjusted_blue)
            frame.append([red, green, blue, white])
        return frame

