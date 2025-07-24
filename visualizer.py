import sys
import math
import time
import copy
import random
import os
import numpy as np
import cv2
import imageio

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QSlider, QComboBox, QFileDialog, QColorDialog, QApplication, QMessageBox
)
from PyQt5.QtCore import Qt, QTimer, QEvent, QSize, QRectF
from PyQt5.QtGui import QMouseEvent, QIcon, QImage, QPixmap, QPainter
import pyqtgraph as pg
from pyqtgraph.exporters import ImageExporter
from PIL import Image

# Schakel OpenGL uit. Dit kan de stabiliteit van de ImageExporter verbeteren,
# omdat OpenGL-rendering soms conflicten kan veroorzaken tijdens het exporteren.
pg.setConfigOptions(useOpenGL=False)

# --- Probeer de echte utility en effect bestanden te importeren ---
try:
    from utils import distance, resample_points, smooth_points, point_line_distance
    from effects.effects import get_effect_class
    from effects.schemas import (
        EffectModel, StaticParams, BreathingParams,
        Color
    )
    from effects.converts import rgb_to_rgbw
    print("INFO: Echte 'utils' en 'effects' modules geladen.")
except ImportError:
    print("WAARSCHUWING: Kon de echte 'utils' en 'effects' modules niet vinden. Fallback naar dummy implementaties.")
    def distance(p1, p2): return math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)
    def resample_points(points, interval):
        if len(points) < 2: return points
        # Dummy implementatie: geeft de punten ongewijzigd terug.
        # Een echte implementatie zou de lijn opnieuw samplen met een vaste interval.
        return points
    def smooth_points(points, window=5): return points
    def point_line_distance(point, p1, p2):
        line_length_sq = distance(p1, p2)**2
        if line_length_sq == 0: return distance(point, p1)
        t = max(0, min(1, (((point[0] - p1[0]) * (p2[0] - p1[0])) + ((point[1] - p1[1]) * (p2[1] - p1[1]))) / line_length_sq))
        closest_point = (p1[0] + t * (p2[0] - p1[0]), p1[1] + t * (p2[1] - p1[1]))
        return distance(point, closest_point)
    def rgb_to_rgbw(r, g, b): return r, g, b, 0
    class Color:
        def __init__(self, red, green, blue): self.red, self.green, self.blue = red, green, blue
    class StaticParams:
        def __init__(self, color, brightness): self.color, self.brightness = color, brightness
    class BreathingParams:
        def __init__(self, color, brightness): self.color, self.brightness = color, brightness
    class EffectModel:
        def __init__(self, params, frame_skip, fps, num_leds): self.params, self.frame_skip, self.fps, self.num_leds = params, frame_skip, fps, num_leds
    class Effects:
        def __init__(self, model: EffectModel):
            self.model, self.params, self.num_leds, self.fps = model, model.params, model.num_leds, model.fps
    class DummyStaticEffect(Effects):
        def get_next_frame(self):
            r, g, b = self.params.color[0].red, self.params.color[0].green, self.params.color[0].blue
            brightness_factor = self.params.brightness / 100.0
            return [(int(r * brightness_factor), int(g * brightness_factor), int(b * brightness_factor), 0)] * self.num_leds
    class BreathingEffect(Effects):
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
    _effect_classes = {"Static": DummyStaticEffect, "Pulseline": BreathingEffect}
    def get_effect_class(effect_name): return _effect_classes.get(effect_name)


