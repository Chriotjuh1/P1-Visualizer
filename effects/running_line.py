# P1-Visualizer/effects/running_line.py

from .base_effect import Effects
from .schemas import EffectModel, RunningLineParams
from .converts import rgb_to_rgbw

class RunningLineEffect(Effects):
    """
    Een effect dat meerdere 'lopende lijnen' of strepen over de LED-strip simuleert.
    """
    def __init__(self, model: EffectModel):
        super().__init__(model)
        # Type checking for parameters
        if not isinstance(self.params, RunningLineParams):
            raise ValueError("Parameters for RunningLineEffect must be of type RunningLineParams")

        self.current_frame = 0.0 # Initialiseer current_frame als float voor nauwkeurigere animatie

    def get_next_frame(self):
        """
        Retourneert het volgende frame voor het Running Line effect.
        """
        line_width = self.params.line_width
        number_of_lines = self.params.number_of_lines

        # Achtergrondkleur
        bg_r = self.params.background_color.red
        bg_g = self.params.background_color.green
        bg_b = self.params.background_color.blue
        bg_rgbw = rgb_to_rgbw(bg_r, bg_g, bg_b)

        # Voorgrondkleur (van de lopende lijn)
        fg_r = self.params.color[0].red
        fg_g = self.params.color[0].green
        fg_b = self.params.color[0].blue
        brightness_factor = self.params.brightness / 100.0
        fg_rgbw = rgb_to_rgbw(
            int(fg_r * brightness_factor),
            int(fg_g * brightness_factor),
            int(fg_b * brightness_factor)
        )

        frame = [bg_rgbw] * self.num_leds # Begin met een frame vol achtergrondkleur

        # Update de frame teller
        # De snelheid van de lijnen kan worden aangepast door de factor 0.5 te wijzigen
        # of door een snelheidsparameter toe te voegen aan RunningLineParams.
        self.current_frame += (self.fps / 33.0) * 0.5 # Pas de snelheid aan op basis van FPS

        if number_of_lines > 0:
            # Bereken de afstand tussen de startpunten van de lijnen
            spacing = self.num_leds / number_of_lines if number_of_lines > 0 else self.num_leds

            for i in range(number_of_lines):
                # Bereken de startpositie van de huidige lijn, rekening houdend met de animatie
                # en de spacing tussen de lijnen.
                start_pos = int((self.current_frame + i * spacing)) % self.num_leds

                # Teken de lijn
                for width_offset in range(line_width):
                    idx = (start_pos + width_offset) % self.num_leds
                    if 0 <= idx < self.num_leds: # Dubbele controle voor de zekerheid
                        frame[idx] = fg_rgbw
        
        return frame
