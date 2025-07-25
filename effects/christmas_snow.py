# P1-Visualizer/effects/christmas_snow.py
import random
import time # Importeer time voor last_frame_time
from .base_effect import Effects
from .schemas import ChristmasSnowParams
from .converts import rgb_to_rgbw


class ChristmasSnowEffect(Effects):
    params: ChristmasSnowParams
    star_density: int = 20
    fade_speed: int = 30 # Verhoogde fade snelheid voor snellere vervaging
    sparkle_brightness: int = 255
    bg_r: int = 0
    bg_g: int = 30 # Donkerdere groene achtergrond voor een kerstsfeer
    bg_b: int = 0
    led_states: list[list[int] | int] = [] # Lijst om (kleur, type) voor elke LED bij te houden

    def __init__(self, model):
        super().__init__(model)
        # Initialiseer de parameters van het effect op basis van het model
        self.params = model.params
        self.num_leds = model.num_leds
        self.fps = model.fps
        self.fade_speed = 30 # Consistent met de klasse variabele
        # Achtergrondkleur (donkergroen, geen wit component in RGBW)
        self.bg_r = 0
        self.bg_g = 30 # Consistent met de klasse variabele
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
        Verwerkt het vervagen van vonken terug naar de achtergrondkleur.
        Zorgt ervoor dat kleuren correct vervagen naar de achtergrond.
        """
        r, g, b = color
        
        # Bereken de stapgrootte voor vervaging gebaseerd op fade_speed
        # Dit zorgt ervoor dat elke component naar zijn achtergrondwaarde beweegt.
        # Voorkom delen door nul
        red_step = (r - self.bg_r) / self.fade_speed if self.fade_speed > 0 else 0
        green_step = (g - self.bg_g) / self.fade_speed if self.fade_speed > 0 else 0
        blue_step = (b - self.bg_b) / self.fade_speed if self.fade_speed > 0 else 0

        # Pas de stap toe
        red = int(r - red_step)
        green = int(g - green_step)
        blue = int(b - blue_step)

        # Zorg ervoor dat de kleuren niet voorbij de achtergrondwaarde gaan
        red = max(self.bg_r, red) if r > self.bg_r else min(self.bg_r, red)
        green = max(self.bg_g, green) if g > self.bg_g else min(self.bg_g, green)
        blue = max(self.bg_b, blue) if b > self.bg_b else min(self.bg_b, blue)

        self.led_states[led][0] = [red, green, blue] # Update de kleur van de LED

        # Als de kleur dicht genoeg bij de achtergrondkleur is, reset dan naar achtergrondtype
        # Gebruik een kleine drempel om floating point afrondingsfouten te voorkomen
        if (
            abs(red - self.bg_r) < 10 # Gebruik een kleine drempel (aangepast van 5 naar 10)
            and abs(green - self.bg_g) < 10
            and abs(blue - self.bg_b) < 10
        ):
            self.led_states[led] = [[self.bg_r, self.bg_g, self.bg_b], 0] # Reset naar achtergrondtoestand
        return red, green, blue

    def get_next_frame(self):
        # Controleer of het aantal LED's is gewijzigd en initialiseer opnieuw indien nodig
        if len(self.led_states) != self.num_leds:
            self._initialize_led_states()

        frame = []

        # Update de star_density van de parameters
        # De som van red_chance en dark_green_chance bepaalt de totale dichtheid van nieuwe vonken.
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
                # Definieer de mogelijke vonkkleuren met hun types
                red_color = [[self.sparkle_brightness, 0, 0], 1] # Helder rood
                bright_green_sparkle = [0, self.sparkle_brightness, 0] # Helder groen
                green_color = [bright_green_sparkle, 2] # Gebruik helder groen
                white_color = [
                    [self.sparkle_brightness, self.sparkle_brightness, self.sparkle_brightness],
                    3, # Type 3 voor witte vonk
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
