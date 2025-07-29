from .base_effect import Effects
from .schemas import StaticParams
from utils import rgb_to_rgbw

class StaticEffect(Effects):
    def __init__(self, model):
        super().__init__(model)
        self.params: StaticParams = self.params

    def get_next_frame(self, delta_time: float):
        """
        Retourneert een statische kleur. delta_time wordt genegeerd.
        """
        brightness = self.params.brightness / 100.0
        r, g, b = self.params.color[0].red, self.params.color[0].green, self.params.color[0].blue
        
        r_out = int(r * brightness)
        g_out = int(g * brightness)
        b_out = int(b * brightness)
        
        return [rgb_to_rgbw(r_out, g_out, b_out)] * self.num_leds
