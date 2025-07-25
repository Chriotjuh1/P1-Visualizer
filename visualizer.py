import sys
import math
import time
import copy
import random
import os
import numpy as np
import cv2
import imageio
import uuid # Voor het genereren van unieke ID's

# Voeg de directory van het script toe aan sys.path zodat modules gevonden kunnen worden
# Dit is cruciaal als het script niet vanuit de root van de projectmap wordt uitgevoerd.
script_dir = os.path.abspath(os.path.dirname(__file__)) # Gebruik absolute pad
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

# print(f"DEBUG: script_dir: {script_dir}") # Debug output, kan uitgecommentarieerd worden
# print(f"DEBUG: sys.path na toevoeging: {sys.path}") # Debug output, kan uitgecommentarieerd worden

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QSlider, QComboBox, QFileDialog, QColorDialog, QApplication, QMessageBox,
    QStatusBar, QGroupBox, QSizePolicy
)
from PyQt5.QtCore import Qt, QTimer, QEvent, QSize, QRectF
from PyQt5.QtGui import QMouseEvent, QIcon, QImage, QPixmap, QPainter, QColor
import pyqtgraph as pg
from pyqtgraph.exporters import ImageExporter
from PIL import Image

# Schakel OpenGL in voor vloeiendere rendering en anti-aliasing
pg.setConfigOptions(useOpenGL=True)

# --- Probeer de echte utility en effect bestanden te importeren ---
try:
    # BELANGRIJKE OPMERKING: Zorg ervoor dat de 'effects' map een geldige Python package is
    # (d.w.w.z. dat er een leeg of initieel '__init__.py' bestand in zit).
    # Controleer ook of de methodenamen in je effectbestanden (bijv. effects/base_effect.py,
    # effects/static.py, effects/breathing.py) allemaal 'get_next_frame' (snake_case) gebruiken
    # in plaats van 'getNextFrame' (camelCase). Dit is cruciaal voor de functionaliteit.
    from effects.schemas import ( # Aangepast importpad
        EffectModel, StaticParams, BreathingParams, Color,
        KnightRiderParams, MeteorParams, MulticolorParams,
        RunningLineParams, ChristmasSnowParams, FlagParams
    )
    from effects.effects import Effects # Aangepast importpad
    from effects.breathing import BreathingEffect # Aangepast importpad
    from effects.knight_rider import KnightRiderEffect # Aangepast importpad
    from effects.meteor import MeteorEffect # Aangepast importpad
    from effects.multicolor import MulticolorEffect # Aangepast importpad
    from effects.running_line import RunningLineEffect # Aangepast importpad
    from effects.christmas_snow import ChristmasSnowEffect # Aangepast importpad
    from effects.flag import FlagEffect # Aangepast importpad
    from effects.static import StaticEffect # Aangepast importpad
    
    from utils import distance, resample_points, smooth_points, point_line_distance # Aangepast importpad
    from effects.converts import rgb_to_rgbw # Aangepast importpad
    print("INFO: Echte 'utils' en 'effects' modules geladen.")

    # Mapping van effectnamen naar hun klassen
    _effect_classes = {
        "Static": StaticEffect,
        "Pulseline": BreathingEffect,
        "Knight Rider": KnightRiderEffect,
        "Meteor": MeteorEffect,
        "Multicolor": MulticolorEffect,
        "Running Line": RunningLineEffect,
        "Christmas Snow": ChristmasSnowEffect,
        "Flag": FlagEffect
    }
    def get_effect_class(effect_name): return _effect_classes.get(effect_name)

