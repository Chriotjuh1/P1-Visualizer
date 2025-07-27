import sys
import math
import time
import copy
import random
import os
import numpy as np
import cv2
import imageio
import uuid # For generating unique IDs
import re # For regex in stylesheet parsing

# Add the script's directory to sys.path so modules can be found
# This is crucial if the script is not run from the project's root folder.
script_dir = os.path.abspath(os.path.dirname(__file__)) # Use absolute path
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

# print(f"DEBUG: script_dir: {script_dir}") # Debug output, can be commented out
# print(f"DEBUG: sys.path after addition: {sys.path}") # Debug output, can be commented out

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QSlider, QComboBox, QFileDialog, QColorDialog, QApplication, QMessageBox,
    QStatusBar, QGroupBox, QSizePolicy, QProgressDialog
)
from PyQt5.QtCore import Qt, QTimer, QEvent, QSize, QRectF
from PyQt5.QtGui import QMouseEvent, QIcon, QImage, QPixmap, QPainter, QColor
import pyqtgraph as pg
from pyqtgraph.exporters import ImageExporter
from PIL import Image

# Enable OpenGL for smoother rendering and anti-aliasing
pg.setConfigOptions(useOpenGL=True)

# --- Try to import the actual utility and effect files ---
try:
    # IMPORTANT NOTE: Make sure the 'effects' folder is a valid Python package
    # (i.e., it contains an empty or initial '__init__.py' file).
    # Also check if the method names in your effect files (e.g., effects/base_effect.py,
    # effects/static.py, effects/breathing.py) all use 'get_next_frame' (snake_case)
    # instead of 'getNextFrame' (camelCase). This is crucial for functionality.
    from effects.schemas import ( # Adjusted import path
        EffectModel, StaticParams, BreathingParams, Color,
        KnightRiderParams, MeteorParams, MulticolorParams,
        RunningLineParams, ChristmasSnowParams, FlagParams
    )
    from effects.effects import Effects # Adjusted import path
    from effects.breathing import BreathingEffect # Adjusted import path
    from effects.knight_rider import KnightRiderEffect # Adjusted import path
    from effects.meteor import MeteorEffect # Adjusted import path
    from effects.multicolor import MulticolorEffect # Adjusted import path
    from effects.running_line import RunningLineEffect # Adjusted import path
    from effects.christmas_snow import ChristmasSnowEffect # Adjusted import path
    from effects.flag import FlagEffect # Adjusted import path
    from effects.static import StaticEffect # Adjusted import path
    
    from utils import distance, resample_points, smooth_points, point_line_distance # Adjusted import path
    from effects.converts import rgb_to_rgbw # Adjusted import path
    print("INFO: Actual 'utils' and 'effects' modules loaded.")

    # Mapping of effect names to their classes
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
    print(f"WARNING: Could not find actual 'utils' and 'effects' modules: {e}. Fallback to dummy implementations.")
    # Dummy implementations for development without full modules
    def distance(p1, p2): return math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)
    def resample_points(points, interval):
        if len(points) < 2: return points
        # For dummy: simple resampling, can be improved later
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
                new_y = points[i][1] + t * (points[i+1][1] - points[i][1]) # Corrected line
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
    def rgb_to_rgbw(r, g, b): return int(r), int(g), int(b), 0 # Ensure they are integers
    
    # Dummy classes for effects and schemas
    class Color:
        # Adjusted to accept keyword arguments for consistency
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
        def __init__(self, color, brightness, meteor_width, spark_intensity): self.color, self.brightness, self.meteor_width, self.spark_intensity = color, brightness, spark_intensity
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
            self.current_frame = 0.0 # Initialize current_frame in the base class

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
            self.frame_counter = 0.0 # Initialize frame_counter

        def get_next_frame(self):
            line_length = self.params.line_length
            r, g, b = self.params.color[0].red, self.params.color[0].green, self.params.color[0].blue
            brightness_factor = self.params.brightness / 100
            
            frame = [[0, 0, 0, 0]] * self.num_leds

            # Update the Knight Rider position based on FPS
            advance_steps = self.fps / 33.0 # Use 33.0 as base for visualizer's FPS
            self.frame_counter += advance_steps

            if self.frame_counter >= 1.0:
                steps_to_take = int(self.frame_counter)
                self.frame_counter -= steps_to_take
                
                for _ in range(steps_to_take):
                    if self.moving_right:
                        self.position += 1
                        if self.position + line_length >= self.num_leds:
                            self.moving_right = False
                            self.position = self.num_leds - line_length - 1
                            if self.position < 0: self.position = 0 # Ensure it doesn't go negative if line_length is large
                    else:
                        self.position -= 1
                        if self.position <= 0:
                            self.moving_right = True
                            self.position = 0
            
            # Draw the main line
            main_color = rgb_to_rgbw(int(r * brightness_factor), int(g * brightness_factor), int(b * brightness_factor))
            for i in range(line_length):
                led_pos = (self.position + i)
                if 0 <= led_pos < self.num_leds:
                    frame[led_pos] = main_color

            # Draw the fading tail
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

                # Fade on the left side
                prev_pos = self.position - fade
                if 0 <= prev_pos < self.num_leds:
                    # Only overwrite if the fading color is brighter (or equal) than existing
                    # This prevents overwriting the main line with a weaker fade
                    if frame[prev_pos][0] < final_faded_color[0] or frame[prev_pos][1] < final_faded_color[1] or frame[prev_pos][2] < final_faded_color[2]:
                        frame[prev_pos] = final_faded_color
                
                # Fade on the right side (behind the main line)
                next_pos = self.position + line_length + fade - 1
                if 0 <= next_pos < self.num_leds:
                    if frame[next_pos][0] < final_faded_color[0] or frame[next_pos][1] < final_faded_color[1] or frame[next_pos][2] < final_faded_color[2]:
                        frame[next_pos] = final_faded_color

            return frame

    class DummyMeteorEffect(Effects):
        def __init__(self, model):
            super().__init__(model)
            self.max_sparkle_duration = 100
            self.frame_counter = 0.0 # Use float for more precision
            self._on_num_leds_change()

        def _on_num_leds_change(self):
            """Reset the status when the number of LEDs changes."""
            self.position = float(self.num_leds - 1)
            self.sparkles = {}

        def get_next_frame(self):
            # --- State Update Logic (throttled by speed/fps) ---
            
            # The visualizer's timer runs at ~33 FPS (30ms).
            # self.fps is the target speed from the slider (e.g., 6 to 150).
            # Calculate how many steps the animation should advance this frame.
            advance_steps = self.fps / 33.0
            self.frame_counter += advance_steps

            if self.frame_counter >= 1.0:
                steps_to_take = int(self.frame_counter)
                self.frame_counter -= steps_to_take
                
                for _ in range(steps_to_take):
                    self.position -= 1

                    # Reset logic: reset if the meteor + tail is completely off screen
                    if self.position + self.params.meteor_width < -self.max_sparkle_duration:
                        self.position = float(self.num_leds - 1)
                        self.sparkles.clear()

                    # Sparkle creation
                    sparkle_index = int(self.position) + self.params.meteor_width
                    if 0 <= sparkle_index < self.num_leds:
                        if random.randint(0, 100) < self.params.spark_intensity:
                            self.sparkles[sparkle_index] = self.max_sparkle_duration

            # --- Drawing Logic (every frame) ---
            frame = [[0, 0, 0, 0]] * self.num_leds
            brightness_factor = self.params.brightness / 100
            r_base = self.params.color[0].red
            g_base = self.params.color[0].green
            b_base = self.params.color[0].blue

            # Draw meteor
            for i in range(self.params.meteor_width):
                led_index = int(self.position) + i
                if 0 <= led_index < self.num_leds:
                    r = int(r_base * brightness_factor)
                    g = int(g_base * brightness_factor)
                    b = int(b_base * brightness_factor)
                    frame[led_index] = rgb_to_rgbw(r, g, b)

            # Draw and fade sparks
            keys_to_delete = []
            for key, value in self.sparkles.items():
                value -= 2 # Fade every frame (a bit faster)
                if value <= 0:
                    keys_to_delete.append(key)
                    continue
                
                sparkle_brightness = value / self.max_sparkle_duration
                sparkle_color_factor = brightness_factor * sparkle_brightness
                
                r = int(r_base * sparkle_color_factor)
                g = int(g_base * sparkle_color_factor)
                b = int(b_base * sparkle_color_factor)
                
                # Ensure the spark does not overwrite a brighter part of the meteor
                if 0 <= key < self.num_leds and (frame[key][0] < r or frame[key][1] < g or frame[key][2] < b):
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
                # IMPORTANT: Integer division here. If self.num_leds is small and self.params.number_of_lines is large,
                # 'gap' can become 0, causing lines to overlap.
                gap = self.num_leds // self.params.number_of_lines
                # print(f"DEBUG (Running Line): num_leds: {self.num_leds}, number_of_lines: {self.params.number_of_lines}, calculated gap: {gap}")
                for i in range(self.params.number_of_lines):
                    current_gap = gap * i
                    for width in range(line_width):
                        idx = (self.pos + current_gap + width) % self.num_leds
                        if 0 <= idx < self.num_leds: # Ensure index is within bounds
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
                # CORRECTION: Remove the double 'brightness' factor.
                # The 'brightness_factor' is already calculated based on self.params.brightness.
                scaled_red = int(color_input.red * brightness_factor)
                scaled_green = int(color_input.green * brightness_factor) 
                scaled_blue = int(color_input.blue * brightness_factor)
                rgbw = rgb_to_rgbw(scaled_red, scaled_green, scaled_blue)
                
                for led_offset in range(flag_width):
                    index = (current_segment_start + led_offset) % self.num_leds
                    frame[index] = rgbw
                current_segment_start = (current_segment_start + flag_width) % self.num_leds
            self.position = (self.position + 1) % self.num_leds
            return frame

    # Dummy get_effect_class function
    _effect_classes = {
        "Static": DummyStaticEffect,
        "Pulseline": DummyBreathingEffect, # Name in UI is Pulseline, class is BreathingEffect
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
    Main window of the LED Visualizer application.
    Provides functionality for loading images, drawing lines,
    applying visual effects, and exporting images/videos.
    """
    def __init__(self, parent=None): # Add parent for better PyQt5 practices
        super().__init__(parent)
        self.setWindowTitle("Pulseline1 Visualizer")
        self.setGeometry(100, 100, 1920, 1080) # Default window size
        
        try:
            self.setWindowIcon(QIcon(os.path.join(script_dir, "icons", "pulseline1.ico")))
        except Exception as e:
            print(f"WARNING: Could not load 'icons/pulseline1.ico': {e}")

        self.original_image = None
        self.image = None
        self.image_item = None

        self.actions = []
        self.current_action = None
        
        # Store the different plot items
        self.line_plot_items = {} # For the bright core of the effects (ScatterPlotItem)
        self.glow_plot_items = {} # NEW: For the glow of the effects (PlotDataItem)
        self.line_data_items = {} # For 'Free Drawing' mode (PlotDataItem)
        self.point_plot_items = {} # For editing points (ScatterPlotItem)
        self.effect_instances = {}

        self.effect_index = 0
        self.default_brightness = 1.0
        self.default_speed = 5
        self.line_width = 5 # Default line width increased for better effect
        self.led_color = (255, 0, 0)

        self.draw_mode = "Vrij Tekenen"
        self.drawing = False
        self.line_drawing_first_click = False
        
        self.selected_action_index = -1
        self.selected_point_index = -1
        self.drag_start_pos = None

        self.undo_stack = []
        self.redo_stack = []

        # New global state for effect parameters
        self.current_global_effect_params = {} 

        self.init_ui()
        self.push_undo_state()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.timer_update)
        self.timer.start(10) # Increased FPS to 100 (10ms interval) for smoother animations

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

        control_layout.addWidget(QLabel("LED Grootte (lijndikte):")) # Custom label
        self.line_width_slider = QSlider(Qt.Horizontal, minimum=1, maximum=20, value=self.line_width)
        # FIX: Connect to a separate method for clarity and to force the update
        self.line_width_slider.valueChanged.connect(self._update_line_width_and_draw)
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
        # Adjusted: Maximum value of speed slider set to 5
        self.speed_slider = QSlider(Qt.Horizontal, minimum=1, maximum=5, value=self.default_speed)
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
        self.show_status_message("Ready to start! Load an image.")

        # Initialize global effect parameters at startup
        self._update_global_effect_params_from_ui() # Read initial values from UI
        self.change_effect() # Call this to set up UI and initial effects
        self.change_mode()
        # self.update_effect_parameters_ui() # This is already called by change_effect

    def show_status_message(self, message):
        self.statusBar.showMessage(message)

    def _update_line_width_and_draw(self, value):
        """Update the line width and force a redraw."""
        self.line_width = value
        # print(f"DEBUG: Line width slider changed to: {self.line_width}")
        self.update_drawing()

    def set_current_action_brightness(self, value):
        brightness_val = value / 100.0
        # Update global brightness
        self.current_global_effect_params['brightness'] = brightness_val

        if self.selected_action_index != -1:
            self.actions[self.selected_action_index]['brightness'] = brightness_val
            self.actions[self.selected_action_index]['reset_effect_state'] = True
            self.show_status_message(f"Brightness of selected line set to {value}%")
        else:
            self.default_brightness = brightness_val # Update default for new lines
            for action in self.actions:
                action['brightness'] = brightness_val
                action['reset_effect_state'] = True
            self.show_status_message(f"Global brightness set to {value}%")
        self.update_drawing()

    def set_current_action_speed(self, value):
        # Update global speed
        self.current_global_effect_params['speed'] = value

        if self.selected_action_index != -1:
            self.actions[self.selected_action_index]['speed'] = value
            self.actions[self.selected_action_index]['reset_effect_state'] = True
            self.show_status_message(f"Speed of selected line set to {value}")
        else:
            self.default_speed = value # Update default for new lines
            for action in self.actions:
                action['speed'] = value
                action['reset_effect_state'] = True
            self.show_status_message(f"Global speed set to {value}")
        self.update_drawing()

    def update_ui_for_selected_action(self):
        self.brightness_slider.blockSignals(True)
        self.speed_slider.blockSignals(True)

        if self.selected_action_index != -1:
            selected_action = self.actions[self.selected_action_index]
            self.brightness_slider.setValue(int(selected_action.get('brightness', self.default_brightness) * 100))
            self.speed_slider.setValue(selected_action.get('speed', self.default_speed))
            self.show_status_message(f"Line {self.selected_action_index + 1} selected.")
            # Update global parameters to match selected line
            self.current_global_effect_params.update({
                'brightness': selected_action.get('brightness', self.default_brightness),
                'speed': selected_action.get('speed', self.default_speed),
                'effect_name': selected_action.get('effect_name', self.effect_combo.currentText())
            })
            # Set the effect combo box to the effect name of the selected line
            idx = self.effect_names.index(self.current_global_effect_params['effect_name'])
            self.effect_combo.blockSignals(True)
            self.effect_combo.setCurrentIndex(idx)
            self.effect_combo.blockSignals(False)
            
        else:
            self.brightness_slider.setValue(int(self.default_brightness * 100))
            self.speed_slider.setValue(self.default_speed)
            self.show_status_message("No line selected. Settings are global.")
            # Update global parameters to match defaults
            self.current_global_effect_params.update({
                'brightness': self.default_brightness,
                'speed': self.default_speed,
                'effect_name': self.effect_combo.currentText()
            })
        
        self.brightness_slider.blockSignals(False)
        self.speed_slider.blockSignals(False)
        
        self.update_effect_parameters_ui() # Update effect-specific UI
        self.update_drawing()

    def timer_update(self):
        self.update_drawing()

    def update_drawing(self, force_next_frame=False):
        # Remove actions that no longer exist
        current_action_ids = {action['id'] for action in self.actions}
        items_to_remove = [action_id for action_id in self.line_plot_items if action_id not in current_action_ids]
        
        for action_id in items_to_remove:
            if action_id in self.line_plot_items:
                self.plot_widget.removeItem(self.line_plot_items[action_id])
                del self.line_plot_items[action_id]
            if action_id in self.glow_plot_items:
                self.plot_widget.removeItem(self.glow_plot_items[action_id])
                del self.glow_plot_items[action_id]
            if action_id in self.line_data_items:
                self.plot_widget.removeItem(self.line_data_items[action_id])
                del self.line_data_items[action_id]
            if action_id in self.point_plot_items:
                self.plot_widget.removeItem(self.point_plot_items[action_id])
                del self.point_plot_items[action_id]
            if action_id in self.effect_instances:
                del self.effect_instances[action_id]

        # Add the temporary action if drawing
        all_actions_to_draw = self.actions[:]
        if self.current_action and len(self.current_action["points"]) > 0 and self.drawing:
            temp_action = copy.deepcopy(self.current_action)
            temp_action['id'] = 'temp_current_action'
            all_actions_to_draw.append(temp_action)

        for action_idx, action in enumerate(all_actions_to_draw):
            action_id = action.get('id', str(uuid.uuid4()))
            if 'id' not in action: action['id'] = action_id

            pts = action["points"]
            
            # Skip empty or too short lines
            if len(pts) < 1:
                # Ensure all related items are cleaned up
                for item_dict in [self.line_plot_items, self.glow_plot_items, self.line_data_items, self.point_plot_items]:
                    if action_id in item_dict:
                        self.plot_widget.removeItem(item_dict[action_id])
                        del item_dict[action_id]
                if action_id in self.effect_instances:
                    del self.effect_instances[action_id]
                continue
            
            action_draw_mode = action.get("mode", "Effect")

            if action_draw_mode == "Vrij Tekenen" or action_draw_mode == "Lijn Tekenen":
                # This is a simple line. Remove any effect items.
                if action_id in self.line_plot_items:
                    self.plot_widget.removeItem(self.line_plot_items[action_id])
                    del self.line_plot_items[action_id]
                if action_id in self.glow_plot_items:
                    self.plot_widget.removeItem(self.glow_plot_items[action_id])
                    del self.glow_plot_items[action_id]
                if action_id in self.effect_instances:
                    del self.effect_instances[action_id]

                # Draw as a continuous line (PlotDataItem)
                line_item = self.line_data_items.get(action_id)
                pen = pg.mkPen(QColor(*action["color"]), width=self.line_width, cap=Qt.RoundCap, join=Qt.RoundJoin)
                if not line_item:
                    line_item = pg.PlotDataItem(pen=pen, antialias=True)
                    self.plot_widget.addItem(line_item)
                    self.line_data_items[action_id] = line_item
                else:
                    line_item.setPen(pen)
                line_item.setData(x=[p[0] for p in pts], y=[p[1] for p in pts])

            else: # Apply effect (draw as glow + bright core)
                # This is an effect. Remove any simple line items.
                if action_id in self.line_data_items:
                    self.plot_widget.removeItem(self.line_data_items[action_id])
                    del self.line_data_items[action_id]

                # Determine the current effect and its parameters
                effect_name = action.get('effect_name', self.effect_names[self.effect_combo.currentIndex()])
                EffectClass = get_effect_class(effect_name)
                
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
                    if not (isinstance(flag_widths, list) and all(isinstance(w, (int, float)) for w in flag_widths)):
                        flag_widths = default_flag_widths
                    bg_color_rgb = action.get('background_color', (0,0,0))
                    params_data = {"color": flag_colors, "brightness": int(current_brightness * 100), "width": flag_widths, "background_color": Color(red=bg_color_rgb[0], green=bg_color_rgb[1], blue=bg_color_rgb[2])}
                else:
                    params_data = {"color": [Color(red=r_base, green=g_base, blue=b_base)], "brightness": int(current_brightness * 100)}

                total_line_length = sum(distance(pts[k], pts[k+1]) for k in range(len(pts) - 1))
                num_leds_for_this_line = max(2, int(total_line_length / 2.0)) if total_line_length > 0 else 1

                if action.get('recalculate_resample', True) or action.get('reset_effect_state', True):
                    resampling_interval = total_line_length / (num_leds_for_this_line - 1) if num_leds_for_this_line > 1 else 1.0
                    points_for_effect = resample_points(pts, resampling_interval)
                    action['resampled_points'] = points_for_effect
                    action['num_leds_actual'] = len(points_for_effect)
                    action['recalculate_resample'] = False
                
                num_leds_for_this_line = action.get('num_leds_actual', 1)

                effect_instance = self.effect_instances.get(action_id)
                calculated_fps = int(100 * (current_speed / 5.0)) 
                if not effect_instance or action.get('reset_effect_state', False) or not isinstance(effect_instance, EffectClass):
                    params_instance = ParamsModel(**params_data)
                    model = EffectModel(params=params_instance, frame_skip=0, fps=calculated_fps, num_leds=num_leds_for_this_line) 
                    effect_instance = EffectClass(model)
                    self.effect_instances[action_id] = effect_instance
                    action['reset_effect_state'] = False
                else:
                    effect_instance.params = ParamsModel(**params_data)
                    effect_instance.num_leds = num_leds_for_this_line
                    effect_instance.fps = calculated_fps
                
                if force_next_frame:
                    frame_colors = effect_instance.get_next_frame()
                else:
                    frame_colors = effect_instance.get_next_frame()

                
                # Ensure all colors in frame_colors are 4-element (R, G, B, W)
                # This handles cases where external effect modules might return 3-element (R, G, B)
                processed_frame_colors = []
                for color_tuple in frame_colors:
                    if len(color_tuple) == 3:
                        # Convert RGB to RGBW using the local rgb_to_rgbw
                        processed_frame_colors.append(rgb_to_rgbw(color_tuple[0], color_tuple[1], color_tuple[2]))
                    elif len(color_tuple) == 4:
                        processed_frame_colors.append(color_tuple)
                    else:
                        # Handle unexpected format, e.g., default to black
                        processed_frame_colors.append((0, 0, 0, 0))


                # --- GLOW EFFECT LOGIC ---
                avg_r, avg_g, avg_b = 0, 0, 0
                num_colors = len(processed_frame_colors)
                if num_colors > 0:
                    for r, g, b, w in processed_frame_colors: # <--- This line will now be safe
                        avg_r += r; avg_g += g; avg_b += b
                    avg_r //= num_colors; avg_g //= num_colors; avg_b //= num_colors
                
                glow_item = self.glow_plot_items.get(action_id)
                glow_pen = pg.mkPen(color=(avg_r, avg_g, avg_b, 70), width=self.line_width * 2, cap=Qt.RoundCap, join=Qt.RoundJoin)
                if not glow_item:
                    glow_item = pg.PlotDataItem(pen=glow_pen, antialias=True)
                    self.plot_widget.addItem(glow_item)
                    self.glow_plot_items[action_id] = glow_item
                else:
                    glow_item.setPen(glow_pen)
                glow_item.setData(x=[p[0] for p in pts], y=[p[1] for p in pts])

                # --- BRIGHT CORE LOGIC (ScatterPlot) ---
                brushes = []
                for i in range(len(action['resampled_points'])):
                    # Use processed_frame_colors here
                    r, g, b = (processed_frame_colors[i][0], processed_frame_colors[i][1], processed_frame_colors[i][2]) if i < len(processed_frame_colors) else (0,0,0)
                    brushes.append(pg.mkBrush(QColor(r, g, b)))

                x_coords = [p[0] for p in action['resampled_points']]
                y_coords = [p[1] for p in action['resampled_points']]

                scatter_item = self.line_plot_items.get(action_id)
                if not scatter_item:
                    scatter_item = pg.ScatterPlotItem(
                        x=x_coords, y=y_coords, size=self.line_width, brush=brushes, 
                        antialias=True, pen=pg.mkPen(None)
                    )
                    self.plot_widget.addItem(scatter_item)
                    self.line_plot_items[action_id] = scatter_item
                else:
                    scatter_item.setData(x=x_coords, y=y_coords, size=self.line_width, brush=brushes)
            
            # Draw editing points
            if self.draw_mode == "Lijn Bewerken" and action_idx == self.selected_action_index:
                point_item = self.point_plot_items.get(action_id)
                if not point_item:
                    point_item = pg.ScatterPlotItem(size=self.line_width + 5, brush=pg.mkBrush('b'), pen=pg.mkPen('w', width=1))
                    self.plot_widget.addItem(point_item)
                    self.point_plot_items[action_id] = point_item
                point_item.setData(x=[p[0] for p in pts], y=[p[1] for p in pts])
            else:
                if action_id in self.point_plot_items:
                    self.plot_widget.removeItem(self.point_plot_items[action_id])
                    del self.point_plot_items[action_id]

    def change_effect(self):
        self.effect_index = self.effect_combo.currentIndex()
        selected_effect_name = self.effect_names[self.effect_index]

        self._update_global_effect_params_with_defaults(selected_effect_name)
        
        for action in self.actions:
            action['reset_effect_state'] = True
            action['effect_name'] = selected_effect_name
            if action.get('mode') in ["Vrij Tekenen", "Lijn Tekenen"]:
                action['mode'] = "Effect"
            action.update(copy.deepcopy(self.current_global_effect_params))

        self.show_status_message(f"Effect changed to: {selected_effect_name}")
        self.update_effect_parameters_ui()
        self.update_drawing()

    def choose_led_color(self):
        color = QColorDialog.getColor(QColor(*self.led_color))
        if color.isValid():
            new_color = (color.red(), color.green(), color.blue())
            
            self.led_color = new_color
            
            if self.selected_action_index != -1:
                self.actions[self.selected_action_index]['color'] = new_color
                self.actions[self.selected_action_index]['reset_effect_state'] = True
                self.show_status_message(f"Color of selected line changed to RGB{new_color}")
            else:
                for action in self.actions:
                    action['color'] = new_color
                    action['reset_effect_state'] = True
                self.show_status_message(f"Global LED color changed to RGB{new_color}")
            self.update_drawing()

    def load_image(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Load Image", "", "Images (*.png *.jpg *.jpeg *.bmp)")
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
                self.show_status_message(f"Image '{os.path.basename(file_path)}' loaded.")
            except Exception as e:
                QMessageBox.critical(self, "Load Error", f"Could not load image: {e}")
                self.show_status_message(f"Error loading image: {e}")

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
        for item_dict in [self.line_plot_items, self.glow_plot_items, self.line_data_items, self.point_plot_items]:
            for item in list(item_dict.values()):
                self.plot_widget.removeItem(item)
            item_dict.clear()

        self.effect_instances.clear()
        self.actions.clear()
        self.current_action = None
        self.selected_action_index = -1
        self.selected_point_index = -1
        if push_undo:
            self.push_undo_state()
            self.show_status_message("All lines cleared.")
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
        self.show_status_message("Image cleared.")
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
        self.show_status_message(f"Background darkness set to {value}%")

    def merge_lines(self):
        if len(self.actions) < 2:
            self.show_status_message("At least two lines needed to merge.")
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
                        line1['points'].extend(line2['points']); merged = True
                    elif distance(p1_end, p2_end) < merge_threshold:
                        line1['points'].extend(reversed(line2['points'])); merged = True
                    elif distance(p1_start, p2_end) < merge_threshold:
                        line1['points'] = list(reversed(line1['points'])) + line2['points']; merged = True
                    elif distance(p1_start, p2_start) < merge_threshold:
                        line1['points'] = list(reversed(line1['points'])) + list(reversed(line2['points'])); merged = True
                    
                    if merged:
                        removed_action_id = self.actions[j]['id']
                        for item_dict in [self.line_plot_items, self.glow_plot_items, self.line_data_items, self.point_plot_items]:
                            if removed_action_id in item_dict:
                                self.plot_widget.removeItem(item_dict[removed_action_id])
                                del item_dict[removed_action_id]
                        if removed_action_id in self.effect_instances:
                            del self.effect_instances[removed_action_id]

                        self.actions.pop(j)
                        self.actions[i]['recalculate_resample'] = True 
                        self.actions[i]['mode'] = "Effect"
                        merged_in_pass = True
                        i = -1
                        break
                    else:
                        j += 1
                if i == -1: break
                i += 1
        
        self.update_drawing()
        self.push_undo_state()
        self.show_status_message("Lines merged.")

    def push_undo_state(self):
        state_to_save = []
        for action in self.actions:
            clean_action = {k: v for k, v in action.items() if k not in ['effect_instance', 'plot_items', 'resampled_points']}
            state_to_save.append(copy.deepcopy(clean_action))
        self.undo_stack.append(state_to_save)
        self.redo_stack.clear()

    def undo_action(self):
        if len(self.undo_stack) > 1:
            current_state = self.undo_stack.pop()
            self.redo_stack.append(current_state)
            
            self.clear_all_lines(False) # Simpler way to clean everything up

            previous_state = self.undo_stack[-1]
            self.actions = copy.deepcopy(previous_state)
            
            for action in self.actions:
                action['reset_effect_state'] = True
                action['recalculate_resample'] = True
            
            self.selected_action_index = -1
            self.selected_point_index = -1
            self.update_drawing()
            self.update_ui_for_selected_action()
            self.show_status_message("Action undone.")
        else:
            self.show_status_message("Nothing to undo.")

    def redo_action(self):
        if self.redo_stack:
            restored_state = self.redo_stack.pop()
            self.undo_stack.append(restored_state)

            self.clear_all_lines(False) # Simpler way to clean everything up

            self.actions = copy.deepcopy(restored_state)
            
            for action in self.actions:
                action['reset_effect_state'] = True
                action['recalculate_resample'] = True

            self.selected_action_index = -1
            self.selected_point_index = -1
            self.update_drawing()
            self.update_ui_for_selected_action()
            self.show_status_message("Action redone.")
        else:
            self.show_status_message("Nothing to redo.")
    
    def rotate_image(self, angle):
        if self.original_image is None:
            self.show_status_message("No image loaded to rotate.")
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
            self.show_status_message(f"Image rotated {angle} degrees.")
        except Exception as e:
            QMessageBox.critical(self, "Rotation Error", f"Error rotating image: {e}")
            self.show_status_message(f"Error rotating image: {e}")


    def change_mode(self):
        self.draw_mode = self.mode_combo.currentText()
        self.selected_action_index = -1
        self.selected_point_index = -1
        self.line_drawing_first_click = False
        self.update_ui_for_selected_action()
        self.update_drawing()
        self.show_status_message(f"Drawing mode changed to: {self.draw_mode}")

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
    
    def _get_current_ui_effect_params(self):
        """
        Retrieves the current values of the effect-specific UI elements.
        This method reads directly from the UI elements.
        """
        params = {}
        selected_effect_name = self.effect_combo.currentText()

        # Retrieve global brightness and speed (these are always present)
        params['brightness'] = self.brightness_slider.value() / 100.0
        params['speed'] = self.speed_slider.value()

        # Retrieve effect-specific parameters
        if selected_effect_name == "Knight Rider":
            params['line_length'] = self.current_effect_ui_elements.get('line_length', QSlider()).value()
        elif selected_effect_name == "Meteor":
            params['meteor_width'] = self.current_effect_ui_elements.get('meteor_width', QSlider()).value()
            params['spark_intensity'] = self.current_effect_ui_elements.get('spark_intensity', QSlider()).value()
        elif selected_effect_name == "Running Line":
            params['line_width'] = self.current_effect_ui_elements.get('line_width', QSlider()).value()
            params['number_of_lines'] = self.current_effect_ui_elements.get('number_of_lines', QSlider()).value()
            
            bg_button = self.current_effect_ui_elements.get('background_color')
            if bg_button:
                style = bg_button.styleSheet()
                match = re.search(r'rgb\((\d+),(\d+),(\d+)\)', style)
                if match:
                    params['background_color'] = (int(match.group(1)), int(match.group(2)), int(match.group(3)))
                else:
                    params['background_color'] = (0,0,0) # Default if not found
            else:
                params['background_color'] = (0,0,0) # Default if button does not exist
                
        elif selected_effect_name == "Christmas Snow":
            params['red_chance'] = self.current_effect_ui_elements.get('red_chance', QSlider()).value()
            params['dark_green_chance'] = self.current_effect_ui_elements.get('dark_green_chance', QSlider()).value()
        elif selected_effect_name == "Flag":
            colors = []
            widths = []
            for i in range(3):
                color_button = self.current_effect_ui_elements.get(f'color_{i}')
                if color_button:
                    style = color_button.styleSheet()
                    match = re.search(r'rgb\((\d+),(\d+),(\d+)\)', style)
                    if match:
                        colors.append((int(match.group(1)), int(match.group(2)), int(match.group(3))))
                width_slider = self.current_effect_ui_elements.get(f'width_{i}')
                if width_slider:
                    widths.append(width_slider.value())
            if colors: params['color'] = colors
            if widths: params['width'] = widths

            bg_button = self.current_effect_ui_elements.get('background_color')
            if bg_button:
                style = bg_button.styleSheet()
                match = re.search(r'rgb\((\d+),(\d+),(\d+)\)', style)
                if match:
                    params['background_color'] = (int(match.group(1)), int(match.group(2)), int(match.group(3)))
                else:
                    params['background_color'] = (0,0,0) # Default if not found
            else:
                params['background_color'] = (0,0,0) # Default if button does not exist

        return params

    def _update_global_effect_params_from_ui(self):
        """
        Reads the current values from the UI elements and stores them in
        self.current_global_effect_params.
        """
        self.current_global_effect_params.update(self._get_current_ui_effect_params())
        self.current_global_effect_params['effect_name'] = self.effect_combo.currentText()
        self.current_global_effect_params['color'] = self.led_color # Ensure base LED color is also global

    def _update_global_effect_params_with_defaults(self, effect_name):
        """
        Sets the global effect parameters to the default values for a given effect.
        """
        # Reset to general defaults
        self.current_global_effect_params = {
            'brightness': self.default_brightness,
            'speed': self.default_speed,
            'effect_name': effect_name,
            'color': self.led_color
        }

        # Apply effect-specific defaults
        if effect_name == "Knight Rider":
            self.current_global_effect_params['line_length'] = 10
        elif effect_name == "Meteor":
            self.current_global_effect_params['meteor_width'] = 10
            self.current_global_effect_params['spark_intensity'] = 50
        elif effect_name == "Running Line":
            self.current_global_effect_params['line_width'] = 5
            self.current_global_effect_params['number_of_lines'] = 3
            self.current_global_effect_params['background_color'] = (0,0,0)
        elif effect_name == "Christmas Snow":
            self.current_global_effect_params['red_chance'] = 30
            self.current_global_effect_params['dark_green_chance'] = 30
        elif effect_name == "Flag":
            self.current_global_effect_params['color'] = [(255,0,0), (255,255,255), (0,0,255)]
            self.current_global_effect_params['width'] = [10, 10, 10]
            self.current_global_effect_params['background_color'] = (0,0,0)


    def handle_mouse_press(self, event):
        pos = self.plot_widget.getViewBox().mapSceneToView(event.pos())
        point = (pos.x(), pos.y())

        base_action_data = {
            "id": str(uuid.uuid4()),
            "points": [point],
            "color": self.led_color,
            'reset_effect_state': True,
            'recalculate_resample': True,
            'effect_name': self.current_global_effect_params.get('effect_name', self.effect_combo.currentText()),
            'mode': self.draw_mode
        }
        base_action_data.update(copy.deepcopy(self.current_global_effect_params))


        if self.draw_mode == "Vrij Tekenen":
            self.drawing = True
            self.current_action = base_action_data
            self.show_status_message("Free drawing started.")
        elif self.draw_mode == "Lijn Tekenen":
            if not self.line_drawing_first_click:
                self.drawing = True
                self.line_drawing_first_click = True
                base_action_data["points"] = [point, point]
                self.current_action = base_action_data
                self.show_status_message("Start point of line selected.")
            else:
                if self.current_action:
                    self.current_action["points"][1] = point
                    self.current_action['mode'] = self.draw_mode
                    self.actions.append(self.current_action)
                    self.push_undo_state()
                    self.show_status_message("Line completed.")
                self.current_action, self.drawing, self.line_drawing_first_click = None, False, False
        elif self.draw_mode == "Lijn Bewerken":
            self.selected_action_index = -1
            self.selected_point_index = -1
            min_dist = float('inf')
            
            click_tolerance = 20 

            for i, action in enumerate(self.actions):
                for j, p in enumerate(action["points"]):
                    dist = distance(point, p)
                    if dist < click_tolerance and dist < min_dist:
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
                
                if min_dist_line < click_tolerance:
                    self.selected_action_index = closest_action_idx
                    self.selected_point_index = -1

            if self.selected_action_index != -1:
                self.drawing = True
                self.drag_start_pos = point
                self.show_status_message(f"Line {self.selected_action_index + 1} selected for editing.")
            else:
                self.show_status_message("No line or point selected.")

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
                    self.current_action['mode'] = self.draw_mode
                    self.actions.append(self.current_action)
                    self.push_undo_state()
                    self.show_status_message("Free drawing completed.")
                else:
                    self.show_status_message("Line too short to save.")
            elif self.draw_mode == "Lijn Bewerken" and self.selected_action_index != -1:
                self.push_undo_state()
                self.show_status_message("Line editing completed.")

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
        button = QPushButton("Choose Color")
        button.clicked.connect(lambda: self._choose_effect_color(param_name, button))
        
        initial_color = self.led_color
        if self.selected_action_index != -1:
            selected_action = self.actions[self.selected_action_index]
            if param_name.startswith("color_"):
                color_idx = int(param_name.split('_')[1])
                if 'color' in selected_action:
                    if isinstance(selected_action['color'], list) and len(selected_action['color']) > color_idx:
                        initial_color = selected_action['color'][color_idx]
                    elif isinstance(selected_action['color'], tuple):
                        initial_color = selected_action['color']
            elif param_name == "background_color" and 'background_color' in selected_action and isinstance(selected_action['background_color'], tuple):
                initial_color = selected_action['background_color']
        elif self.drawing and self.current_action:
            current_drawing_action = self.current_action
            if param_name.startswith("color_"):
                color_idx = int(param_name.split('_')[1])
                if 'color' in current_drawing_action:
                    if isinstance(current_drawing_action['color'], list) and len(current_drawing_action['color']) > color_idx:
                        initial_color = current_drawing_action['color'][color_idx]
                    elif isinstance(current_drawing_action['color'], tuple):
                        initial_color = current_drawing_action['color']
            elif param_name == "background_color" and 'background_color' in current_drawing_action and isinstance(current_drawing_action['background_color'], tuple):
                initial_color = current_drawing_action['background_color']
        else:
            if param_name.startswith("color_"):
                color_idx = int(param_name.split('_')[1])
                if 'color' in self.current_global_effect_params and isinstance(self.current_global_effect_params['color'], list) and len(self.current_global_effect_params['color']) > color_idx:
                    initial_color = self.current_global_effect_params['color'][color_idx]
                elif 'color' in self.current_global_effect_params and isinstance(self.current_global_effect_params['color'], tuple):
                    initial_color = self.current_global_effect_params['color']
            elif param_name == "background_color" and 'background_color' in self.current_global_effect_params and isinstance(self.current_global_effect_params['background_color'], tuple):
                initial_color = self.current_global_effect_params['background_color']


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
                if 'color' in selected_action:
                    if isinstance(selected_action['color'], list) and len(selected_action['color']) > color_idx:
                        current_color_rgb = selected_action['color'][color_idx]
                    elif isinstance(selected_action['color'], tuple):
                        current_color_rgb = selected_action['color']
            elif param_name == "background_color" and 'background_color' in selected_action and isinstance(selected_action['background_color'], tuple):
                current_color_rgb = selected_action['background_color']
        elif self.drawing and self.current_action:
            current_drawing_action = self.current_action
            if param_name.startswith("color_"):
                color_idx = int(param_name.split('_')[1])
                if 'color' in current_drawing_action:
                    if isinstance(current_drawing_action['color'], list) and len(current_drawing_action['color']) > color_idx:
                        current_color_rgb = current_drawing_action['color'][color_idx]
                    elif isinstance(current_drawing_action['color'], tuple):
                        current_color_rgb = current_drawing_action['color']
            elif param_name == "background_color" and 'background_color' in current_drawing_action and isinstance(current_drawing_action['background_color'], tuple):
                current_color_rgb = current_drawing_action['background_color']
        else:
            if param_name.startswith("color_"):
                color_idx = int(param_name.split('_')[1])
                if 'color' in self.current_global_effect_params and isinstance(self.current_global_effect_params['color'], list) and len(self.current_global_effect_params['color']) > color_idx:
                    current_color_rgb = self.current_global_effect_params['color'][color_idx]
                elif 'color' in self.current_global_effect_params and isinstance(self.current_global_effect_params['color'], tuple):
                    current_color_rgb = self.current_global_effect_params['color']
            elif param_name == "background_color" and 'background_color' in self.current_global_effect_params and isinstance(self.current_global_effect_params['background_color'], tuple):
                current_color_rgb = self.current_global_effect_params['background_color']

        color = QColorDialog.getColor(QColor(*current_color_rgb))
        if color.isValid():
            new_rgb = (color.red(), color.green(), color.blue())
            button.setStyleSheet(f"background-color: rgb({new_rgb[0]},{new_rgb[1]},{new_rgb[2]});")
            self.set_effect_specific_param(param_name, new_rgb)

    def set_effect_specific_param(self, param_name, value):
        if param_name.startswith("color_"):
            color_idx = int(param_name.split('_')[1])
            if 'color' not in self.current_global_effect_params or not isinstance(self.current_global_effect_params['color'], list):
                self.current_global_effect_params['color'] = [(255,255,255)] * 3
            while len(self.current_global_effect_params['color']) <= color_idx:
                self.current_global_effect_params['color'].append((255,255,255))
            self.current_global_effect_params['color'][color_idx] = value
        elif param_name.startswith("width_"):
            width_idx = int(param_name.split('_')[1])
            if 'width' not in self.current_global_effect_params or not isinstance(self.current_global_effect_params['width'], list):
                self.current_global_effect_params['width'] = [10] * 3
            while len(self.current_global_effect_params['width']) <= width_idx:
                self.current_global_effect_params['width'].append(10)
            self.current_global_effect_params['width'][width_idx] = value
        else:
            self.current_global_effect_params[param_name] = value

        actions_to_update = []
        
        if self.selected_action_index != -1:
            actions_to_update.append(self.actions[self.selected_action_index])
            self.show_status_message(f"Parameter '{param_name}' of selected line set to: {value}")
        elif self.drawing and self.current_action:
            actions_to_update.append(self.current_action)
            self.show_status_message(f"Parameter '{param_name}' of drawing line set to: {value}")
        else:
            actions_to_update = self.actions
            self.show_status_message(f"Global parameter '{param_name}' set to: {value} for all lines.")

        if not actions_to_update:
            self.update_drawing()
            return

        for target_action in actions_to_update:
            target_action['effect_name'] = self.effect_combo.currentText()
            target_action.update(copy.deepcopy(self.current_global_effect_params))
            target_action['reset_effect_state'] = True

        self.update_drawing()

    def update_effect_parameters_ui(self):
        for i in reversed(range(self.effect_params_layout.count())):
            widget = self.effect_params_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)
                widget.deleteLater()
        self.current_effect_ui_elements.clear()

        selected_effect_name = self.effect_combo.currentText()
        
        params_to_display = {}
        if self.selected_action_index != -1:
            params_to_display = self.actions[self.selected_action_index]
        else:
            params_to_display = self.current_global_effect_params

        if selected_effect_name == "Knight Rider":
            default_val = params_to_display.get('line_length', 10) 
            slider = self._add_slider("Line Length", "line_length", 1, 50, default_val)
            slider.blockSignals(True); slider.setValue(default_val); slider.blockSignals(False)
        
        elif selected_effect_name == "Meteor":
            default_meteor_width = params_to_display.get('meteor_width', 10)
            slider_width = self._add_slider("Meteor Width", "meteor_width", 1, 50, default_meteor_width)
            slider_width.blockSignals(True); slider_width.setValue(default_meteor_width); slider_width.blockSignals(False)

            default_spark_intensity = params_to_display.get('spark_intensity', 50)
            slider_spark = self._add_slider("Spark Intensity", "spark_intensity", 0, 100, default_spark_intensity)
            slider_spark.blockSignals(True); slider_spark.setValue(default_spark_intensity); slider_spark.blockSignals(False)
        
        elif selected_effect_name == "Running Line":
            default_line_width = params_to_display.get('line_width', 5)
            slider_line_width = self._add_slider("Line Width", "line_width", 1, 20, default_line_width)
            slider_line_width.blockSignals(True); slider_line_width.setValue(default_line_width); slider_line_width.blockSignals(False)

            default_num_lines = params_to_display.get('number_of_lines', 3)
            slider_num_lines = self._add_slider("Number of Lines", "number_of_lines", 1, 10, default_num_lines)
            slider_num_lines.blockSignals(True); slider_num_lines.setValue(default_num_lines); slider_num_lines.blockSignals(False)

            color_button = self._add_color_picker("Background Color", "background_color")
            bg_color_rgb = params_to_display.get('background_color', (0,0,0))
            color_button.setStyleSheet(f"background-color: rgb({bg_color_rgb[0]},{bg_color_rgb[1]},{bg_color_rgb[2]});")
        
        elif selected_effect_name == "Christmas Snow":
            default_red_chance = params_to_display.get('red_chance', 30)
            slider_red_chance = self._add_slider("Red Chance (%)", "red_chance", 0, 100, default_red_chance)
            slider_red_chance.blockSignals(True); slider_red_chance.setValue(default_red_chance); slider_red_chance.blockSignals(False)

            default_dark_green_chance = params_to_display.get('dark_green_chance', 30)
            slider_dark_green_chance = self._add_slider("Dark Green Chance (%)", "dark_green_chance", 0, 100, default_dark_green_chance)
            slider_dark_green_chance.blockSignals(True); slider_dark_green_chance.setValue(default_dark_green_chance); slider_dark_green_chance.blockSignals(False)
        
        elif selected_effect_name == "Flag":
            default_colors = params_to_display.get('color')
            if not isinstance(default_colors, list) or not all(isinstance(c, (list, tuple)) for c in default_colors):
                default_colors = [(255,0,0), (255,255,255), (0,0,255)]
            
            default_widths = params_to_display.get('width')
            if not isinstance(default_widths, list) or not all(isinstance(w, (int, float)) for w in default_widths):
                default_widths = [10, 10, 10]

            for i in range(3):
                color_button = self._add_color_picker(f"Color {i+1}", f"color_{i}")
                current_color_rgb = default_colors[i] if i < len(default_colors) else (255,255,255)
                color_button.setStyleSheet(f"background-color: rgb({current_color_rgb[0]},{current_color_rgb[1]},{current_color_rgb[2]});")

                current_width = default_widths[i] if i < len(default_widths) else 10
                slider_width = self._add_slider(f"Width {i+1}", f"width_{i}", 1, 50, current_width)
                slider_width.blockSignals(True); slider_width.setValue(current_width); slider_width.blockSignals(False)
            
            bg_button = self._add_color_picker("Background Color", "background_color")
            bg_color_rgb = params_to_display.get('background_color', (0,0,0))
            bg_button.setStyleSheet(f"background-color: rgb({bg_color_rgb[0]},{bg_color_rgb[1]},{bg_color_rgb[2]});")


   
    
    def _capture_and_crop_frame(self):
        """
        Legt een screenshot van de plot vast en exporteert deze.
        Deze functie past dynamisch de weergave aan de inhoud (afbeelding + lijnen) aan
        en legt vervolgens het frame vast, zodat de exportresolutie volledig gevuld is.
        Eventuele lege ruimte wordt gevuld met een zwarte achtergrond.
        """
        if not self.image_item and not self.actions:
            QMessageBox.warning(self, "Export Fout", "Geen afbeelding of lijnen geladen om te exporteren!")
            return None

        QApplication.processEvents()

        # Dynamisch aanpassen van exportbreedte en -hoogte aan de afbeelding
        # Dit definieert de *doelresolutie* van de output video/afbeelding
        if self.original_image is not None:
            img_height, img_width, _ = self.original_image.shape
            EXPORT_WIDTH = img_width
            EXPORT_HEIGHT = img_height
        else:
            # Fallback naar standaardresolutie als er geen afbeelding is geladen
            EXPORT_WIDTH = 1920
            EXPORT_HEIGHT = 1080

        target_qimage_size = QSize(EXPORT_WIDTH, EXPORT_HEIGHT)

        # Creëer een QPixmap direct en vul deze met zwart
        pixmap = QPixmap(target_qimage_size)
        pixmap.fill(QColor(0, 0, 0)) # Vul de QPixmap expliciet met zwart

        painter = QPainter(pixmap) # Teken op de QPixmap
        
        view_box = self.plot_widget.getViewBox()
        plot_item = self.plot_widget.getPlotItem() # Haal het plotItem op
        
        original_x_range, original_y_range = view_box.viewRange() # Bewaar het originele weergavebereik

        try:
            painter.setRenderHint(QPainter.Antialiasing)
            scene = plot_item.scene() # Gebruik plot_item.scene() direct

            # Bepaal de initiële inhoudsgrenzen op basis van de afbeelding (indien aanwezig)
            if self.original_image is not None:
                # Gebruik de afmetingen van de geladen afbeelding als startpunt
                content_x_min, content_x_max = 0.0, float(img_width)
                content_y_min, content_y_max = 0.0, float(img_height)
            else:
                # Als er geen afbeelding is, begin dan met een lege set coördinaten
                content_x_min, content_x_max = float('inf'), float('-inf')
                content_y_min, content_y_max = float('inf'), float('-inf')

            # Breid de grenzen uit met alle lijnpunten
            for action in self.actions:
                for p in action['points']:
                    content_x_min = min(content_x_min, p[0])
                    content_x_max = max(content_x_max, p[0])
                    content_y_min = min(content_y_min, p[1])
                    content_y_max = max(content_y_max, p[1])
            
            # Als er nog steeds geen inhoud is (geen afbeelding en geen lijnen), retourneer None
            if content_x_min == float('inf') or content_y_min == float('inf'):
                return None

            # Voeg GEEN buffermarge toe voor "Fill Screen" om maximale vulling te garanderen
            buffer_pixel_margin = 0 # <-- Gewijzigd naar 0
            
            content_x_min -= buffer_pixel_margin
            content_x_max += buffer_pixel_margin
            content_y_min -= buffer_pixel_margin
            content_y_max += buffer_pixel_margin

            content_width = content_x_max - content_x_min
            content_height = content_y_max - content_y_min
            
            # Zorg ervoor dat de inhoudsbreedte en -hoogte niet nul of negatief zijn
            if content_width <= 0: content_width = 1.0 # Minimum 1 pixel
            if content_height <= 0: content_height = 1.0 # Minimum 1 pixel

            # Bereken de schaalfactor om de inhoud in de exportafmetingen te vullen.
            # We gebruiken 'max' om ervoor te zorgen dat de video volledig gevuld is,
            # wat zal resulteren in bijsnijden als de beeldverhouding van de inhoud
            # niet overeenkomt met de beeldverhouding van de exportresolutie.
            scale_x = EXPORT_WIDTH / content_width
            scale_y = EXPORT_HEIGHT / content_height
            scale = max(scale_x, scale_y) # Dit is de "Fill Screen" logica

            # Bereken de werkelijke weergaveafmetingen (in de plot-coördinaten) die nodig zijn
            # om de geschaalde inhoud te bevatten en de exportbeeldverhouding te vullen.
            view_width = EXPORT_WIDTH / scale
            view_height = EXPORT_HEIGHT / scale

            # Centreer de inhoud binnen de berekende weergaveafmetingen
            center_x = content_x_min + content_width / 2
            center_y = content_y_min + content_height / 2

            final_x_min = center_x - view_width / 2
            final_x_max = center_x + view_width / 2
            final_y_min = center_y - view_height / 2
            final_y_max = center_y + view_height / 2

            # Stel de view box in op het berekende bereik
            view_box.setRange(xRange=(final_x_min, final_x_max), yRange=(final_y_min, final_y_max), padding=0)

            # Render de scène naar de QPixmap
            scene.render(painter, QRectF(pixmap.rect()), view_box.viewRect())

        finally:
            painter.end()
            # Herstel het originele weergavebereik.
            view_box.setRange(xRange=original_x_range, yRange=original_y_range, padding=0)
            self.update_drawing() # Zorg ervoor dat de liveweergave correct wordt bijgewerkt na herstel

        # Converteer QPixmap naar QImage, en vervolgens naar NumPy array
        qimage_result = pixmap.toImage()
        if qimage_result.isNull():
            print("WAARSCHUWING: Renderen van de scène naar QImage mislukt.")
            return None

        buffer = qimage_result.constBits()
        buffer.setsize(qimage_result.sizeInBytes())
        arr = np.frombuffer(buffer, dtype=np.uint8).reshape((qimage_result.height(), qimage_result.width(), 4))
        
        arr_rgba = cv2.cvtColor(arr, cv2.COLOR_BGRA2RGBA)
        pil_image = Image.fromarray(arr_rgba, 'RGBA')

        return pil_image



    
    def save_image(self):
        if self.plot_widget:
            try:
                self.plot_widget.getViewBox().autoRange(padding=0.0)

                exporter = ImageExporter(self.plot_widget.plotItem)
                exporter.params['width'] = 1920
                exporter.params['height'] = 1080

                file_path, _ = QFileDialog.getSaveFileName(self, "Save Image", "", "PNG Files (*.png)")
                if file_path:
                    if not file_path.lower().endswith('.png'):
                        file_path += '.png'
                    exporter.export(file_path)
                    self.show_status_message(f"Image saved as {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Export Error", f"Failed to save image: {e}")


    def export_video(self):
        import os
        import cv2
        import numpy as np

        if self.original_image is None:
            self.show_status_message("Geen afbeelding geladen.")
            return

        # Resolutie gebaseerd op originele afbeelding
        height, width, _ = self.original_image.shape
        export_width = width
        export_height = height

        # Video-instellingen
        fps = 30
        duration_seconds = 10
        total_frames = fps * duration_seconds

        # Effect-snelheid aanpassen aan sliderwaarde
        effect_update_interval_ms = 1000 / max(1, self.default_speed)  # bijv. 500 ms bij speed 2
        video_frame_interval_ms = 1000 / fps                           # bijv. 33.3 ms
        frames_per_effect_step = max(1, round(effect_update_interval_ms / video_frame_interval_ms))

        # Bestemming kiezen
        output_path, _ = QFileDialog.getSaveFileName(self, "Export Video", "", "MP4 Files (*.mp4)")
        if not output_path:
            return

        # Voortgangsvenster
        progress = QProgressDialog("Video wordt geëxporteerd...", "Annuleren", 0, total_frames, self)
        progress.setWindowTitle("Exporteren")
        progress.setWindowModality(Qt.WindowModal)
        progress.setAutoClose(False)
        progress.setAutoReset(False)
        progress.setMinimumWidth(400)
        progress.setMinimumDuration(0)
        progress.show()
        QApplication.processEvents()

        # Video-writer instellen
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        video_writer = cv2.VideoWriter(output_path, fourcc, fps, (export_width, export_height))

        # Video opbouwen frame per frame
        for frame_idx in range(total_frames):
            if progress.wasCanceled():
                video_writer.release()
                if os.path.exists(output_path):
                    os.remove(output_path)
                self.show_status_message("Export geannuleerd.")
                return

            # Effect updaten op basis van snelheid
            if frame_idx % frames_per_effect_step == 0:
                self.update_drawing(force_next_frame=True)

            # Render het frame exact zoals zichtbaar in UI
            frame = self.render_frame_to_image(export_width, export_height)

            # RGBA naar BGR voor OpenCV
            if frame.shape[2] == 4:
                frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGBA2BGR)
            else:
                frame_bgr = frame

            video_writer.write(frame_bgr)

            progress.setValue(frame_idx + 1)
            QApplication.processEvents()

        # Opschonen en afsluiten
        video_writer.release()
        progress.close()
        self.show_status_message(f"Video geëxporteerd naar: {output_path}")




    def render_frame_to_image(self, width, height):
        from PyQt5.QtGui import QImage, QPainter
        import numpy as np

        self.update_drawing(force_next_frame=True)
        QApplication.processEvents()

        original_size = self.plot_widget.size()
        self.plot_widget.resize(width, height)
        QApplication.processEvents()

        image = QImage(width, height, QImage.Format_RGBA8888)
        image.fill(0)

        painter = QPainter(image)
        self.plot_widget.render(painter)
        painter.end()

        self.plot_widget.resize(original_size)
        QApplication.processEvents()

        ptr = image.bits()
        ptr.setsize(image.byteCount())
        frame = np.array(ptr).reshape((height, width, 4))

        return frame







if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = LEDVisualizer()
    ex.show()
    sys.exit(app.exec_())