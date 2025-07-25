# P1-Visualizer/effects/flag.py

from .base_effect import Effects
from .schemas import EffectModel, FlagParams
from .converts import rgb_to_rgbw

class FlagEffect(Effects):
    """
    Een effect dat een bewegende vlag simuleert met meerdere kleurensegmenten.
    """
    def __init__(self, model: EffectModel):
        super().__init__(model)
        # Type checking for parameters
        if not isinstance(self.params, FlagParams):
            raise ValueError("Parameters for FlagEffect must be of type FlagParams")

        self.current_frame = 0.0 # Initialiseer current_frame als float voor nauwkeurigere animatie

    def get_next_frame(self):
        """
        Retourneert het volgende frame voor het Flag effect.
        """
        frame = [[0, 0, 0, 0]] * self.num_leds # Begin met een leeg (zwart) frame

        brightness_factor = self.params.brightness / 100.0
        
        # Achtergrondkleur
        bg_r = self.params.background_color.red
        bg_g = self.params.background_color.green
        bg_b = self.params.background_color.blue
        bg_rgbw = rgb_to_rgbw(bg_r, bg_g, bg_b)

        # Update de frame teller
        # De snelheid van de vlagbeweging kan worden aangepast door de factor 0.5 te wijzigen
        # of door een snelheidsparameter toe te voegen aan FlagParams.
        self.current_frame += (self.fps / 33.0) * 0.5 # Pas de snelheid aan op basis van FPS

        # Bereken de totale breedte van het vlagpatroon
        total_pattern_width = sum(self.params.width)

        # Vul het frame met de achtergrondkleur
        frame = [bg_rgbw] * self.num_leds

        # Teken de vlagsegmenten
        current_segment_offset = 0
        for idx, color_input in enumerate(self.params.color):
            flag_width = self.params.width[idx]

            scaled_red = int(color_input.red * brightness_factor)
            scaled_green = int(color_input.green * brightness_factor) 
            scaled_blue = int(color_input.blue * brightness_factor)
            rgbw = rgb_to_rgbw(scaled_red, scaled_green, scaled_blue)
            
            for led_offset in range(flag_width):
                # Bereken de positie in het totale vlagpatroon
                pos_in_pattern = (current_segment_offset + led_offset)

                # Bereken de uiteindelijke LED-index op de strip, rekening houdend met de animatie
                # en de herhaling van het patroon.
                # De vlag beweegt over de strip, dus we gebruiken self.current_frame voor de offset.
                led_index = int((pos_in_pattern + self.current_frame) % self.num_leds)
                
                if 0 <= led_index < self.num_leds:
                    frame[led_index] = rgbw
            
            current_segment_offset += flag_width
        
        return frame