class LEDVisualizer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Pulseline1 Visualizer")
        self.setGeometry(100, 100, 1920, 1080)
        # self.setWindowIcon(QIcon("logo.ico"))

        # --- Attributen ---
        self.original_image, self.image, self.image_item = None, None, None
        self.actions, self.current_action = [], None
        self.effect_index = 0
        self.default_brightness, self.default_speed = 1.0, 5
        self.line_width = 3
        self.led_color = (255, 0, 0)
        self.draw_mode = "Vrij Tekenen"
        self.drawing, self.line_drawing_first_click = False, False
        self.selected_action_index, self.selected_point_index = -1, -1
        self.drag_start_pos = None
        self.undo_stack, self.redo_stack = [], []
        self.edit_points_items, self.sliders = [], {}

        self.init_ui()
        self.push_undo_state()

        self.timer = QTimer(self, timeout=self.timer_update)
        self.timer.start(10)

    def init_ui(self):
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        # Maak de PlotWidget aan zonder standaard achtergrond of rand voor een schone export
        self.plot_widget = pg.PlotWidget(background=None, border=None)
        
        # Haal het PlotItem en de ViewBox op voor configuratie
        plot_item = self.plot_widget.getPlotItem()
        view_box = plot_item.getViewBox()

        # Verberg de assen
        plot_item.hideAxis('left')
        plot_item.hideAxis('bottom')

        # Schakel muisinteractie uit en vergrendel de beeldverhouding
        view_box.setMouseEnabled(x=False, y=False)
        view_box.setAspectLocked(True)
        
        # Verwijder alle interne marges om witte randen te voorkomen
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
        control_layout.addWidget(QPushButton("Lijnen Samenvoegen", clicked=self.merge_lines))
        control_layout.addWidget(QLabel("Lijndikte:"))
        self.line_width_slider = QSlider(Qt.Horizontal, minimum=1, maximum=20, value=self.line_width)
        self.line_width_slider.valueChanged.connect(lambda v: setattr(self, 'line_width', v))
        control_layout.addWidget(self.line_width_slider)
        control_layout.addWidget(QPushButton("Kies LED Kleur", clicked=self.choose_led_color))
        control_layout.addWidget(QLabel("Effect:"))
        self.effect_combo = QComboBox()
        self.effect_names = ["Static", "Pulseline"]
        self.effect_combo.addItems(self.effect_names)
        self.effect_combo.currentIndexChanged.connect(self.change_effect)
        control_layout.addWidget(self.effect_combo)
        control_layout.addWidget(QLabel("Helderheid (globaal of per lijn):"))
        self.brightness_slider = QSlider(Qt.Horizontal, minimum=0, maximum=100, value=int(self.default_brightness * 100), singleStep=1)
        self.brightness_slider.valueChanged.connect(self.set_current_action_brightness)
        control_layout.addWidget(self.brightness_slider)
        control_layout.addWidget(QLabel("Snelheid (globaal of per lijn):"))
        self.speed_slider = QSlider(Qt.Horizontal, minimum=1, maximum=50, value=self.default_speed)
        self.speed_slider.valueChanged.connect(self.set_current_action_speed)
        control_layout.addWidget(self.speed_slider)
        
        control_layout.addWidget(QLabel("Achtergrond Donkerheid:"))
        self.darkness_slider = QSlider(Qt.Horizontal, minimum=0, maximum=80, value=0)
        self.darkness_slider.valueChanged.connect(self.update_background_darkness)
        control_layout.addWidget(self.darkness_slider)

        control_layout.addStretch()
        control_layout.addWidget(QPushButton("Sla Afbeelding Op", clicked=self.save_image))
        control_layout.addWidget(QPushButton("Exporteer MP4", clicked=self.export_video))
        control_layout.addWidget(QPushButton("Ongedaan Maken", clicked=self.undo_action))
        control_layout.addWidget(QPushButton("Opnieuw Uitvoeren", clicked=self.redo_action))
        control_layout.addWidget(QPushButton("Roteer Links", clicked=lambda: self.rotate_image(-90)))
        control_layout.addWidget(QPushButton("Roteer Rechts", clicked=lambda: self.rotate_image(90)))
        control_layout.addWidget(QPushButton("Wis Afbeelding", clicked=self.clear_image))
        control_layout.addWidget(QPushButton("Wis Lijnen", clicked=self.clear_everything))
        self.change_effect()
        self.change_mode()

    def set_current_action_brightness(self, value):
        brightness_val = value / 100.0
        if self.selected_action_index != -1:
            self.actions[self.selected_action_index]['brightness'] = brightness_val
        else:
            self.default_brightness = brightness_val
            for action in self.actions:
                action['brightness'] = brightness_val
        self.update_drawing()

    def set_current_action_speed(self, value):
        if self.selected_action_index != -1:
            self.actions[self.selected_action_index]['speed'] = value
        else:
            self.default_speed = value
            for action in self.actions:
                action['speed'] = value
        self.update_drawing()

    def update_ui_for_selected_action(self):
        if self.selected_action_index != -1:
            selected_action = self.actions[self.selected_action_index]
            self.brightness_slider.blockSignals(True); self.speed_slider.blockSignals(True)
            self.brightness_slider.setValue(int(selected_action.get('brightness', self.default_brightness) * 100))
            self.speed_slider.setValue(selected_action.get('speed', self.default_speed))
            self.brightness_slider.blockSignals(False); self.speed_slider.blockSignals(False)
        else:
            self.brightness_slider.blockSignals(True); self.speed_slider.blockSignals(True)
            self.brightness_slider.setValue(int(self.default_brightness * 100))
            self.speed_slider.setValue(self.default_speed)
            self.brightness_slider.blockSignals(False); self.speed_slider.blockSignals(False)
        self.change_effect()

    def timer_update(self):
        self.update_drawing()

    def update_drawing(self):
        for item in self.edit_points_items: self.plot_widget.removeItem(item)
        self.edit_points_items.clear()
        
        all_actions_to_draw = self.actions[:]
        if self.current_action and len(self.current_action["points"]) > 0 and self.drawing:
            all_actions_to_draw.append(self.current_action)

        for action_idx, action in enumerate(all_actions_to_draw):
            pts = action["points"]
            if 'plot_items' not in action: action['plot_items'] = []

            if len(pts) < 2:
                for item in action.get('plot_items', []): self.plot_widget.removeItem(item)
                action['plot_items'] = []
                continue

            base_color = action.get("color", self.led_color)
            total_line_length = sum(distance(pts[k], pts[k+1]) for k in range(len(pts) - 1))
            num_leds_for_this_line = max(10, min(1000, int(total_line_length / 5)))
            num_leds_for_this_line = max(2, num_leds_for_this_line)
            resampling_interval = total_line_length / (num_leds_for_this_line - 1) if num_leds_for_this_line > 1 else 1.0
            points_for_effect = resample_points(pts, resampling_interval) if resampling_interval > 0 else pts
            num_leds_for_this_line = len(points_for_effect)

            effect_name = self.effect_names[self.effect_combo.currentIndex()]
            EffectClass = get_effect_class(effect_name)
            ParamsModel = StaticParams if effect_name == "Static" else BreathingParams

            current_speed = action.get('speed', self.default_speed)
            current_brightness = action.get('brightness', self.default_brightness)
            
            r, g, b = base_color
            params_data = {"color": [Color(red=r, green=g, blue=b)], "brightness": int(current_brightness * 100)}
            
            if 'effect_instance' not in action or not isinstance(action.get('effect_instance'), EffectClass) or action.get('reset_effect_state', False):
                params_instance = ParamsModel(**params_data)
                model = EffectModel(params=params_instance, frame_skip=0, fps=30 * (current_speed / 5.0), num_leds=num_leds_for_this_line)
                action['effect_instance'] = EffectClass(model)
                action['reset_effect_state'] = False
            else:
                action['effect_instance'].params = ParamsModel(**params_data)
                action['effect_instance'].num_leds = num_leds_for_this_line
                action['effect_instance'].fps = 30 * (current_speed / 5.0)

            line_width = self.line_width + 3 if self.draw_mode == "Lijn Bewerken" and action_idx == self.selected_action_index else self.line_width

            if action.get('effect_instance'):
                frame = action['effect_instance'].get_next_frame()
                if frame:
                    r, g, b, w = frame[0]
                    pen = pg.mkPen(color=(r, g, b), width=line_width, antialias=True)
                    all_x, all_y = [p[0] for p in pts], [p[1] for p in pts]
                    if not action['plot_items']:
                        action['plot_items'].append(self.plot_widget.plot(all_x, all_y, pen=pen, connect='all'))
                    else:
                        action['plot_items'][0].setData(all_x, all_y, pen=pen, connect='all')
                
        if self.draw_mode == "Lijn Bewerken" and self.selected_action_index != -1:
            for x, y in self.actions[self.selected_action_index]["points"]:
                point_item = pg.ScatterPlotItem([x], [y], size=10, brush=pg.mkBrush('b'), pen=pg.mkPen('w', width=1))
                self.plot_widget.addItem(point_item)
                self.edit_points_items.append(point_item)

    def change_effect(self):
        self.effect_index = self.effect_combo.currentIndex()
        for action in self.actions: action['reset_effect_state'] = True
        self.update_drawing()

    def choose_led_color(self):
        color = QColorDialog.getColor()
        if color.isValid():
            new_color = (color.red(), color.green(), color.blue())
            if self.selected_action_index != -1:
                self.actions[self.selected_action_index]['color'] = new_color
            else:
                self.led_color = new_color
                for action in self.actions: action['color'] = new_color
            self.update_drawing()

    def load_image(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Afbeelding Laden", "", "Afbeeldingen (*.png *.jpg *.jpeg *.bmp)")
        if file_path:
            self.original_image = np.array(Image.open(file_path).convert("RGBA"))
            self.darkness_slider.setValue(0)
            self.update_background_darkness(0)
            self.clear_everything(clear_image_data=False)
            # Ensure the view box fits the new image
            if self.original_image is not None:
                h, w, _ = self.original_image.shape
                self.plot_widget.getViewBox().setRange(xRange=(0, w), yRange=(0, h), padding=0)
            else:
                self.plot_widget.getViewBox().autoRange()


    def update_display(self):
        if self.image is not None:
            if not self.image_item:
                self.image_item = pg.ImageItem()
                self.plot_widget.addItem(self.image_item)
            # De y-as van pyqtgraph is standaard omgekeerd, dus we draaien de afbeelding om.
            # Echter, ImageItem verwacht data in (rows, cols) format, so (height, width).
            # If the image is (width, height, channels) from PIL, we need to transpose.
            # The original code `np.transpose(np.flipud(self.image), (1, 0, 2))` correctly handles this.
            transposed_image = np.transpose(np.flipud(self.image), (1, 0, 2))
            self.image_item.setImage(transposed_image)
            h, w, _ = self.image.shape
            self.image_item.setRect(0, 0, w, h)
        self.update_drawing()

    def clear_everything(self, clear_image_data=True):
        for action in self.actions:
            for item in action.get('plot_items', []):
                self.plot_widget.removeItem(item)
        self.actions.clear()
        self.current_action = None
        if clear_image_data:
            self.clear_image()
        self.push_undo_state()
        self.update_drawing()
        
    def clear_image(self):
        if self.image_item:
            self.plot_widget.removeItem(self.image_item)
            self.image_item = None
        self.image = None
        self.original_image = None
        self.clear_everything(clear_image_data=False)

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

    def merge_lines(self):
        if len(self.actions) < 2:
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
                        # This logic was incorrect, if p1_start connects to p2_start,
                        # then line1 should be reversed, and then line2 appended as is.
                        line1['points'] = list(reversed(line1['points'])) + line2['points']
                        merged = True
                    if merged:
                        # Verwijder plot items van de samengevoegde lijn
                        for item in self.actions[j].get('plot_items', []):
                            self.plot_widget.removeItem(item)
                        self.actions.pop(j)
                        self.actions[i]['reset_effect_state'] = True
                        merged_in_pass = True
                        i = -1 # Restart outer loop to check for further merges with the newly merged line
                        break
                    else: j += 1
                if i == -1: break
                i += 1
        self.update_drawing()

    def push_undo_state(self):
        state_to_save = []
        for action in self.actions:
            clean_action = {k: v for k, v in action.items() if k not in ['effect_instance', 'plot_items']}
            state_to_save.append(clean_action)
        self.undo_stack.append(copy.deepcopy(state_to_save))
        self.redo_stack.clear()

    def undo_action(self):
        if len(self.undo_stack) > 1:
            current_state = self.undo_stack.pop()
            self.redo_stack.append(current_state)
            for action in self.actions:
                for item in action.get('plot_items', []): self.plot_widget.removeItem(item)
            self.actions = copy.deepcopy(self.undo_stack[-1])
            for action in self.actions:
                action['reset_effect_state'] = True
            self.update_drawing()
            self.update_ui_for_selected_action()

    def redo_action(self):
        if self.redo_stack:
            for action in self.actions:
                for item in action.get('plot_items', []): self.plot_widget.removeItem(item)
            restored_state = self.redo_stack.pop()
            self.undo_stack.append(restored_state)
            self.actions = copy.deepcopy(restored_state)
            for action in self.actions:
                action['reset_effect_state'] = True
            self.update_drawing()
            self.update_ui_for_selected_action()
    
    def rotate_image(self, angle):
        if self.original_image is not None:
            # OpenCV rotate functions: ROTATE_90_CLOCKWISE, ROTATE_90_COUNTERCLOCKWISE, ROTATE_180
            if angle == 90:
                self.original_image = cv2.rotate(self.original_image, cv2.ROTATE_90_CLOCKWISE)
            elif angle == -90:
                self.original_image = cv2.rotate(self.original_image, cv2.ROTATE_90_COUNTERCLOCKWISE)
            # After rotation, the image dimensions might change, so update the viewbox range
            h, w, _ = self.original_image.shape
            self.plot_widget.getViewBox().setRange(xRange=(0, w), yRange=(0, h), padding=0)
            self.update_background_darkness(self.darkness_slider.value())
            # Clear existing lines as their coordinates will be invalid after rotation
            self.clear_everything(clear_image_data=False)


    def change_mode(self):
        self.draw_mode = self.mode_combo.currentText()
        self.selected_action_index = -1
        self.update_ui_for_selected_action()
        self.update_drawing()

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
            self.current_action = {"mode": self.draw_mode, "points": [point], "color": self.led_color, 'speed': self.default_speed, 'brightness': self.default_brightness}
        elif self.draw_mode == "Lijn Tekenen":
            if not self.line_drawing_first_click:
                self.drawing = True
                self.line_drawing_first_click = True
                self.current_action = {"mode": self.draw_mode, "points": [point, point], "color": self.led_color, 'speed': self.default_speed, 'brightness': self.default_brightness}
            else:
                if self.current_action:
                    self.current_action["points"][1] = point
                    self.actions.append(self.current_action)
                    self.push_undo_state()
                self.current_action, self.drawing, self.line_drawing_first_click = None, False, False
        elif self.draw_mode == "Lijn Bewerken":
            self.selected_action_index, self.selected_point_index = -1, -1
            min_dist = float('inf')
            # Selecteer de lijn die het dichtstbij is, niet alleen een punt
            closest_action_idx = -1
            for i, action in enumerate(self.actions):
                for k in range(len(action["points"]) - 1):
                    dist = point_line_distance(point, action["points"][k], action["points"][k+1])
                    if dist < min_dist:
                        min_dist = dist
                        closest_action_idx = i
            
            if min_dist < 15: # Drempelwaarde om een lijn te selecteren
                self.selected_action_index = closest_action_idx
                # Zoek nu naar een specifiek punt op de geselecteerde lijn
                for j, p in enumerate(self.actions[self.selected_action_index]["points"]):
                    if distance(point, p) < 15:
                        self.selected_point_index = j
                        break # We hebben een punt gevonden, stop met zoeken
            
            if self.selected_action_index != -1:
                self.drawing = True
                self.drag_start_pos = point
            self.update_ui_for_selected_action()
        self.update_drawing()

    def handle_mouse_move(self, event):
        if not self.drawing: return
        pos = self.plot_widget.getViewBox().mapSceneToView(event.pos())
        point = (pos.x(), pos.y())

        if self.draw_mode == "Vrij Tekenen" and self.current_action:
            self.current_action["points"].append(point)
        elif self.draw_mode == "Lijn Tekenen" and self.current_action:
            self.current_action["points"][1] = point
        elif self.draw_mode == "Lijn Bewerken" and self.selected_action_index != -1:
            action = self.actions[self.selected_action_index]
            if self.selected_point_index != -1:
                # Verplaats een specifiek punt
                action["points"][self.selected_point_index] = point
            elif self.drag_start_pos:
                # Verplaats de hele lijn
                dx, dy = point[0] - self.drag_start_pos[0], point[1] - self.drag_start_pos[1]
                action["points"] = [(px + dx, py + dy) for px, py in action["points"]]
                self.drag_start_pos = point
            action['reset_effect_state'] = True
        self.update_drawing()

    def handle_mouse_release(self, event):
        # Voor Lijn Tekenen, de release event voltooit de actie niet.
        if self.draw_mode == "Lijn Tekenen" and self.line_drawing_first_click:
            return

        if self.drawing:
            if self.draw_mode == "Vrij Tekenen" and self.current_action:
                if len(self.current_action["points"]) > 1:
                    self.actions.append(self.current_action)
            
            # Alleen een undo state pushen als er daadwerkelijk iets is veranderd
            if self.current_action or self.draw_mode == "Lijn Bewerken":
                self.push_undo_state()

        self.drawing, self.drag_start_pos, self.current_action = False, None, None
        self.update_drawing()
    
    def _capture_and_crop_frame(self):
        """
        Maakt een schermafbeelding van de plot door de QGraphicsScene direct naar een QImage te renderen.
        Deze methode is robuuster dan ImageExporter of widget.grab().
        """
        if not self.image_item:
            print("INFO: Geen afbeelding item aanwezig om te exporteren.")
            return None

        # Zorg ervoor dat alle UI-updates zijn verwerkt
        QApplication.processEvents()

        # Haal de scene en de viewbox op
        scene = self.plot_widget.getPlotItem().scene()
        view_box = self.plot_widget.getViewBox()

        # Bepaal het brongebied dat we willen renderen (de view van de viewbox)
        source_rect = view_box.viewRect()

        if source_rect.width() <= 0 or source_rect.height() <= 0:
            print("WAARSCHUWING: ViewBox heeft geen geldige afmetingen voor export.")
            return None

        # Maak een QImage met de juiste afmetingen en een alpha-kanaal
        # We gebruiken de afmetingen van de originele afbeelding voor de juiste verhouding
        if self.original_image is not None:
            h, w, _ = self.original_image.shape
            target_size = QSize(w, h)
        else:
            target_size = source_rect.size().toSize()

        qimage = QImage(target_size, QImage.Format_ARGB32)
        qimage.fill(Qt.transparent) # Vul met transparante achtergrond

        # Maak een QPainter om op de QImage te tekenen
        painter = QPainter(qimage)
        painter.setRenderHint(QPainter.Antialiasing) # Optioneel: voor mooiere lijnen

        # Render de scene naar de painter.
        # Converteer de QRect en QRectF expliciet om TypeErrors te voorkomen.
        scene.render(painter, QRectF(qimage.rect()), QRectF(source_rect))
        painter.end()

        # Controleer of de QImage geldig is
        if qimage.isNull():
            print("WAARSCHUWING: Renderen van de scene naar QImage is mislukt.")
            return None

        # Converteer de QImage naar een PIL Image
        buffer = qimage.constBits()
        buffer.setsize(qimage.sizeInBytes())
        arr = np.frombuffer(buffer, dtype=np.uint8).reshape((qimage.height(), qimage.width(), 4))
        
        # Converteer van BGRA (Qt) naar RGBA (PIL)
        arr_rgba = cv2.cvtColor(arr, cv2.COLOR_BGRA2RGBA)
        pil_image = Image.fromarray(arr_rgba, 'RGBA')

        return pil_image

    def save_image(self):
        if not self.image_item:
            msg = QMessageBox(); msg.setIcon(QMessageBox.Warning); msg.setText("Geen afbeelding geladen!")
            msg.setInformativeText("Laad eerst een afbeelding voordat je opslaat."); msg.setWindowTitle("Opslaan Fout"); msg.exec_()
            return

        file_path, _ = QFileDialog.getSaveFileName(self, "Sla Afbeelding Op", "", "PNG Afbeeldingen (*.png);;JPEG Afbeeldingen (*.jpg)")
        if not file_path: return

        try:
            frame_pil = self._capture_and_crop_frame()
            if frame_pil:
                # Voor JPG, converteer naar RGB omdat JPG geen transparantie ondersteunt.
                if file_path.lower().endswith('.jpg') or file_path.lower().endswith('.jpeg'):
                    # Create a white background for JPG conversion to avoid black transparent areas
                    background = Image.new("RGB", frame_pil.size, (255, 255, 255))
                    background.paste(frame_pil, (0, 0), frame_pil) # Paste the RGBA image using its alpha channel
                    frame_pil = background
                frame_pil.save(file_path)
                
                print(f"Afbeelding opgeslagen naar {file_path}")
                msg = QMessageBox(); msg.setIcon(QMessageBox.Information); msg.setText("Opslaan Voltooid")
                msg.setInformativeText(f"Afbeelding opgeslagen als {os.path.basename(file_path)}"); msg.setWindowTitle("Succes"); msg.exec_()
            else:
                raise ValueError("Kon de afbeelding niet correct vastleggen/bijsnijden.")
        except Exception as e:
            print(f"Fout bij opslaan van afbeelding: {e}")
            msg = QMessageBox(); msg.setIcon(QMessageBox.Critical); msg.setText("Opslaan Mislukt")
            msg.setInformativeText(f"Er is een fout opgetreden:\n{e}"); msg.setWindowTitle("Opslaan Fout"); msg.exec_()

    def export_video(self):
        if not self.image_item:
            msg = QMessageBox(); msg.setIcon(QMessageBox.Warning); msg.setText("Geen afbeelding geladen!")
            msg.setInformativeText("Laad eerst een afbeelding voordat je exporteert."); msg.setWindowTitle("Export Fout"); msg.exec_()
            return

        file_path, _ = QFileDialog.getSaveFileName(self, "Sla MP4 op", "", "MP4 Bestanden (*.mp4)")
        if not file_path: return
        
        duration, fps = 5, 30
        watermark_path = os.path.join("images", "pulseline1.png")
        watermark_image = None
        
        try:
            watermark_image = Image.open(watermark_path).convert("RGBA")
            print(f"Watermerk '{watermark_path}' succesvol geladen.")
        except FileNotFoundError:
            print(f"WAARSCHUWING: Watermerk niet gevonden op '{watermark_path}'. Video wordt zonder watermerk gemaakt.")

        self.timer.stop() # Stop the timer during export to prevent UI updates from interfering
        
        frames_written = 0
        total_frames = duration * fps
        
        try:
            # Removed macro_block_size=1, as it can cause issues and is often not needed.
            # Using 'h264' codec as it's more standard and widely supported.
            with imageio.get_writer(file_path, fps=fps, codec='h264', quality=8) as writer:
                for i in range(total_frames):
                    self.timer_update() # Update the drawing for the current frame
                    QApplication.processEvents() # Process UI events to ensure drawing is complete
                    
                    frame_pil = self._capture_and_crop_frame()
                    if not frame_pil:
                        print(f"Frame {i+1}/{total_frames} mislukt, wordt overgeslagen.")
                        continue

                    # Converteer het frame naar RGBA voor consistente verwerking
                    base_image_rgba = frame_pil.convert('RGBA')

                    if watermark_image:
                        img_width, img_height = base_image_rgba.size
                        wm_width, wm_height = watermark_image.size
                        
                        max_wm_width = int(img_width * 0.2)
                        if wm_width > max_wm_width:
                            ratio = max_wm_width / wm_width
                            wm_width = max_wm_width
                            wm_height = int(wm_height * ratio)
                            # Corrected resize call:
                            watermark_resized = watermark_image.resize((wm_width, wm_height), Image.LANCZOS)
                        else:
                            watermark_resized = watermark_image

                        position = (10, img_height - watermark_resized.height - 10)
                        
                        # Maak een transparante laag voor het watermerk
                        txt_layer = Image.new('RGBA', base_image_rgba.size, (255,255,255,0))
                        txt_layer.paste(watermark_resized, position, watermark_resized)
                        
                        # Voeg het watermerk samen met de afbeelding
                        final_frame = Image.alpha_composite(base_image_rgba, txt_layer)
                    else:
                        final_frame = base_image_rgba

                    # Converteer het uiteindelijke frame naar RGB voor de MP4-codec
                    writer.append_data(np.array(final_frame.convert('RGB')))
                    frames_written += 1
                
            if frames_written > 0:
                print(f"Export naar {file_path} voltooid! {frames_written}/{total_frames} frames geschreven.")
                msg = QMessageBox(); msg.setIcon(QMessageBox.Information); msg.setText("Export Voltooid")
                msg.setInformativeText(f"Video opgeslagen als {os.path.basename(file_path)}"); msg.setWindowTitle("Succes"); msg.exec_()
            else:
                print("Export mislukt: geen enkele frame kon worden vastgelegd.")
                msg = QMessageBox(); msg.setIcon(QMessageBox.Critical); msg.setText("Export Mislukt")
                msg.setInformativeText("Kon geen frames vastleggen. Controleer of de afbeelding correct wordt weergegeven."); msg.setWindowTitle("Export Fout"); msg.exec_()
                if os.path.exists(file_path): os.remove(file_path)

        except Exception as e:
            print(f"Fout bij opslaan van MP4: {e}")
            print("Zorg ervoor dat 'imageio-ffmpeg' is geïnstalleerd: pip install imageio-ffmpeg")
            msg = QMessageBox(); msg.setIcon(QMessageBox.Critical); msg.setText("Fout bij Exporteren")
            msg.setInformativeText(f"Er is een onverwachte fout opgetreden:\n{e}"); msg.setWindowTitle("Export Fout"); msg.exec_()
        finally:
            self.timer.start(10) # Restart the timer after export


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = LEDVisualizer()
    ex.show()
    sys.exit(app.exec_())
