import math
from .effects import Effects
from .schemas import BreathingParams
# --- CORRECTIE HIER: Importeer nu vanuit utils ---
from utils import rgb_to_rgbw 

class BreathingEffect(Effects):
    def __init__(self, model):
        super().__init__(model)
        self.params: BreathingParams = self.params
        self.phase = 0.0

    def get_next_frame(self, delta_time: float):
        # ... (de rest van de functie blijft hetzelfde)
        speed_factor = 2 * math.pi / (6 - self.speed)
        self.phase = (self.phase + delta_time * speed_factor) % (2 * math.pi)
        breath_factor = (math.sin(self.phase) + 1) / 2.0
        brightness = self.params.brightness / 100.0
        r, g, b = self.params.color[0].red, self.params.color[0].green, self.params.color[0].blue
        r_out = int(r * breath_factor * brightness)
        g_out = int(g * breath_factor * brightness)
        b_out = int(b * breath_factor * brightness)
        return [rgb_to_rgbw(r_out, g_out, b_out)] * self.num_leds