except ImportError as e:
    print(f"WAARSCHUWING: Kon de echte 'utils' en 'effects' modules niet vinden: {e}. Fallback naar dummy implementaties.")
    # Dummy implementaties voor ontwikkeling zonder volledige modules
    def distance(p1, p2): return math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)
    def resample_points(points, interval):
        if len(points) < 2: return points
        # Voor dummy: simpele resampling, kan later verbeterd worden
        if interval <= 0: return points
        resampled = [points[0]]
        current_dist = 0.0
        for i in range(len(points) - 1):
            segment_length = distance(points[i], points[i+1])
            if segment_length == 0: continue
            num_segments = int(segment_length / interval)
            for j in range(1, num_segments + 1):
                t = j * interval / segment_length
                new_x = points[i][0] + t * (points[i+1][0] - points[i][0])
                new_y = points[i][1] + t * (points[i+1][1] - points[i][1])
                resampled.append((new_x, new_y))
        if len(points) > 1: resampled.append(points[-1])
        return resampled


    def smooth_points(points, window=5): return points
    def point_line_distance(point, p1, p2):
        line_length_sq = distance(p1, p2)**2
        if line_length_sq == 0: return distance(point, p1)
        t = max(0, min(1, (((point[0] - p1[0]) * (p2[0] - p1[0])) + ((point[1] - p1[1]) * (p2[1] - p1[1]))) / line_length_sq))
        closest_point = (p1[0] + t * (p2[0] - p1[0]), p1[1] + t * (p2[1] - p1[1]))
        return distance(point, closest_point)
    def rgb_to_rgbw(r, g, b): return int(r), int(g), int(b), 0 # Zorg dat het integers zijn
    
    # Dummy klassen voor de effecten en schema's
    class Color:
        # Aangepast om keyword arguments te accepteren voor consistentie
        def __init__(self, red, green, blue): 
            self.red, self.green, self.blue = int(red), int(green), int(blue)
        def __repr__(self): return f"Color(r={self.red}, g={self.green}, b={self.blue})"
    
    class StaticParams:
        def __init__(self, color, brightness): self.color, self.brightness = color, brightness
    class BreathingParams:
        def __init__(self, color, brightness): self.color, self.brightness = color, brightness
    class KnightRiderParams:
        def __init__(self, color, brightness, line_length): self.color, self.brightness, self.line_length = color, brightness, line_length
    class MeteorParams:
        def __init__(self, color, brightness, meteor_width, spark_intensity): self.color, self.brightness, self.meteor_width, self.spark_intensity = color, brightness, meteor_width, spark_intensity
    class MulticolorParams:
        def __init__(self, brightness): self.brightness = brightness
    class RunningLineParams:
        def __init__(self, color, brightness, line_width, background_color, number_of_lines): self.color, self.brightness, self.line_width, self.background_color, self.number_of_lines = color, brightness, line_width, background_color, number_of_lines
    class ChristmasSnowParams:
        def __init__(self, brightness, red_chance, dark_green_chance): self.brightness, self.red_chance, self.dark_green_chance = brightness, red_chance, dark_green_chance
    class FlagParams:
        def __init__(self, color, brightness, width, background_color): self.color, self.brightness, self.width, self.background_color = color, brightness, width, background_color

    class EffectModel:
        def __init__(self, params, frame_skip, fps, num_leds): self.params, self.frame_skip, self.fps, self.num_leds = params, frame_skip, fps, num_leds
    
    class Effects:
        def __init__(self, model: EffectModel):
            self.model = model
            self.params = model.params
            self.fps = model.fps
            self._num_leds = model.num_leds
            self._on_num_leds_change()

        @property
        def num_leds(self):
            return self._num_leds

        @num_leds.setter
        def num_leds(self, value):
            if self._num_leds != value:
                self._num_leds = value
                self._on_num_leds_change()

        def _on_num_leds_change(self):
            pass

        def get_next_frame(self):
            raise NotImplementedError("get_next_frame() must be implemented by subclasses")


    class DummyStaticEffect(Effects):
        def get_next_frame(self):
            r, g, b = self.params.color[0].red, self.params.color[0].green, self.params.color[0].blue
            brightness_factor = self.params.brightness / 100.0
            return [[int(r * brightness_factor), int(g * brightness_factor), int(b * brightness_factor), 0]] * self.num_leds
    
    class DummyBreathingEffect(Effects):
        def __init__(self, model):
            super().__init__(model)
            self.current_breathing_factor = 0.0
            self.rising = True
        def get_next_frame(self):
            brightness = self.params.brightness / 100.0
            speed_factor = self.fps / 30.0
            increment = 5 * speed_factor
            if self.rising:
                self.current_breathing_factor += increment
                if self.current_breathing_factor >= 255.0:
                    self.current_breathing_factor = 255.0
                    self.rising = False
            else:
                self.current_breathing_factor -= increment
                if self.current_breathing_factor <= 0:
                    self.current_breathing_factor = 0
                    self.rising = True
            normalized_factor = self.current_breathing_factor / 255.0
            r, g, b = self.params.color[0].red, self.params.color[0].green, self.params.color[0].blue
            r_breath, g_breath, b_breath = r * normalized_factor, g * normalized_factor, b * normalized_factor
            red, green, blue = int(r_breath * brightness), int(g_breath * brightness), int(b_breath * brightness)
            red, green, blue, white = rgb_to_rgbw(red, green, blue)
            return [[red, green, blue, white]] * self.num_leds

    class DummyKnightRiderEffect(Effects):
        def __init__(self, model):
            super().__init__(model)
            self.position = 0
            self.moving_right = True
            self.fade_divider = 3
            self.frame_counter = 0.0 # Initialiseer frame_counter

        def get_next_frame(self):
            line_length = self.params.line_length
            r, g, b = self.params.color[0].red, self.params.color[0].green, self.params.color[0].blue
            brightness_factor = self.params.brightness / 100
            
            frame = [[0, 0, 0, 0]] * self.num_leds

            # Update de positie van de Knight Rider op basis van de FPS
            advance_steps = self.fps / 33.0 # Gebruik 33.0 als basis voor de visualizer's FPS
            self.frame_counter += advance_steps

            if self.frame_counter >= 1.0:
                steps_to_take = int(self.frame_counter)
                self.frame_counter -= steps_to_take
                
                for _ in range(steps_to_take):
                    if self.moving_right:
                        self.position += 1
                        if self.position + line_length >= self.num_leds:
                            self.moving_right = False
                            self.position = self.num_leds - line_length -1 
                            if self.position < 0: self.position = 0
                    else:
                        self.position -= 1
                        if self.position <= 0:
                            self.moving_right = True
                            self.position = 0
            
            # Teken de hoofdlijn
            main_color = rgb_to_rgbw(int(r * brightness_factor), int(g * brightness_factor), int(b * brightness_factor))
            for i in range(line_length):
                led_pos = (self.position + i)
                if 0 <= led_pos < self.num_leds:
                    frame[led_pos] = main_color

            # Teken de vervagende staart
            for fade in range(1, line_length + 1):
                current_fade_factor = 1.0 - (fade / (line_length + self.fade_divider))
                if current_fade_factor < 0: current_fade_factor = 0

                faded_r_extra = int(r * current_fade_factor * brightness_factor)
                faded_g_extra = int(g * current_fade_factor * brightness_factor)
                faded_b_extra = int(b * current_fade_factor * brightness_factor)
                red_out_faded, green_out_faded, blue_out_faded, white_out_faded = rgb_to_rgbw(
                    faded_r_extra, faded_g_extra, faded_b_extra
                )
                final_faded_color = [red_out_faded, green_out_faded, blue_out_faded, white_out_faded]

                prev_pos = self.position - fade
                if 0 <= prev_pos < self.num_leds:
                    frame[prev_pos] = final_faded_color
                
                next_pos = self.position + line_length + fade - 1
                if 0 <= next_pos < self.num_leds:
                    frame[next_pos] = final_faded_color

            return frame

    class DummyMeteorEffect(Effects):
        def __init__(self, model):
            super().__init__(model)
            self.max_sparkle_duration = 100
            self.frame_counter = 0.0 # Gebruik float voor meer precisie
            self._on_num_leds_change()

        def _on_num_leds_change(self):
            """Reset de status wanneer het aantal LEDs verandert."""
            self.position = float(self.num_leds - 1)
            self.sparkles = {}

        def get_next_frame(self):
            # --- State Update Logic (throttled by speed/fps) ---
            
            # De visualizer's timer runs at ~33 FPS (30ms).
            # self.fps is de doelsnelheid van de slider (bijv. 6 tot 150).
            # Bereken hoeveel stappen de animatie deze frame moet vooruitgaan.
            advance_steps = self.fps / 33.0
            self.frame_counter += advance_steps

            if self.frame_counter >= 1.0:
                steps_to_take = int(self.frame_counter)
                self.frame_counter -= steps_to_take
                
                for _ in range(steps_to_take):
                    self.position -= 1

                    # Reset logica: reset als de meteoor + staart volledig van het scherm is
                    if self.position + self.params.meteor_width < -self.max_sparkle_duration:
                        self.position = float(self.num_leds - 1)
                        self.sparkles.clear()

                    # Sparkle creatie
                    sparkle_index = int(self.position) + self.params.meteor_width
                    if 0 <= sparkle_index < self.num_leds:
                        if random.randint(0, 100) < self.params.spark_intensity:
                            self.sparkles[sparkle_index] = self.max_sparkle_duration

            # --- Drawing Logic (elke frame) ---
            frame = [[0, 0, 0, 0]] * self.num_leds
            brightness_factor = self.params.brightness / 100
            r_base = self.params.color[0].red
            g_base = self.params.color[0].green
            b_base = self.params.color[0].blue

            # Teken meteoor
            for i in range(self.params.meteor_width):
                led_index = int(self.position) + i
                if 0 <= led_index < self.num_leds:
                    r = int(r_base * brightness_factor)
                    g = int(g_base * brightness_factor)
                    b = int(b_base * brightness_factor)
                    frame[led_index] = rgb_to_rgbw(r, g, b)

            # Teken en fade vonken
            keys_to_delete = []
            for key, value in self.sparkles.items():
                value -= 2 # Fade elke frame (iets sneller)
                if value <= 0:
                    keys_to_delete.append(key)
                    continue
                
                sparkle_brightness = value / self.max_sparkle_duration
                sparkle_color_factor = brightness_factor * sparkle_brightness
                
                r = int(r_base * sparkle_color_factor)
                g = int(g_base * sparkle_color_factor)
                b = int(b_base * sparkle_color_factor)
                
                # Zorg ervoor dat de vonk geen helderder deel van de meteoor overschrijft
                if 0 <= key < self.num_leds and frame[key][0] < r:
                    frame[key] = rgb_to_rgbw(r, g, b)

                self.sparkles[key] = value

            for key in keys_to_delete:
                if key in self.sparkles:
                    del self.sparkles[key]

            return frame


    class DummyMulticolorEffect(Effects):
        def __init__(self, model):
            super().__init__(model)
            self.initial_hsv_color = [0.0, 1.0, 1.0]
        def get_next_frame(self):
            import colorsys
            brightness_factor = self.params.brightness / 100
            red_hsv, green_hsv, blue_hsv = colorsys.hsv_to_rgb(*self.initial_hsv_color)
            self.initial_hsv_color[0] = round(self.initial_hsv_color[0] + 0.01, 3)
            if self.initial_hsv_color[0] > 1:
                self.initial_hsv_color[0] = 0
            red = int(red_hsv * 255 * brightness_factor)
            green = int(green_hsv * 255 * brightness_factor)
            blue = int(blue_hsv * 255 * brightness_factor)
            return [rgb_to_rgbw(red, green, blue)] * self.num_leds

    class DummyRunningLineEffect(Effects):
        def __init__(self, model):
            super().__init__(model)
            self.pos = 0
        def get_next_frame(self):
            line_width = self.params.line_width
            bg_r = self.params.background_color.red
            bg_g = self.params.background_color.green
            bg_b = self.params.background_color.blue
            
            fg_r = self.params.color[0].red
            fg_g = self.params.color[0].green
            fg_b = self.params.color[0].blue

            bg_rgbw = rgb_to_rgbw(bg_r, bg_g, bg_b)
            fg_rgbw = rgb_to_rgbw(fg_r, fg_g, fg_b)

            frame = [bg_rgbw] * self.num_leds
            
            if self.params.number_of_lines > 0:
                gap = self.num_leds // self.params.number_of_lines
                for i in range(self.params.number_of_lines):
                    current_gap = gap * i
                    for width in range(line_width):
                        idx = (self.pos + current_gap + width) % self.num_leds
                        frame[idx] = fg_rgbw
            
            self.pos = (self.pos + 1) % self.num_leds
            return frame

    class DummyChristmasSnowEffect(Effects):
        def __init__(self, model):
            self.bg_r, self.bg_g, self.bg_b = 0, 120, 0
            self.sparkle_brightness = 255
            self.fade_speed = 10
            self.star_density = 20
            self.led_states = []
            super().__init__(model)

        def _on_num_leds_change(self):
            self.led_states = [[[self.bg_r, self.bg_g, self.bg_b], 0] for _ in range(self.num_leds)]

        def handle_green_red(self, color, led):
            r, g, b = color
            red = max(self.bg_r, r - self.fade_speed) if r > self.bg_r else min(self.bg_r, r + self.fade_speed)
            green = max(self.bg_g, g - self.fade_speed) if g > self.bg_g else min(self.bg_g, g + self.fade_speed)
            blue = max(self.bg_b, b - self.fade_speed) if b > self.bg_b else min(self.bg_b, b + self.fade_speed)
            self.led_states[led][0] = [red, green, blue]
            if abs(red - self.bg_r) < 10 and abs(green - self.bg_g) < 10 and abs(blue - self.bg_b) < 10: # Changed from 5 to 10
                self.led_states[led] = [[self.bg_r, self.bg_g, self.bg_b], 0]
            return red, green, blue

        def get_next_frame(self):
            frame = []
            for led in range(self.num_leds):
                color, type = self.led_states[led]
                if type == 0:
                    red, green, blue = self.bg_r, self.bg_g, self.bg_b
                else:
                    red, green, blue = self.handle_green_red(color, led)

                if self.led_states[led][1] == 0 and random.randint(0, 100) < self.star_density:
                    faded_green = self.bg_g - random.randint(60, 120)
                    red_color = [[self.sparkle_brightness, 0, 0], 1]
                    green_color = [[0, faded_green, 0], 2]
                    white_color = [[self.sparkle_brightness, self.sparkle_brightness, self.sparkle_brightness], 3]
                    
                    white_chance = 100 - self.params.red_chance - self.params.dark_green_chance
                    if white_chance < 0: white_chance = 0 # Ensure non-negative weight

                    try:
                        self.led_states[led] = random.choices(
                            [red_color, green_color, white_color],
                            weights=[self.params.red_chance, self.params.dark_green_chance, white_chance],
                        )[0]
                    except ValueError: # Handles case where all weights are zero
                           self.led_states[led] = [[self.bg_r, self.bg_g, self.bg_b], 0]


                brightness_mod = self.params.brightness / 100
                adjusted_red = int(red * brightness_mod)
                adjusted_green = int(green * brightness_mod)
                adjusted_blue = int(blue * brightness_mod)
                
                r, g, b, w = rgb_to_rgbw(adjusted_red, adjusted_green, adjusted_blue)
                frame.append([r, g, b, w])
            return frame

    class DummyFlagEffect(Effects):
        def __init__(self, model):
            super().__init__(model)
            self.position = 0
        def get_next_frame(self):
            frame = [[0, 0, 0, 0]] * self.num_leds
            brightness_factor = self.params.brightness / 100
            
            current_segment_start = self.position
            for idx, color_input in enumerate(self.params.color):
                flag_width = self.params.width[idx]
                # CORRECTIE: Verwijder de dubbele 'brightness' factor.
                # De 'brightness_factor' is al berekend op basis van self.params.brightness.
                scaled_red = int(color_input.red * brightness_factor)
                scaled_green = int(color_input.green * brightness_factor) # Fixed: removed extra 'brightness' multiplication
                scaled_blue = int(color_input.blue * brightness_factor)
                rgbw = rgb_to_rgbw(scaled_red, scaled_green, scaled_blue)
                
                for led_offset in range(flag_width):
                    index = (current_segment_start + led_offset) % self.num_leds
                    frame[index] = rgbw
                current_segment_start = (current_segment_start + flag_width) % self.num_leds
            self.position = (self.position + 1) % self.num_leds
            return frame

    # Dummy get_effect_class functie
    _effect_classes = {
        "Static": DummyStaticEffect,
        "Pulseline": DummyBreathingEffect, # Naam in UI is Pulseline, klasse is BreathingEffect
        "Knight Rider": DummyKnightRiderEffect,
        "Meteor": DummyMeteorEffect,
        "Multicolor": DummyMulticolorEffect,
        "Running Line": DummyRunningLineEffect,
        "Christmas Snow": DummyChristmasSnowEffect,
        "Flag": DummyFlagEffect
    }
    def get_effect_class(effect_name): return _effect_classes.get(effect_name)


