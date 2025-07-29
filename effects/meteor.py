import random
from .effects import Effects
from .schemas import MeteorParams
from utils import rgb_to_rgbw

class MeteorEffect(Effects):
    def __init__(self, model):
        super().__init__(model)
        self.params: MeteorParams = self.params
        self.max_sparkle_duration = 1.0 # Levensduur in seconden
        self._on_num_leds_change()

    def _on_num_leds_change(self):
        self.position = float(self.num_leds - 1)
        self.sparkles = {} # Slaat op: {index: resterende_tijd}

    def get_next_frame(self, delta_time: float):
        pixels_per_second = self.speed * 50
        
        last_pos_int = int(self.position)
        self.position -= pixels_per_second * delta_time
        new_pos_int = int(self.position)
        
        if self.position + self.params.meteor_width < -20: # Reset
            self.position = float(self.num_leds - 1)
            self.sparkles.clear()
            
        for p in range(new_pos_int, last_pos_int):
            sparkle_index = p + self.params.meteor_width
            if 0 <= sparkle_index < self.num_leds and random.randint(0, 100) < self.params.spark_intensity:
                self.sparkles[sparkle_index] = self.max_sparkle_duration
                
        frame = [[0, 0, 0, 0]] * self.num_leds
        brightness = self.params.brightness / 100.0
        r, g, b = self.params.color[0].red, self.params.color[0].green, self.params.color[0].blue
        
        for i in range(self.params.meteor_width):
            if 0 <= int(self.position) + i < self.num_leds:
                frame[int(self.position) + i] = rgb_to_rgbw(int(r*brightness), int(g*brightness), int(b*brightness))
                
        keys_to_delete = []
        for key, time_left in self.sparkles.items():
            time_left -= delta_time
            if time_left <= 0:
                keys_to_delete.append(key)
                continue
            sparkle_brightness = time_left / self.max_sparkle_duration
            r_s = int(r * brightness * sparkle_brightness)
            g_s = int(g * brightness * sparkle_brightness)
            b_s = int(b * brightness * sparkle_brightness)
            if 0 <= key < self.num_leds:
                frame[key] = rgb_to_rgbw(r_s, g_s, b_s)
            self.sparkles[key] = time_left
            
        for key in keys_to_delete:
            del self.sparkles[key]
            
        return frame
