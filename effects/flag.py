# P1-Visualizer/effects/flag.py

from .base_effect import Effects
from .schemas import EffectModel, FlagParams
from utils import rgb_to_rgbw

class FlagEffect(Effects):
    """
    Een effect dat een vlag als één blok van links naar rechts over de strip laat lopen,
    vergelijkbaar met het 'Running Line' effect.
    """
    def __init__(self, model: EffectModel):
        super().__init__(model)
        if not isinstance(self.params, FlagParams):
            raise ValueError("Parameters for FlagEffect must be of type FlagParams")

        # current_frame wordt al geïnitialiseerd in de base class

    def get_next_frame(self, delta_time: float = 0.0):
        """
        Retourneert het volgende frame voor het Flag effect.
        """
        brightness_factor = self.params.brightness / 100.0
        
        bg_r, bg_g, bg_b = self.params.background_color.red, self.params.background_color.green, self.params.background_color.blue
        bg_rgbw = rgb_to_rgbw(bg_r, bg_g, bg_b)

        total_pattern_width = sum(self.params.width)
        if total_pattern_width == 0:
             return [bg_rgbw] * self.num_leds

        # --- NIEUWE SNELHEIDSBEREKENING ---
        # De vlag moet de hele strip + zijn eigen lengte afleggen om volledig uit beeld te verdwijnen.
        total_distance = self.num_leds + total_pattern_width
        speed_multiplier = 40.0
        self.current_frame = (self.current_frame + self.speed * delta_time * speed_multiplier) % total_distance

        # Maak een "kleurenkaart" van het vlagpatroon voor efficiëntie.
        pattern_map = []
        for i, width in enumerate(self.params.width):
            color_input = self.params.color[i]
            scaled_red = int(color_input.red * brightness_factor)
            scaled_green = int(color_input.green * brightness_factor) 
            scaled_blue = int(color_input.blue * brightness_factor)
            rgbw_color = rgb_to_rgbw(scaled_red, scaled_green, scaled_blue)
            pattern_map.extend([rgbw_color] * width)

        # Begin met een volledig lege (achtergrondkleur) strip.
        frame = [bg_rgbw] * self.num_leds

        # --- NIEUWE TEKENLOGICA ---
        # Bepaal de startpositie van de vlag. 
        # Door de breedte van het patroon eraf te halen, start de vlag buiten het beeld.
        start_pos = int(self.current_frame) - total_pattern_width

        # Teken alleen de pixels van de vlag die daadwerkelijk op de strip zichtbaar zijn.
        for i in range(total_pattern_width):
            led_index = start_pos + i
            # Controleer of de pixel binnen de strip valt (van 0 tot num_leds).
            if 0 <= led_index < self.num_leds:
                frame[led_index] = pattern_map[i]
        
        return frame