class LEDVisualizer(QMainWindow):
    """
    Hoofdvenster van de LED Visualizer applicatie.
    Biedt functionaliteit voor het laden van afbeeldingen, tekenen van lijnen,
    toepassen van visuele effecten, en exporteren van afbeeldingen/video's.
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Pulseline1 Visualizer")
        self.setGeometry(100, 100, 1920, 1080) # Standaard venstergrootte
        
        try:
            self.setWindowIcon(QIcon(os.path.join(script_dir, "icons", "pulseline1.ico")))
        except Exception as e:
            print(f"WAARSCHUWING: Kon 'icons/pulseline1.ico' niet laden: {e}")

        self.original_image = None
        self.image = None
        self.image_item = None

        self.actions = []
        self.current_action = None
        
        # line_plot_items zal nu ScatterPlotItem objecten bevatten om individuele LEDs te tekenen
        self.line_plot_items = {} 
        self.point_plot_items = {} # Voor bewerkingspunten
        self.effect_instances = {}

        self.effect_index = 0
        self.default_brightness = 1.0
        self.default_speed = 5
        self.line_width = 3 # Dit wordt nu de grootte van de individuele LEDs
        self.led_color = (255, 0, 0)

        self.draw_mode = "Vrij Tekenen"
        self.drawing = False
        self.line_drawing_first_click = False
        
        self.selected_action_index = -1
        self.selected_point_index = -1
        self.drag_start_pos = None

        self.undo_stack = []
        self.redo_stack = []

        self.init_ui()
        self.push_undo_state()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.timer_update)
        self.timer.start(10) # Verhoogde FPS naar 100 (10ms interval) voor vloeiendere animaties

    def init_ui(self):
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        self.plot_widget = pg.PlotWidget(background=None, border=None)
        
        plot_item = self.plot_widget.getPlotItem()
        view_box = plot_item.getViewBox()

        plot_item.hideAxis('left')
        plot_item.hideAxis('bottom')

        view_box.setMouseEnabled(x=False, y=False)
        view_box.setAspectLocked(False)
        
        view_box.setContentsMargins(0, 0, 0, 0)
        plot_item.setContentsMargins(0, 0, 0, 0)

        main_layout.addWidget(self.plot_widget, 80)
        self.plot_widget.viewport().installEventFilter(self)

        control_layout = QVBoxLayout()
        main_layout.addLayout(control_layout, 20)
        
        control_layout.addWidget(QPushButton("Afbeelding Laden", clicked=self.load_image))

        control_layout.addWidget(QLabel("Tekenmodus:"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Vrij Tekenen", "Lijn Tekenen", "Lijn Bewerken"])
        self.mode_combo.currentIndexChanged.connect(self.change_mode)
        control_layout.addWidget(self.mode_combo)

        control_layout.addWidget(QLabel("LED Grootte (lijndikte):")) # Aangepaste label
        self.line_width_slider = QSlider(Qt.Horizontal, minimum=1, maximum=20, value=self.line_width)
        # FIX: Voeg self.update_drawing() toe voor directe visuele feedback
        self.line_width_slider.valueChanged.connect(lambda v: (setattr(self, 'line_width', v), self.update_drawing()))
        control_layout.addWidget(self.line_width_slider)

        control_layout.addWidget(QPushButton("Kies LED Kleur", clicked=self.choose_led_color))

        control_layout.addWidget(QLabel("Effect:"))
        self.effect_combo = QComboBox()
        
        if '_effect_classes' in globals():
            self.effect_names = list(globals()['_effect_classes'].keys())
        else:
            self.effect_names = ["Static", "Pulseline"]

        self.effect_combo.addItems(self.effect_names)
        self.effect_combo.currentIndexChanged.connect(self.change_effect)
        control_layout.addWidget(self.effect_combo)

        control_layout.addStretch()
        extra_options_group = QGroupBox("Extra Opties")
        extra_options_layout = QVBoxLayout(extra_options_group)

        extra_options_layout.addWidget(QLabel("Helderheid (globaal of per lijn):"))
        self.brightness_slider = QSlider(Qt.Horizontal, minimum=0, maximum=100, value=int(self.default_brightness * 100), singleStep=1)
        self.brightness_slider.valueChanged.connect(self.set_current_action_brightness)
        extra_options_layout.addWidget(self.brightness_slider)
        
        extra_options_layout.addWidget(QLabel("Snelheid (globaal of per lijn):"))
        self.speed_slider = QSlider(Qt.Horizontal, minimum=1, maximum=50, value=self.default_speed)
        self.speed_slider.valueChanged.connect(self.set_current_action_speed)
        extra_options_layout.addWidget(self.speed_slider)
        
        extra_options_layout.addWidget(QLabel("Achtergrond Donkerheid:"))
        self.darkness_slider = QSlider(Qt.Horizontal, minimum=0, maximum=80, value=0)
        self.darkness_slider.valueChanged.connect(self.update_background_darkness)
        extra_options_layout.addWidget(self.darkness_slider)

        self.effect_params_container = QWidget()
        self.effect_params_layout = QVBoxLayout(self.effect_params_container)
        extra_options_layout.addWidget(self.effect_params_container)
        self.current_effect_ui_elements = {}

        extra_options_layout.addWidget(QPushButton("Lijnen Samenvoegen", clicked=self.merge_lines))
        extra_options_layout.addWidget(QPushButton("Ongedaan Maken", clicked=self.undo_action))
        extra_options_layout.addWidget(QPushButton("Opnieuw Uitvoeren", clicked=self.redo_action))
        extra_options_layout.addWidget(QPushButton("Sla Afbeelding Op", clicked=self.save_image))
        extra_options_layout.addWidget(QPushButton("Exporteer MP4", clicked=self.export_video))
        extra_options_layout.addWidget(QPushButton("Roteer Links", clicked=lambda: self.rotate_image(-90)))
        extra_options_layout.addWidget(QPushButton("Roteer Rechts", clicked=lambda: self.rotate_image(90)))
        extra_options_layout.addWidget(QPushButton("Wis Afbeelding", clicked=self.clear_image))
        control_layout.addWidget(QPushButton("Wis Alle Lijnen", clicked=self.clear_all_lines)) # Changed to clear_all_lines

        control_layout.addWidget(extra_options_group)

        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.show_status_message("Klaar om te beginnen! Laad een afbeelding.")

        self.change_effect()
        self.change_mode()
        self.update_effect_parameters_ui()

    def show_status_message(self, message):
        self.statusBar.showMessage(message)

    def set_current_action_brightness(self, value):
        brightness_val = value / 100.0
        if self.selected_action_index != -1:
            self.actions[self.selected_action_index]['brightness'] = brightness_val
            self.actions[self.selected_action_index]['reset_effect_state'] = True
            self.show_status_message(f"Helderheid van geselecteerde lijn ingesteld op {value}%")
        else:
            self.default_brightness = brightness_val
            for action in self.actions:
                action['brightness'] = brightness_val
                action['reset_effect_state'] = True
            self.show_status_message(f"Globale helderheid ingesteld op {value}%")
        self.update_drawing()

    def set_current_action_speed(self, value):
        if self.selected_action_index != -1:
            self.actions[self.selected_action_index]['speed'] = value
            self.actions[self.selected_action_index]['reset_effect_state'] = True
            self.show_status_message(f"Snelheid van geselecteerde lijn ingesteld op {value}")
        else:
            self.default_speed = value
            for action in self.actions:
                action['speed'] = value
                action['reset_effect_state'] = True
            self.show_status_message(f"Globale snelheid ingesteld op {value}")
        self.update_drawing()

    def update_ui_for_selected_action(self):
        self.brightness_slider.blockSignals(True)
        self.speed_slider.blockSignals(True)

        if self.selected_action_index != -1:
            selected_action = self.actions[self.selected_action_index]
            self.brightness_slider.setValue(int(selected_action.get('brightness', self.default_brightness) * 100))
            self.speed_slider.setValue(selected_action.get('speed', self.default_speed))
            self.show_status_message(f"Lijn {self.selected_action_index + 1} geselecteerd.")
        else:
            self.brightness_slider.setValue(int(self.default_brightness * 100))
            self.speed_slider.setValue(self.default_speed)
            self.show_status_message("Geen lijn geselecteerd. Instellingen zijn globaal.")
        
        self.brightness_slider.blockSignals(False)
        self.speed_slider.blockSignals(False)
        
        self.update_effect_parameters_ui()
        self.update_drawing()

    def timer_update(self):
        self.update_drawing()

    def update_drawing(self):
        # Verwijder acties die niet meer bestaan
        current_action_ids = {action['id'] for action in self.actions}
        items_to_remove = [action_id for action_id in self.line_plot_items if action_id not in current_action_ids]
        
        for action_id in items_to_remove:
            if action_id in self.line_plot_items:
                self.plot_widget.removeItem(self.line_plot_items[action_id])
                del self.line_plot_items[action_id]
            if action_id in self.point_plot_items:
                self.plot_widget.removeItem(self.point_plot_items[action_id])
                del self.point_plot_items[action_id]
            if action_id in self.effect_instances:
                del self.effect_instances[action_id]

        # Voeg de tijdelijke actie toe als er getekend wordt
        all_actions_to_draw = self.actions[:]
        if self.current_action and len(self.current_action["points"]) > 0 and self.drawing:
            temp_action = copy.deepcopy(self.current_action)
            temp_action['id'] = 'temp_current_action'
            all_actions_to_draw.append(temp_action)

        for action_idx, action in enumerate(all_actions_to_draw):
            action_id = action.get('id', str(uuid.uuid4()))
            if 'id' not in action: action['id'] = action_id

            pts = action["points"]
            
            # Sla lege of te korte lijnen over
            if len(pts) < 2:
                if action_id in self.line_plot_items:
                    self.plot_widget.removeItem(self.line_plot_items[action_id])
                    del self.line_plot_items[action_id]
                if action_id in self.point_plot_items:
                    self.plot_widget.removeItem(self.point_plot_items[action_id])
                    del self.point_plot_items[action_id]
                if action_id in self.effect_instances:
                    del self.effect_instances[action_id]
                continue

            # Bepaal het huidige effect en zijn parameters
            effect_name = self.effect_names[self.effect_combo.currentIndex()]
            EffectClass = get_effect_class(effect_name)
            
            # Selecteer het juiste parameter schema voor het effect
            ParamsModel = StaticParams
            if effect_name == "Pulseline": ParamsModel = BreathingParams
            elif effect_name == "Knight Rider": ParamsModel = KnightRiderParams
            elif effect_name == "Meteor": ParamsModel = MeteorParams
            elif effect_name == "Multicolor": ParamsModel = MulticolorParams
            elif effect_name == "Running Line": ParamsModel = RunningLineParams
            elif effect_name == "Christmas Snow": ParamsModel = ChristmasSnowParams
            elif effect_name == "Flag": ParamsModel = FlagParams

            current_speed = action.get('speed', self.default_speed)
            current_brightness = action.get('brightness', self.default_brightness)
            r_base, g_base, b_base = action.get("color", self.led_color)
            
            # Bereid de parameters voor het effect voor
            params_data = {}
            if effect_name == "Static" or effect_name == "Pulseline":
                params_data = {"color": [Color(red=r_base, green=g_base, blue=b_base)], "brightness": int(current_brightness * 100)}
            elif effect_name == "Knight Rider":
                params_data = {"color": [Color(red=r_base, green=g_base, blue=b_base)], "brightness": int(current_brightness * 100), "line_length": action.get('line_length', 10)}
            elif effect_name == "Meteor":
                params_data = {"color": [Color(red=r_base, green=g_base, blue=b_base)], "brightness": int(current_brightness * 100), "meteor_width": action.get('meteor_width', 10), "spark_intensity": action.get('spark_intensity', 50)}
            elif effect_name == "Multicolor":
                params_data = {"brightness": int(current_brightness * 100)}
            elif effect_name == "Running Line":
                bg_color_rgb = action.get('background_color', (0,0,0))
                params_data = {"color": [Color(red=r_base, green=g_base, blue=b_base)], "brightness": int(current_brightness * 100), "line_width": action.get('line_width', 5), "background_color": Color(red=bg_color_rgb[0], green=bg_color_rgb[1], blue=bg_color_rgb[2]), "number_of_lines": action.get('number_of_lines', 3)}
            elif effect_name == "Christmas Snow":
                params_data = {"brightness": int(current_brightness * 100), "red_chance": action.get('red_chance', 30), "dark_green_chance": action.get('dark_green_chance', 30)}
            elif effect_name == "Flag":
                default_flag_colors_rgb = [(255,0,0), (255,255,255), (0,0,255)]
                default_flag_widths = [10, 10, 10]
                
                flag_colors_data = action.get('color', default_flag_colors_rgb)
                
                if not (isinstance(flag_colors_data, list) and all(isinstance(c, (list, tuple)) for c in flag_colors_data)):
                    flag_colors_data = default_flag_colors_rgb

                flag_colors = [Color(red=c[0], green=c[1], blue=c[2]) for c in flag_colors_data]
                flag_widths = action.get('width', default_flag_widths)
                bg_color_rgb = action.get('background_color', (0,0,0))
                params_data = {"color": flag_colors, "brightness": int(current_brightness * 100), "width": flag_widths, "background_color": Color(red=bg_color_rgb[0], green=bg_color_rgb[1], blue=bg_color_rgb[2])}
            else:
                params_data = {"color": [Color(red=r_base, green=g_base, blue=b_base)], "brightness": int(current_brightness * 100)}

            # Bereken de totale lengte van de lijn en het aantal virtuele LED's
            total_line_length = sum(distance(pts[k], pts[k+1]) for k in range(len(pts) - 1))
            num_leds_for_this_line = max(1, int(total_line_length / 5)) if total_line_length > 0 else 1 # Minimaal 1 LED

            # Hersampleer de punten als de lijn is gewijzigd of het effect gereset moet worden
            if action.get('recalculate_resample', True) or action.get('reset_effect_state', True):
                resampling_interval = total_line_length / (num_leds_for_this_line - 1) if num_leds_for_this_line > 1 else 1.0
                points_for_effect = resample_points(pts, resampling_interval)
                action['resampled_points'] = points_for_effect
                action['num_leds_actual'] = len(points_for_effect)
                action['recalculate_resample'] = False
            
            num_leds_for_this_line = action.get('num_leds_actual', 0)
            if num_leds_for_this_line == 0: num_leds_for_this_line = 1

            # Initialiseer of update de effect instantie
            effect_instance = self.effect_instances.get(action_id)
            # Cast fps to int to prevent Pydantic validation error
            calculated_fps = int(100 * (current_speed / 5.0)) 
            if not effect_instance or action.get('reset_effect_state', False) or not isinstance(effect_instance, EffectClass):
                params_instance = ParamsModel(**params_data)
                model = EffectModel(params=params_instance, frame_skip=0, fps=calculated_fps, num_leds=num_leds_for_this_line) 
                effect_instance = EffectClass(model)
                self.effect_instances[action_id] = effect_instance
                action['reset_effect_state'] = False
            else:
                # Update bestaande effect instantie met nieuwe parameters en LED-aantal
                effect_instance.params = ParamsModel(**params_data)
                effect_instance.num_leds = num_leds_for_this_line # Update num_leds property
                effect_instance.fps = calculated_fps
            
            # Haal de kleuren voor het huidige frame op van het effect
            frame_colors = effect_instance.get_next_frame()
            
            # Bereid de 'brushes' (kleuren) voor de ScatterPlotItem voor
            brushes = []
            # Zorg ervoor dat het aantal kleuren overeenkomt met het aantal punten
            # Als frame_colors korter is, vul aan met zwart. Als het langer is, negeer extra kleuren.
            for i in range(len(action['resampled_points'])):
                if i < len(frame_colors):
                    r, g, b = frame_colors[i][0], frame_colors[i][1], frame_colors[i][2]
                    brushes.append(pg.mkBrush(QColor(r, g, b)))
                else:
                    brushes.append(pg.mkBrush(QColor(0, 0, 0))) # Zwarte fallback

            # Haal de x en y coördinaten van de hersampleerde punten op
            x_coords = [p[0] for p in action['resampled_points']]
            y_coords = [p[1] for p in action['resampled_points']]

            # Gebruik ScatterPlotItem om individuele LEDs te tekenen
            scatter_item = self.line_plot_items.get(action_id)
            if not scatter_item:
                # Maak een nieuwe ScatterPlotItem als deze nog niet bestaat
                scatter_item = pg.ScatterPlotItem(
                    x=x_coords, y=y_coords, 
                    size=self.line_width, # Gebruik line_width als de grootte van de LED
                    brush=brushes, 
                    antialias=True,
                    pen=pg.mkPen(None) # Geen rand om de individuele LEDs
                )
                self.plot_widget.addItem(scatter_item)
                self.line_plot_items[action_id] = scatter_item
            else:
                # Update de data van de bestaande ScatterPlotItem
                scatter_item.setData(
                    x=x_coords, y=y_coords, 
                    size=self.line_width, 
                    brush=brushes
                )
            
            # Teken bewerkingspunten als de modus "Lijn Bewerken" is en deze lijn geselecteerd is
            if self.draw_mode == "Lijn Bewerken" and action_idx == self.selected_action_index:
                point_item = self.point_plot_items.get(action_id)
                if not point_item:
                    # Teken grotere, blauwe punten voor bewerking
                    point_item = pg.ScatterPlotItem(x=[p[0] for p in pts], y=[p[1] for p in pts], size=self.line_width + 5, brush=pg.mkBrush('b'), pen=pg.mkPen('w', width=1))
                    self.plot_widget.addItem(point_item)
                    self.point_plot_items[action_id] = point_item
                else:
                    point_item.setData(x=[p[0] for p in pts], y=[p[1] for p in pts])
            else:
                # Verwijder bewerkingspunten als de lijn niet geselecteerd is of de modus anders is
                if action_id in self.point_plot_items:
                    self.plot_widget.removeItem(self.point_plot_items[action_id])
                    del self.point_plot_items[action_id]

    def change_effect(self):
        self.effect_index = self.effect_combo.currentIndex()
        for action in self.actions:
            action['reset_effect_state'] = True
        self.show_status_message(f"Effect gewijzigd naar: {self.effect_names[self.effect_index]}")
        self.update_effect_parameters_ui()
        self.update_drawing()

    def choose_led_color(self):
        color = QColorDialog.getColor(QColor(*self.led_color))
        if color.isValid():
            new_color = (color.red(), color.green(), color.blue())
            if self.selected_action_index != -1:
                self.actions[self.selected_action_index]['color'] = new_color
                self.actions[self.selected_action_index]['reset_effect_state'] = True
                self.show_status_message(f"Kleur van geselecteerde lijn gewijzigd naar RGB{new_color}")
            else:
                self.led_color = new_color
                for action in self.actions:
                    action['color'] = new_color
                    action['reset_effect_state'] = True
                self.show_status_message(f"Globale LED kleur gewijzigd naar RGB{new_color}")
            self.update_drawing()

    def load_image(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Afbeelding Laden", "", "Afbeeldingen (*.png *.jpg *.jpeg *.bmp)")
        if file_path:
            try:
                pil_image = Image.open(file_path).convert("RGBA")
                self.original_image = np.array(pil_image)
                
                self.darkness_slider.setValue(0)
                self.update_background_darkness(0)

                self.clear_all_lines(False)
                self.push_undo_state()

                if self.original_image is not None:
                    h, w, _ = self.original_image.shape
                    self.plot_widget.getViewBox().setRange(xRange=(0, w), yRange=(0, h), padding=0)
                else:
                    self.plot_widget.getViewBox().autoRange()
                self.show_status_message(f"Afbeelding '{os.path.basename(file_path)}' geladen.")
            except Exception as e:
                QMessageBox.critical(self, "Fout bij Laden", f"Kon afbeelding niet laden: {e}")
                self.show_status_message(f"Fout bij laden van afbeelding: {e}")

    def update_display(self):
        if self.image is not None:
            if not self.image_item:
                self.image_item = pg.ImageItem()
                self.plot_widget.addItem(self.image_item)
            
            transposed_image = np.transpose(np.flipud(self.image), (1, 0, 2))
            self.image_item.setImage(transposed_image)
            h, w, _ = self.image.shape
            self.image_item.setRect(0, 0, w, h)
        else:
            if self.image_item:
                self.plot_widget.removeItem(self.image_item)
                self.image_item = None
        self.update_drawing()

    def clear_all_lines(self, push_undo=True):
        for action_id in list(self.line_plot_items.keys()):
            self.plot_widget.removeItem(self.line_plot_items[action_id])
            del self.line_plot_items[action_id]
        
        for action_id in list(self.point_plot_items.keys()):
            self.plot_widget.removeItem(self.point_plot_items[action_id])
            del self.point_plot_items[action_id]

        self.effect_instances.clear()
        self.actions.clear()
        self.current_action = None
        self.selected_action_index = -1
        self.selected_point_index = -1
        if push_undo:
            self.push_undo_state()
            self.show_status_message("Alle lijnen gewist.")
        self.update_drawing()
        self.update_ui_for_selected_action()

    def clear_image(self):
        if self.image_item:
            self.plot_widget.removeItem(self.image_item)
            self.image_item = None
        self.image = None
        self.original_image = None
        self.clear_all_lines(False)
        self.push_undo_state()
        self.show_status_message("Afbeelding gewist.")
        self.plot_widget.getViewBox().autoRange()

    def update_background_darkness(self, value):
        if self.original_image is None:
            return
        
        brightness_factor = 1.0 - (value / 100.0)
        self.image = self.original_image.copy()
        
        rgb_channels = self.image[:, :, :3].astype('float')
        rgb_channels *= brightness_factor
        rgb_channels = np.clip(rgb_channels, 0, 255)
        self.image[:, :, :3] = rgb_channels.astype('uint8')
        
        self.update_display()
        self.show_status_message(f"Achtergrond duisternis ingesteld op {value}%")

    def merge_lines(self):
        if len(self.actions) < 2:
            self.show_status_message("Minstens twee lijnen nodig om samen te voegen.")
            return

        self.push_undo_state()
        merge_threshold = 25
        merged_in_pass = True
        
        while merged_in_pass:
            merged_in_pass = False
            i = 0
            while i < len(self.actions):
                j = i + 1
                while j < len(self.actions):
                    line1, line2 = self.actions[i], self.actions[j]
                    p1_start, p1_end = line1['points'][0], line1['points'][-1]
                    p2_start, p2_end = line2['points'][0], line2['points'][-1]
                    merged = False
                    
                    if distance(p1_end, p2_start) < merge_threshold:
                        line1['points'].extend(line2['points'])
                        merged = True
                    elif distance(p1_end, p2_end) < merge_threshold:
                        line1['points'].extend(reversed(line2['points']))
                        merged = True
                    elif distance(p1_start, p2_end) < merge_threshold:
                        line1['points'] = list(reversed(line1['points'])) + line2['points']
                        merged = True
                    elif distance(p1_start, p2_start) < merge_threshold:
                        line1['points'] = list(reversed(line1['points'])) + list(reversed(line2['points']))
                        merged = True
                    
                    if merged:
                        removed_action_id = self.actions[j]['id']
                        if removed_action_id in self.line_plot_items:
                            self.plot_widget.removeItem(self.line_plot_items[removed_action_id])
                            del self.line_plot_items[removed_action_id]
                        if removed_action_id in self.point_plot_items:
                            self.plot_widget.removeItem(self.point_plot_items[removed_action_id])
                            del self.point_plot_items[removed_action_id]
                        if removed_action_id in self.effect_instances:
                            del self.effect_instances[removed_action_id]

                        self.actions.pop(j)
                        self.actions[i]['reset_effect_state'] = True
                        self.actions[i]['recalculate_resample'] = True
                        merged_in_pass = True
                        i = -1
                        break
                    else:
                        j += 1
                if i == -1: break
                i += 1
        
        self.update_drawing()
        self.push_undo_state()
        self.show_status_message("Lijnen samengevoegd.")

    def push_undo_state(self):
        state_to_save = []
        for action in self.actions:
            clean_action = {k: v for k, v in action.items() if k not in ['effect_instance', 'plot_items', 'resampled_points']}
            state_to_save.append(copy.deepcopy(clean_action)) # Gebruik deepcopy om geneste mutaties te voorkomen
        self.undo_stack.append(state_to_save)
        self.redo_stack.clear()

    def undo_action(self):
        if len(self.undo_stack) > 1:
            current_state = self.undo_stack.pop()
            self.redo_stack.append(current_state)
            
            for item in self.line_plot_items.values(): self.plot_widget.removeItem(item)
            self.line_plot_items.clear()
            for item in self.point_plot_items.values(): self.plot_widget.removeItem(item)
            self.point_plot_items.clear()
            self.effect_instances.clear()

            previous_state = self.undo_stack[-1]
            self.actions = copy.deepcopy(previous_state)
            
            for action in self.actions:
                action['reset_effect_state'] = True
                action['recalculate_resample'] = True
            
            self.selected_action_index = -1
            self.selected_point_index = -1
            self.update_drawing()
            self.update_ui_for_selected_action()
            self.show_status_message("Actie ongedaan gemaakt.")
        else:
            self.show_status_message("Niets om ongedaan te maken.")

    def redo_action(self):
        if self.redo_stack:
            restored_state = self.redo_stack.pop()
            self.undo_stack.append(restored_state)

            for item in self.line_plot_items.values(): self.plot_widget.removeItem(item)
            self.line_plot_items.clear()
            for item in self.point_plot_items.values(): self.plot_widget.removeItem(item)
            self.point_plot_items.clear()
            self.effect_instances.clear()

            self.actions = copy.deepcopy(restored_state)
            
            for action in self.actions:
                action['reset_effect_state'] = True
                action['recalculate_resample'] = True

            self.selected_action_index = -1
            self.selected_point_index = -1
            self.update_drawing()
            self.update_ui_for_selected_action()
            self.show_status_message("Actie opnieuw uitgevoerd.")
        else:
            self.show_status_message("Niets om opnieuw uit te voeren.")
    
    def rotate_image(self, angle):
        if self.original_image is None:
            self.show_status_message("Geen afbeelding geladen om te roteren.")
            return

        try:
            if angle == 90:
                self.original_image = cv2.rotate(self.original_image, cv2.ROTATE_90_CLOCKWISE)
            elif angle == -90:
                self.original_image = cv2.rotate(self.original_image, cv2.ROTATE_90_COUNTERCLOCKWISE)
            
            h, w, _ = self.original_image.shape
            self.plot_widget.getViewBox().setRange(xRange=(0, w), yRange=(0, h), padding=0)
            self.update_background_darkness(self.darkness_slider.value())
            
            self.clear_all_lines(False)
            self.push_undo_state()
            self.show_status_message(f"Afbeelding {angle} graden geroteerd.")
        except Exception as e:
            QMessageBox.critical(self, "Rotatie Fout", f"Fout bij roteren van afbeelding: {e}")
            self.show_status_message(f"Fout bij roteren van afbeelding: {e}")


    def change_mode(self):
        self.draw_mode = self.mode_combo.currentText()
        self.selected_action_index = -1
        self.selected_point_index = -1
        self.line_drawing_first_click = False
        self.update_ui_for_selected_action()
        self.update_drawing()
        self.show_status_message(f"Tekenmodus gewijzigd naar: {self.draw_mode}")

    def eventFilter(self, source, event):
        if source == self.plot_widget.viewport():
            if event.type() == QEvent.MouseButtonPress and event.button() == Qt.LeftButton:
                self.handle_mouse_press(event)
                return True
            elif event.type() == QEvent.MouseMove:
                self.handle_mouse_move(event)
                return True
            elif event.type() == QEvent.MouseButtonRelease and event.button() == Qt.LeftButton:
                self.handle_mouse_release(event)
                return True
        return super().eventFilter(source, event)
    
    def handle_mouse_press(self, event):
        pos = self.plot_widget.getViewBox().mapSceneToView(event.pos())
        point = (pos.x(), pos.y())

        if self.draw_mode == "Vrij Tekenen":
            self.drawing = True
            self.current_action = {"id": str(uuid.uuid4()), "mode": self.draw_mode, "points": [point], "color": self.led_color, 'speed': self.default_speed, 'brightness': self.default_brightness, 'reset_effect_state': True, 'recalculate_resample': True}
            self.show_status_message("Vrij tekenen gestart.")
        elif self.draw_mode == "Lijn Tekenen":
            if not self.line_drawing_first_click:
                self.drawing = True
                self.line_drawing_first_click = True
                self.current_action = {"id": str(uuid.uuid4()), "mode": self.draw_mode, "points": [point, point], "color": self.led_color, 'speed': self.default_speed, 'brightness': self.default_brightness, 'reset_effect_state': True, 'recalculate_resample': True}
                self.show_status_message("Beginpunt van lijn geselecteerd.")
            else:
                if self.current_action:
                    self.current_action["points"][1] = point
                    self.actions.append(self.current_action)
                    self.push_undo_state()
                    self.show_status_message("Lijn voltooid.")
                self.current_action, self.drawing, self.line_drawing_first_click = None, False, False
        elif self.draw_mode == "Lijn Bewerken":
            self.selected_action_index, self.selected_point_index = -1, -1
            min_dist = float('inf')
            
            for i, action in enumerate(self.actions):
                for j, p in enumerate(action["points"]):
                    dist = distance(point, p)
                    if dist < 15 and dist < min_dist:
                        min_dist = dist
                        self.selected_action_index = i
                        self.selected_point_index = j
            
            if self.selected_action_index == -1:
                min_dist_line = float('inf')
                closest_action_idx = -1
                for i, action in enumerate(self.actions):
                    if len(action["points"]) < 2: continue
                    for k in range(len(action["points"]) - 1):
                        dist = point_line_distance(point, action["points"][k], action["points"][k+1])
                        if dist < min_dist_line:
                            min_dist_line = dist
                            closest_action_idx = i
                
                if min_dist_line < 15:
                    self.selected_action_index = closest_action_idx
                    self.selected_point_index = -1

            if self.selected_action_index != -1:
                self.drawing = True
                self.drag_start_pos = point
                self.show_status_message(f"Lijn {self.selected_action_index + 1} geselecteerd voor bewerking.")
            else:
                self.show_status_message("Geen lijn of punt geselecteerd.")

            self.update_ui_for_selected_action()
        self.update_drawing()

    def handle_mouse_move(self, event):
        if not self.drawing: return
        pos = self.plot_widget.getViewBox().mapSceneToView(event.pos())
        point = (pos.x(), pos.y())

        if self.draw_mode == "Vrij Tekenen" and self.current_action:
            self.current_action["points"].append(point)
            self.current_action['recalculate_resample'] = True
            self.current_action['reset_effect_state'] = True
        elif self.draw_mode == "Lijn Tekenen" and self.current_action:
            self.current_action["points"][1] = point
            self.current_action['recalculate_resample'] = True
            self.current_action['reset_effect_state'] = True
        elif self.draw_mode == "Lijn Bewerken" and self.selected_action_index != -1:
            action = self.actions[self.selected_action_index]
            if self.selected_point_index != -1:
                action["points"][self.selected_point_index] = point
            elif self.drag_start_pos:
                dx, dy = point[0] - self.drag_start_pos[0], point[1] - self.drag_start_pos[1]
                action["points"] = [(px + dx, py + dy) for px, py in action["points"]]
                self.drag_start_pos = point
            action['reset_effect_state'] = True
            action['recalculate_resample'] = True
        self.update_drawing()

    def handle_mouse_release(self, event):
        if self.draw_mode == "Lijn Tekenen" and self.line_drawing_first_click:
            return

        if self.drawing:
            if self.draw_mode == "Vrij Tekenen" and self.current_action:
                if len(self.current_action["points"]) > 1:
                    self.actions.append(self.current_action)
                    self.push_undo_state()
                    self.show_status_message("Vrij tekenen voltooid.")
                else:
                    self.show_status_message("Lijn te kort om op te slaan.")
            elif self.draw_mode == "Lijn Bewerken" and self.selected_action_index != -1:
                self.push_undo_state()
                self.show_status_message("Lijn bewerking voltooid.")

        self.drawing = False
        self.drag_start_pos = None
        self.current_action = None
        self.update_drawing()

    def _add_slider(self, label_text, param_name, min_val, max_val, default_val):
        label = QLabel(label_text)
        slider = QSlider(Qt.Horizontal, minimum=min_val, maximum=max_val, value=default_val)
        slider.valueChanged.connect(lambda val: self.set_effect_specific_param(param_name, val))
        self.effect_params_layout.addWidget(label)
        self.effect_params_layout.addWidget(slider)
        self.current_effect_ui_elements[param_name] = slider
        return slider

    def _add_color_picker(self, label_text, param_name):
        label = QLabel(label_text)
        button = QPushButton("Kies Kleur")
        button.clicked.connect(lambda: self._choose_effect_color(param_name, button))
        
        initial_color = self.led_color
        if self.selected_action_index != -1:
            selected_action = self.actions[self.selected_action_index]
            if param_name.startswith("color_"):
                color_idx = int(param_name.split('_')[1])
                if 'color' in selected_action and isinstance(selected_action['color'], list) and len(selected_action['color']) > color_idx:
                    initial_color = selected_action['color'][color_idx]
                elif 'color' in selected_action and isinstance(selected_action['color'], tuple):
                    initial_color = selected_action['color']
            elif param_name == "background_color" and 'background_color' in selected_action and isinstance(selected_action['background_color'], tuple):
                initial_color = selected_action['background_color']
        
        button.setStyleSheet(f"background-color: rgb({initial_color[0]},{initial_color[1]},{initial_color[2]});")
        
        self.effect_params_layout.addWidget(label)
        self.effect_params_layout.addWidget(button)
        self.current_effect_ui_elements[param_name] = button
        return button

    def _choose_effect_color(self, param_name, button):
        current_color_rgb = self.led_color
        if self.selected_action_index != -1:
            selected_action = self.actions[self.selected_action_index]
            if param_name.startswith("color_"):
                color_idx = int(param_name.split('_')[1])
                if 'color' in selected_action and isinstance(selected_action['color'], list) and len(selected_action['color']) > color_idx:
                    current_color_rgb = selected_action['color'][color_idx]
                elif 'color' in selected_action and isinstance(selected_action['color'], tuple):
                    current_color_rgb = selected_action['color']
            elif param_name == "background_color" and 'background_color' in selected_action and isinstance(selected_action['background_color'], tuple):
                current_color_rgb = selected_action['background_color']

        color = QColorDialog.getColor(QColor(*current_color_rgb))
        if color.isValid():
            new_rgb = (color.red(), color.green(), color.blue())
            button.setStyleSheet(f"background-color: rgb({new_rgb[0]},{new_rgb[1]},{new_rgb[2]});")
            self.set_effect_specific_param(param_name, new_rgb)

    def set_effect_specific_param(self, param_name, value):
        if self.selected_action_index != -1:
            action = self.actions[self.selected_action_index]
            
            if param_name.startswith("color_"):
                color_idx = int(param_name.split('_')[1])
                if 'color' not in action or not isinstance(action.get('color'), list):
                    # If it's a tuple or doesn't exist, create a list based on default colors
                    action['color'] = [(255,0,0), (255,255,255), (0,0,255)]
                while len(action['color']) <= color_idx:
                    action['color'].append((255,255,255)) # Add white as default for new colors
                action['color'][color_idx] = value
            elif param_name.startswith("width_"):
                width_idx = int(param_name.split('_')[1])
                if 'width' not in action or not isinstance(action.get('width'), list):
                    action['width'] = [10, 10, 10]
                while len(action['width']) <= width_idx:
                    action['width'].append(10)
                action['width'][width_idx] = value
            else:
                action[param_name] = value
            
            action['reset_effect_state'] = True
            self.show_status_message(f"Parameter '{param_name}' van geselecteerde lijn ingesteld op: {value}")
        else:
            self.show_status_message("Selecteer een lijn om effect-specifieke parameters in te stellen.")

        self.update_drawing()

    def update_effect_parameters_ui(self):
        for i in reversed(range(self.effect_params_layout.count())):
            widget = self.effect_params_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)
                widget.deleteLater()
        self.current_effect_ui_elements.clear()

        selected_effect_name = self.effect_combo.currentText()
        
        selected_action_params = {}
        if self.selected_action_index != -1:
            selected_action_params = self.actions[self.selected_action_index]

        if selected_effect_name == "Knight Rider":
            default_val = selected_action_params.get('line_length', 10) 
            self._add_slider("Lijnlengte", "line_length", 1, 50, default_val) 
        
        elif selected_effect_name == "Meteor":
            self._add_slider("Meteoor Breedte", "meteor_width", 1, 50, selected_action_params.get('meteor_width', 10))
            self._add_slider("Vonk Intensiteit", "spark_intensity", 0, 100, selected_action_params.get('spark_intensity', 50))
        
        elif selected_effect_name == "Running Line":
            self._add_slider("Lijn Breedte", "line_width", 1, 20, selected_action_params.get('line_width', 5))
            self._add_slider("Aantal Lijnen", "number_of_lines", 1, 10, selected_action_params.get('number_of_lines', 3))
            self._add_color_picker("Achtergrond Kleur", "background_color")
        
        elif selected_effect_name == "Christmas Snow":
            self._add_slider("Rode Kans (%)", "red_chance", 0, 100, selected_action_params.get('red_chance', 30))
            self._add_slider("Donkergroene Kans (%)", "dark_green_chance", 0, 100, selected_action_params.get('dark_green_chance', 30))
        
        elif selected_effect_name == "Flag":
            default_colors = selected_action_params.get('color', [(255,0,0), (255,255,255), (0,0,255)])
            default_widths = selected_action_params.get('width', [10, 10, 10])

            for i in range(3):
                color_button = self._add_color_picker(f"Kleur {i+1}", f"color_{i}")
                current_color_rgb = default_colors[i] if i < len(default_colors) else (255,255,255)
                color_button.setStyleSheet(f"background-color: rgb({current_color_rgb[0]},{current_color_rgb[1]},{current_color_rgb[2]});")

                current_width = default_widths[i] if i < len(default_widths) else 10
                self._add_slider(f"Breedte {i+1}", f"width_{i}", 1, 50, current_width)
            
            bg_button = self._add_color_picker("Achtergrond Kleur", "background_color")
            bg_color_rgb = selected_action_params.get('background_color', (0,0,0))
            bg_button.setStyleSheet(f"background-color: rgb({bg_color_rgb[0]},{bg_color_rgb[1]},{bg_color_rgb[2]});")


    def _capture_and_crop_frame(self):
        """
        Maakt een schermafbeelding van de plot en exporteert deze als 1920x1080.
        Het zal de inhoud van de plot uitrekken om de 1920x1080 afmetingen te vullen
        als de oorspronkelijke beeldverhouding afwijkt.
        """
        if not self.image_item and not self.actions:
            QMessageBox.warning(self, "Export Fout", "Geen afbeelding of lijnen geladen om te exporteren!")
            return None

        QApplication.processEvents()

        EXPORT_WIDTH = 1920
        EXPORT_HEIGHT = 1080
        target_qimage_size = QSize(EXPORT_WIDTH, EXPORT_HEIGHT)

        qimage = QImage(target_qimage_size, QImage.Format_ARGB32)
        qimage.fill(Qt.transparent)

        painter = QPainter(qimage)
        
        try:
            painter.setRenderHint(QPainter.Antialiasing)
            scene = self.plot_widget.getPlotItem().scene()
            view_box = self.plot_widget.getViewBox()

            # Bepaal de bron-rechthoek voor het renderen.
            # Prioriteer de afmetingen van de originele afbeelding voor een perfecte uitsnede.
            if self.original_image is not None:
                h, w, _ = self.original_image.shape
                source_rect = QRectF(0, 0, w, h)
            else:
                # Fallback naar de zichtbare view als er geen afbeelding is (alleen lijnen).
                source_rect = view_box.viewRect()

            # Render de scene naar de QImage.
            # De inhoud van source_rect wordt geschaald om precies in qimage.rect() te passen.
            scene.render(painter, QRectF(qimage.rect()), source_rect)

        finally:
            painter.end()

        if qimage.isNull():
            print("WAARSCHUWING: Renderen van de scene naar QImage is mislukt.")
            return None

        buffer = qimage.constBits()
        buffer.setsize(qimage.sizeInBytes())
        arr = np.frombuffer(buffer, dtype=np.uint8).reshape((qimage.height(), qimage.width(), 4))
        
        arr_rgba = cv2.cvtColor(arr, cv2.COLOR_BGRA2RGBA)
        pil_image = Image.fromarray(arr_rgba, 'RGBA')

        return pil_image
    
    def save_image(self):
        if not self.image_item and not self.actions:
            QMessageBox.warning(self, "Opslaan Fout", "Geen afbeelding of lijnen geladen om op te slaan!")
            return

        file_path, _ = QFileDialog.getSaveFileName(self, "Sla Afbeelding Op", "", "PNG Afbeeldingen (*.png);;JPEG Afbeeldingen (*.jpg)")
        if not file_path: return

        try:
            frame_pil = self._capture_and_crop_frame()
            if frame_pil:
                if file_path.lower().endswith(('.jpg', '.jpeg')):
                    background = Image.new("RGB", frame_pil.size, (255, 255, 255))
                    background.paste(frame_pil, (0, 0), frame_pil)
                    frame_pil = background
                frame_pil.save(file_path)
                
                self.show_status_message(f"Afbeelding opgeslagen naar {os.path.basename(file_path)}")
                QMessageBox.information(self, "Opslaan Voltooid", f"Afbeelding opgeslagen als {os.path.basename(file_path)}")
            else:
                raise ValueError("Kon de afbeelding niet correct vastleggen.")
        except Exception as e:
            self.show_status_message(f"Fout bij opslaan van afbeelding: {e}")
            QMessageBox.critical(self, "Opslaan Mislukt", f"Er is een fout opgetreden:\n{e}")

    def export_video(self):
        if not self.image_item and not self.actions:
            QMessageBox.warning(self, "Export Fout", "Geen afbeelding of lijnen geladen om te exporteren!")
            return

        file_path, _ = QFileDialog.getSaveFileName(self, "Sla MP4 op", "", "MP4 Bestanden (*.mp4)")
        if not file_path: return
        
        duration = 5
        fps = 30
        watermark_path = os.path.join(script_dir, "images", "pulseline1.png")
        watermark_image = None
        
        try:
            watermark_image = Image.open(watermark_path).convert("RGBA")
        except Exception as e:
            self.show_status_message(f"WAARSCHUWING: Kon watermerk niet laden: {e}.")

        self.timer.stop()
        
        frames_written = 0
        total_frames = duration * fps
        
        try:
            with imageio.get_writer(file_path, fps=fps, codec='h264', quality=8) as writer:
                for i in range(total_frames):
                    self.update_drawing()
                    QApplication.processEvents()
                    
                    frame_pil = self._capture_and_crop_frame()
                    if not frame_pil:
                        self.show_status_message(f"Frame {i+1}/{total_frames} mislukt, wordt overgeslagen.")
                        continue

                    base_image_rgba = frame_pil.convert('RGBA')

                    if watermark_image:
                        img_width, img_height = base_image_rgba.size
                        wm_width, wm_height = watermark_image.size
                        
                        max_wm_width = int(img_width * 0.2)
                        if wm_width > max_wm_width:
                            ratio = max_wm_width / wm_width
                            wm_width = max_wm_width
                            wm_height = int(wm_height * ratio)
                            watermark_resized = watermark_image.resize((wm_width, wm_height), Image.LANCZOS)
                        else:
                            watermark_resized = watermark_image

                        position = (10, img_height - watermark_resized.height - 10)
                        
                        txt_layer = Image.new('RGBA', base_image_rgba.size, (255,255,255,0))
                        txt_layer.paste(watermark_resized, position, watermark_resized)
                        
                        final_frame = Image.alpha_composite(base_image_rgba, txt_layer)
                    else:
                        final_frame = base_image_rgba

                    writer.append_data(np.array(final_frame.convert('RGB')))
                    frames_written += 1
                    self.show_status_message(f"Exporteren: {frames_written}/{total_frames} frames...")
                
            if frames_written > 0:
                self.show_status_message(f"Export naar {os.path.basename(file_path)} voltooid!")
                QMessageBox.information(self, "Export Voltooid", f"Video opgeslagen als {os.path.basename(file_path)}")
            else:
                self.show_status_message("Export mislukt: geen frames vastgelegd.")
                QMessageBox.critical(self, "Export Mislukt", "Kon geen frames vastleggen.")
                if os.path.exists(file_path): os.remove(file_path)

        except Exception as e:
            self.show_status_message(f"Fout bij opslaan van MP4: {e}")
            QMessageBox.critical(self, "Fout bij Exporteren", f"Er is een fout opgetreden:\n{e}\nZorg ervoor dat 'imageio-ffmpeg' is geïnstalleerd.")
        finally:
            self.timer.start(10) # Start de timer opnieuw met 10ms interval


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = LEDVisualizer()
    ex.show()
    sys.exit(app.exec_())
