# P1-Visualizer/effects/knight_rider.py

from .base_effect import Effects
from .schemas import EffectModel, KnightRiderParams
from .converts import rgb_to_rgbw

class KnightRiderEffect(Effects):
    """
    Een effect dat een heen en weer bewegende lijn simuleert, zoals in Knight Rider.
    """
    def __init__(self, model: EffectModel):
        super().__init__(model)
        # Type checking for parameters
        if not isinstance(self.params, KnightRiderParams):
            raise ValueError("Parameters for KnightRiderEffect must be of type KnightRiderParams")

        self.position = 0
        self.moving_right = True
        self.fade_divider = 3 # Hoe sneller de staart vervaagt
        self.current_frame = 0.0 # Initialiseer current_frame als float voor nauwkeurigere animatie

    def get_next_frame(self):
        """
        Retourneert het volgende frame voor het Knight Rider effect.
        """
        line_length = self.params.line_length
        r_base, g_base, b_base = self.params.color[0].red, self.params.color[0].green, self.params.color[0].blue
        brightness_factor = self.params.brightness / 100.0
        
        frame = [[0, 0, 0, 0]] * self.num_leds

        # De visualizer's timer draait op ~33 FPS (30ms).
        # self.fps is de doelsnelheid van de slider (bijv. 6 tot 150).
        # Bereken hoeveel stappen de animatie deze frame moet vooruitgaan.
        advance_steps = self.fps / 33.0
        self.current_frame += advance_steps

        # Voer de positie-update alleen uit als de teller een hele stap heeft bereikt
        if self.current_frame >= 1.0:
            steps_to_take = int(self.current_frame)
            self.current_frame -= steps_to_take
            
            for _ in range(steps_to_take):
                if self.moving_right:
                    self.position += 1
                    if self.position + line_length >= self.num_leds:
                        self.moving_right = False
                        self.position = self.num_leds - line_length - 1 
                        if self.position < 0: self.position = 0 # Zorg dat positie niet negatief wordt
                else:
                    self.position -= 1
                    if self.position <= 0:
                        self.moving_right = True
                        self.position = 0
        
        # Teken de hoofdlijn
        main_color = rgb_to_rgbw(int(r_base * brightness_factor), int(g_base * brightness_factor), int(b_base * brightness_factor))
        for i in range(line_length):
            led_pos = (self.position + i)
            if 0 <= led_pos < self.num_leds:
                frame[led_pos] = main_color

        # Teken de vervagende staart
        for fade in range(1, line_length + 1):
            current_fade_factor = 1.0 - (fade / (line_length + self.fade_divider))
            if current_fade_factor < 0: current_fade_factor = 0 # Zorg dat de factor niet negatief is

            faded_r_extra = int(r_base * current_fade_factor * brightness_factor)
            faded_g_extra = int(g_base * current_fade_factor * brightness_factor)
            faded_b_extra = int(b_base * current_fade_factor * brightness_factor)
            
            red_out_faded, green_out_faded, blue_out_faded, white_out_faded = rgb_to_rgbw(
                faded_r_extra, faded_g_extra, faded_b_extra
            )
            final_faded_color = [red_out_faded, green_out_faded, blue_out_faded, white_out_faded]

            # Vervagende staart voor achter de "kop"
            prev_pos = self.position - fade
            if 0 <= prev_pos < self.num_leds:
                # Alleen overschrijven als de nieuwe kleur helderder is, of als de huidige LED uit is
                if frame[prev_pos][0] < final_faded_color[0] or sum(frame[prev_pos][:3]) == 0:
                    frame[prev_pos] = final_faded_color
            
            # Vervagende staart voor voor de "kop" (als de lijn beweegt)
            next_pos = self.position + line_length + fade - 1
            if 0 <= next_pos < self.num_leds:
                if frame[next_pos][0] < final_faded_color[0] or sum(frame[next_pos][:3]) == 0:
                    frame[next_pos] = final_faded_color

        return frame
