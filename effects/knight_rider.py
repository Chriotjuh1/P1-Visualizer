from .effects import Effects
from .schemas import KnightRiderParams
from utils import rgb_to_rgbw

class KnightRiderEffect(Effects):
    def __init__(self, model):
        super().__init__(model)
        self.params: KnightRiderParams = self.params
        self.position = 0.0
        self.direction = 1

    def get_next_frame(self, delta_time: float = 0.0):
        pixels_per_second = self.speed * 40
        self.position += self.direction * pixels_per_second * delta_time
        
        line_length = self.params.line_length
        if self.position + line_length >= self.num_leds:
            self.position = self.num_leds - line_length
            self.direction = -1
        if self.position <= 0:
            self.position = 0
            self.direction = 1
            
        frame = [[0, 0, 0, 0]] * self.num_leds
        r, g, b = self.params.color[0].red, self.params.color[0].green, self.params.color[0].blue
        brightness = self.params.brightness / 100.0
        main_color = rgb_to_rgbw(int(r * brightness), int(g * brightness), int(b * brightness))
        
        start_led = int(self.position)
        for i in range(line_length):
            if 0 <= start_led + i < self.num_leds:
                frame[start_led + i] = main_color
        
        return frame
