# P1-Visualizer/effects/knight_rider.py
from .base_effect import Effects
from .converts import rgb_to_rgbw
from .schemas import KnightRiderParams


class KnightRiderEffect(Effects):
    params: KnightRiderParams
    fade_divider: int = 3
    position: int = 0
    moving_right: bool = True
    last_update: int = 0
    # Voeg een frame_counter toe om de snelheid te regelen
    frame_counter: float = 0.0

    def get_next_frame(self):
        line_length = self.params.line_length # Gebruik line_length van params
        red = self.params.color[0].red
        green = self.params.color[0].green
        blue = self.params.color[0].blue

        frame = [[0, 0, 0, 0]] * self.num_leds
        brightness_factor = self.params.brightness / 100

        faded_r = int(red * brightness_factor)
        faded_g = int(green * brightness_factor)
        faded_b = int(blue * brightness_factor)
        red_out, green_out, blue_out, white_out = rgb_to_rgbw(faded_r, faded_g, faded_b)

        # Update de positie van de Knight Rider op basis van de FPS
        # De visualizer's timer draait op ~33 FPS (30ms).
        # self.fps is de doelsnelheid van de slider (bijv. 6 tot 150).
        # Bereken hoeveel stappen de animatie deze frame moet vooruitgaan.
        advance_steps = self.fps / 33.0
        self.frame_counter += advance_steps

        if self.frame_counter >= 1.0:
            steps_to_take = int(self.frame_counter)
            self.frame_counter -= steps_to_take
            
            for _ in range(steps_to_take):
                if self.moving_right:
                    self.position += 1
                    if self.position + line_length >= self.num_leds:
                        self.moving_right = False
                        self.position = self.num_leds - line_length -1 # Zorg dat de lijn niet buiten beeld gaat
                        if self.position < 0: self.position = 0 # Voorkom negatieve positie bij korte lijnen
                else:
                    self.position -= 1
                    if self.position <= 0:
                        self.moving_right = True
                        self.position = 0
        
        # Teken de hoofdlijn van de Knight Rider
        for line in range(line_length):
            led_pos = (self.position + line)
            if 0 <= led_pos < self.num_leds: # Zorg ervoor dat de positie binnen de grenzen valt
                frame[led_pos] = [red_out, green_out, blue_out, white_out]

        # Teken de vervagende staart
        # De fade_factor wordt per stap van de staart vermenigvuldigd
        # Dit creëert een geleidelijke vervaging
        for fade in range(1, line_length + 1): # Loop door de hele lengte voor de staart
            # Bereken de fade_factor. Hoe verder van de hoofdlijn, hoe meer vervaagd.
            current_fade_factor = 1.0 - (fade / (line_length + self.fade_divider)) # Lineaire fade over de lengte + divider
            if current_fade_factor < 0: current_fade_factor = 0 # Zorg dat het niet negatief wordt

            faded_r_extra = int(red * current_fade_factor * brightness_factor)
            faded_g_extra = int(green * current_fade_factor * brightness_factor)
            faded_b_extra = int(blue * current_fade_factor * brightness_factor)
            red_out_faded, green_out_faded, blue_out_faded, white_out_faded = rgb_to_rgbw(
                faded_r_extra, faded_g_extra, faded_b_extra
            )
            final_faded_color = [red_out_faded, green_out_faded, blue_out_faded, white_out_faded]

            # Teken de vervagende LEDs achter de hoofdlijn
            prev_pos = self.position - fade
            if 0 <= prev_pos < self.num_leds:
                frame[prev_pos] = final_faded_color
            
            # Teken de vervagende LEDs voor de hoofdlijn (voor symmetrie)
            next_pos = self.position + line_length + fade - 1
            if 0 <= next_pos < self.num_leds:
                frame[next_pos] = final_faded_color

        return frame
