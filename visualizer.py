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

# Schakel OpenGL uit. Dit kan de stabiliteit van de ImageExporter verbeteren,
# omdat OpenGL-rendering soms conflicten kan veroorzaken tijdens het exporteren.
pg.setConfigOptions(useOpenGL=False)

# --- Probeer de echte utility en effect bestanden te importeren ---
try:
    # BELANGRIJKE OPMERKING: Zorg ervoor dat de 'effects' map een geldige Python package is
    # (d.w.z. dat er een leeg of initieel '__init__.py' bestand in zit).
    # Controleer ook of de methodenamen in je effectbestanden (bijv. effects/base_effect.py,
    # effects/static.py, effects/breathing.py) allemaal 'get_next_frame' (snake_case) gebruiken
    # in plaats van 'getNextFrame' (camelCase). Dit is cruciaal voor de functionaliteit.
    from effects.schemas import EffectModel, StaticParams, BreathingParams, Color, KnightRiderParams, MeteorParams, MulticolorParams, RunningLineParams, ChristmasSnowParams, FlagParams
    from effects.effects import get_effect_class
    from utils import distance, resample_points, smooth_points, point_line_distance
    from effects.converts import rgb_to_rgbw
    print("INFO: Echte 'utils' en 'effects' modules geladen.")
except ImportError as e:
    print(f"WAARSCHUWING: Kon de echte 'utils' en 'effects' modules niet vinden: {e}. Fallback naar dummy implementaties.")
    # Dummy implementaties voor ontwikkeling zonder volledige modules
    def distance(p1, p2): return math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)
    def resample_points(points, interval):
        if len(points) < 2: return points
        return points
    def smooth_points(points, window=5): return points
    def point_line_distance(point, p1, p2):
        line_length_sq = distance(p1, p2)**2
        if line_length_sq == 0: return distance(point, p1)
        t = max(0, min(1, (((point[0] - p1[0]) * (p2[0] - p1[0])) + ((point[1] - p1[1]) * (p2[1] - p1[1]))) / line_length_sq))
        closest_point = (p1[0] + t * (p2[0] - p1[0]), p1[1] + t * (p2[1] - p1[1]))
        return distance(point, closest_point)
    def rgb_to_rgbw(r, g, b): return r, g, b, 0
    
    # Dummy klassen voor de effecten en schema's
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
        def get_next_frame(self): # Correcte naam in dummy
            raise NotImplementedError("get_next_frame() must be implemented by subclasses")

    class DummyStaticEffect(Effects):
        def get_next_frame(self): # Correcte naam in dummy
            r, g, b = self.params.color[0].red, self.params.color[0].green, self.params.color[0].blue
            brightness_factor = self.params.brightness / 100.0
            return [(int(r * brightness_factor), int(g * brightness_factor), int(b * brightness_factor), 0)] * self.num_leds
    class BreathingEffect(Effects):
        def __init__(self, model):
            super().__init__(model)
            self.current_breathing_factor = 0.0
            self.rising = True
        def get_next_frame(self): # Correcte naam in dummy
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
    
    # Dummy get_effect_class functie
    _effect_classes = {"Static": DummyStaticEffect, "Pulseline": BreathingEffect}
    def get_effect_class(effect_name): return _effect_classes.get(effect_name)

    # Dummy parameters voor andere effecten (niet geïmplementeerd in dummy)
    class KnightRiderParams: pass
    class MeteorParams: pass
    class MulticolorParams: pass
    class RunningLineParams: pass
    class ChristmasSnowParams: pass
    class FlagParams: pass


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
        
        # Probeer het icoon te laden
        # Gebruik os.path.join om het pad correct samen te stellen
        try:
            self.setWindowIcon(QIcon(os.path.join(script_dir, "icons", "pulseline1.ico")))
        except Exception as e:
            print(f"WAARSCHUWING: Kon 'icons/pulseline1.ico' niet laden: {e}")

        # --- Attributen voor Afbeelding en Tekenen ---
        self.original_image = None # De origineel geladen afbeelding
        self.image = None          # De afbeelding met toegepaste duisternis
        self.image_item = None     # pyqtgraph ImageItem voor weergave van de afbeelding

        self.actions = []          # Lijst van getekende lijnen/acties. Elke actie is een dict.
        self.current_action = None # De lijn die momenteel wordt getekend
        
        self.line_plot_items = {}  # Dict om pyqtgraph PlotDataItem objecten bij te houden {action_id: PlotDataItem}
        self.point_plot_items = {} # Dict om pyqtgraph ScatterPlotItem objecten bij te houden {action_id: ScatterPlotItem}
        self.effect_instances = {} # Dict om effect instanties bij te houden {action_id: EffectObject}

        self.effect_index = 0      # Index van het geselecteerde effect in de combobox
        self.default_brightness = 1.0 # Standaard helderheid (0.0-1.0)
        self.default_speed = 5     # Standaard snelheid (1-50)
        self.line_width = 3        # Standaard lijndikte voor weergave
        self.led_color = (255, 0, 0) # Standaard LED kleur (rood)

        self.draw_mode = "Vrij Tekenen" # Huidige tekenmodus
        self.drawing = False           # Vlag om aan te geven of er getekend wordt
        self.line_drawing_first_click = False # Vlag voor de "Lijn Tekenen" modus
        
        self.selected_action_index = -1 # Index van de geselecteerde lijn in self.actions
        self.selected_point_index = -1  # Index van het geselecteerde punt binnen een lijn
        self.drag_start_pos = None      # Startpositie van een sleepactie

        self.undo_stack = []       # Stapel voor ongedaan maken
        self.redo_stack = []       # Stapel voor opnieuw uitvoeren

        self.init_ui() # Initialiseer de gebruikersinterface
        self.push_undo_state() # Sla de initiële lege staat op voor undo

        # Timer voor animatie-updates
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.timer_update)
        self.timer.start(30) # Update elke 30 ms (ongeveer 33 FPS)

    def init_ui(self):
        """
        Initialiseert de gebruikersinterface van de applicatie.
        """
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

        main_layout.addWidget(self.plot_widget, 80) # PlotWidget neemt 80% van de breedte in beslag
        self.plot_widget.viewport().installEventFilter(self) # Installeer event filter voor muisinteractie

        # --- Bedieningspaneel aan de rechterkant ---
        control_layout = QVBoxLayout()
        main_layout.addLayout(control_layout, 20) # Bedieningspaneel neemt 20% van de breedte in beslag
        
        # 1. Afbeelding Laden
        control_layout.addWidget(QPushButton("Afbeelding Laden", clicked=self.load_image))

        # 2. Lijnen intekenen (Tekenmodus)
        control_layout.addWidget(QLabel("Tekenmodus:"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Vrij Tekenen", "Lijn Tekenen", "Lijn Bewerken"])
        self.mode_combo.currentIndexChanged.connect(self.change_mode)
        control_layout.addWidget(self.mode_combo)

        # 3. Lijndikte bepalen
        control_layout.addWidget(QLabel("Lijndikte:"))
        self.line_width_slider = QSlider(Qt.Horizontal, minimum=1, maximum=20, value=self.line_width)
        self.line_width_slider.valueChanged.connect(lambda v: setattr(self, 'line_width', v))
        control_layout.addWidget(self.line_width_slider)

        # 4. Kies kleur
        control_layout.addWidget(QPushButton("Kies LED Kleur", clicked=self.choose_led_color))

        # 5. Kies effect
        control_layout.addWidget(QLabel("Effect:"))
        self.effect_combo = QComboBox()
        # Haal effectnamen op uit de get_effect_class functie
        self.effect_names = list(get_effect_class.__globals__['_effect_classes'].keys()) if '_effect_classes' in get_effect_class.__globals__ else ["Static", "Pulseline"]
        self.effect_combo.addItems(self.effect_names)
        self.effect_combo.currentIndexChanged.connect(self.change_effect)
        control_layout.addWidget(self.effect_combo)

        # Extra Opties (rechtsonder)
        control_layout.addStretch() # Duwt de volgende groep naar beneden
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

        extra_options_layout.addWidget(QPushButton("Lijnen Samenvoegen", clicked=self.merge_lines))
        extra_options_layout.addWidget(QPushButton("Ongedaan Maken", clicked=self.undo_action))
        extra_options_layout.addWidget(QPushButton("Opnieuw Uitvoeren", clicked=self.redo_action))
        extra_options_layout.addWidget(QPushButton("Sla Afbeelding Op", clicked=self.save_image))
        extra_options_layout.addWidget(QPushButton("Exporteer MP4", clicked=self.export_video))
        extra_options_layout.addWidget(QPushButton("Roteer Links", clicked=lambda: self.rotate_image(-90)))
        extra_options_layout.addWidget(QPushButton("Roteer Rechts", clicked=lambda: self.rotate_image(90)))
        extra_options_layout.addWidget(QPushButton("Wis Afbeelding", clicked=self.clear_image))
        extra_options_layout.addWidget(QPushButton("Wis Alle Lijnen", clicked=self.clear_all_lines))

        control_layout.addWidget(extra_options_group)

        # Statusbalk
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.show_status_message("Klaar om te beginnen! Laad een afbeelding.")

        # Initialiseer de effect- en modusinstellingen
        self.change_effect()
        self.change_mode()

    def show_status_message(self, message):
        """
        Toont een bericht in de statusbalk.
        """
        self.statusBar.showMessage(message)

    def set_current_action_brightness(self, value):
        """
        Stelt de helderheid in voor de geselecteerde lijn, of globaal als geen lijn is geselecteerd.
        """
        brightness_val = value / 100.0
        if self.selected_action_index != -1:
            self.actions[self.selected_action_index]['brightness'] = brightness_val
            self.actions[self.selected_action_index]['reset_effect_state'] = True # Reset effect bij wijziging
            self.show_status_message(f"Helderheid van geselecteerde lijn ingesteld op {value}%")
        else:
            self.default_brightness = brightness_val
            for action in self.actions:
                action['brightness'] = brightness_val
                action['reset_effect_state'] = True # Reset effect bij wijziging
            self.show_status_message(f"Globale helderheid ingesteld op {value}%")
        self.update_drawing()

    def set_current_action_speed(self, value):
        """
        Stelt de snelheid in voor de geselecteerde lijn, of globaal als geen lijn is geselecteerd.
        """
        if self.selected_action_index != -1:
            self.actions[self.selected_action_index]['speed'] = value
            self.actions[self.selected_action_index]['reset_effect_state'] = True # Reset effect bij wijziging
            self.show_status_message(f"Snelheid van geselecteerde lijn ingesteld op {value}")
        else:
            self.default_speed = value
            for action in self.actions:
                action['speed'] = value
                action['reset_effect_state'] = True # Reset effect bij wijziging
            self.show_status_message(f"Globale snelheid ingesteld op {value}")
        self.update_drawing()

    def update_ui_for_selected_action(self):
        """
        Werkt de UI-sliders bij op basis van de eigenschappen van de geselecteerde lijn.
        """
        # Blokkeer signalen om ongewenste triggers te voorkomen tijdens het instellen van waarden
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
        
        # Deblokkeer signalen
        self.brightness_slider.blockSignals(False)
        self.speed_slider.blockSignals(False)
        self.update_drawing() # Zorgt voor visuele update van selectie

    def timer_update(self):
        """
        Wordt periodiek aangeroepen door de QTimer om de animatie te updaten.
        """
        self.update_drawing()

    def update_drawing(self):
        """
        Tekent alle lijnen en effecten op de PlotWidget.
        Deze functie is geoptimaliseerd om bestaande plot-items bij te werken in plaats van ze opnieuw aan te maken.
        """
        # Verwijder plot-items die niet langer in self.actions staan
        current_action_ids = {action['id'] for action in self.actions}
        items_to_remove = []
        for action_id, item in self.line_plot_items.items():
            if action_id not in current_action_ids:
                self.plot_widget.removeItem(item)
                items_to_remove.append(action_id)
        for action_id in items_to_remove:
            del self.line_plot_items[action_id]
            if action_id in self.point_plot_items:
                self.plot_widget.removeItem(self.point_plot_items[action_id])
                del self.point_plot_items[action_id]
            if action_id in self.effect_instances:
                del self.effect_instances[action_id]

        # Voeg de huidige actie (als die getekend wordt) toe aan de lijst voor weergave
        all_actions_to_draw = self.actions[:]
        if self.current_action and len(self.current_action["points"]) > 0 and self.drawing:
            # Tijdelijk een kopie toevoegen, zodat de echte actie niet permanent wordt gewijzigd
            temp_action = copy.deepcopy(self.current_action)
            temp_action['id'] = 'temp_current_action' # Tijdelijke ID voor de huidige tekening
            all_actions_to_draw.append(temp_action)

        # Teken of update alle acties
        for action_idx, action in enumerate(all_actions_to_draw):
            action_id = action.get('id', str(uuid.uuid4())) # Zorg voor een ID
            if 'id' not in action: action['id'] = action_id # Voeg ID toe als deze ontbreekt

            pts = action["points"]
            
            if len(pts) < 2:
                # Verwijder het item als er geen punten zijn
                if action_id in self.line_plot_items:
                    self.plot_widget.removeItem(self.line_plot_items[action_id])
                    del self.line_plot_items[action_id]
                if action_id in self.point_plot_items:
                    self.plot_widget.removeItem(self.point_plot_items[action_id])
                    del self.point_plot_items[action_id]
                if action_id in self.effect_instances:
                    del self.effect_instances[action_id]
                continue

            # Bepaal lijndikte en kleur op basis van selectie en modus
            line_width = self.line_width
            
            # Haal effect klasse en parameters op
            effect_name = self.effect_names[self.effect_combo.currentIndex()]
            EffectClass = get_effect_class(effect_name)
            
            # Bepaal de juiste ParamsModel voor het effect
            ParamsModel = StaticParams
            if effect_name == "Pulseline": ParamsModel = BreathingParams
            # Voeg hier meer effecten toe als ze worden geïmplementeerd
            # elif effect_name == "Knight Rider": ParamsModel = KnightRiderParams

            current_speed = action.get('speed', self.default_speed)
            current_brightness = action.get('brightness', self.default_brightness)
            
            r_base, g_base, b_base = action.get("color", self.led_color)
            params_data = {"color": [Color(red=r_base, green=g_base, blue=b_base)], "brightness": int(current_brightness * 100)}
            
            # Bereken aantal LEDs en resampling interval
            total_line_length = sum(distance(pts[k], pts[k+1]) for k in range(len(pts) - 1))
            num_leds_for_this_line = max(2, int(total_line_length / 5)) if total_line_length > 0 else 2
            resampling_interval = total_line_length / (num_leds_for_this_line - 1) if num_leds_for_this_line > 1 else 1.0
            
            # Resample punten alleen als de geometrie is gewijzigd of de effect staat gereset moet worden
            if action.get('recalculate_resample', True) or action.get('reset_effect_state', True):
                points_for_effect = resample_points(pts, resampling_interval)
                action['resampled_points'] = points_for_effect
                action['num_leds_actual'] = len(points_for_effect)
                action['recalculate_resample'] = False # Reset vlag
            else:
                points_for_effect = action.get('resampled_points', [])
                num_leds_for_this_line = action.get('num_leds_actual', len(points_for_effect))

            # Beheer effect instanties
            effect_instance = self.effect_instances.get(action_id)
            if not effect_instance or action.get('reset_effect_state', False) or not isinstance(effect_instance, EffectClass):
                # Maak een nieuwe instantie of reset als nodig
                params_instance = ParamsModel(**params_data)
                model = EffectModel(params=params_instance, frame_skip=0, fps=30 * (current_speed / 5.0), num_leds=num_leds_for_this_line)
                effect_instance = EffectClass(model)
                self.effect_instances[action_id] = effect_instance
                action['reset_effect_state'] = False # Reset de vlag
            else:
                # Update bestaande instantie parameters
                effect_instance.params = ParamsModel(**params_data)
                effect_instance.num_leds = num_leds_for_this_line
                effect_instance.fps = 30 * (current_speed / 5.0)
            
            # Haal het volgende frame van het effect op
            frame_colors = effect_instance.get_next_frame()

            # Bepaal de uiteindelijke penkleur op basis van het effectframe
            # Gebruik de kleur van de eerste LED in het frame voor de lijn
            final_pen_color = QColor(*frame_colors[0][:3]) 

            # Pas selectievisuele feedback toe op de lijndikte en kleur
            if self.draw_mode == "Lijn Bewerken" and action_idx == self.selected_action_index:
                line_width += 3 # Maak geselecteerde lijn dikker
                # Optioneel: verander de kleur van de geselecteerde lijn naar geel voor extra duidelijkheid
                # final_pen_color = QColor(255, 255, 0) # Geel voor geselecteerde lijn
                # Als je wilt dat het effect zichtbaar blijft op de geselecteerde lijn,
                # kun je de gele kleur mengen of een rand toevoegen. Voor nu blijft het effect zichtbaar.

            # Update de lijn op de plot
            all_x, all_y = [p[0] for p in pts], [p[1] for p in pts]
            
            line_item = self.line_plot_items.get(action_id)
            if not line_item:
                # Maak een nieuw PlotDataItem aan als het nog niet bestaat
                line_item = self.plot_widget.plot(all_x, all_y, pen=pg.mkPen(final_pen_color, width=line_width, antialias=True), connect='all')
                self.line_plot_items[action_id] = line_item
            else:
                # Update de data en pen van het bestaande PlotDataItem
                line_item.setData(all_x, all_y)
                line_item.setPen(pg.mkPen(final_pen_color, width=line_width, antialias=True))

            # Teken bewerkingspunten als de lijn geselecteerd is in "Lijn Bewerken" modus
            if self.draw_mode == "Lijn Bewerken" and action_idx == self.selected_action_index:
                point_item = self.point_plot_items.get(action_id)
                if not point_item:
                    point_item = pg.ScatterPlotItem(x=[p[0] for p in pts], y=[p[1] for p in pts], size=10, brush=pg.mkBrush('b'), pen=pg.mkPen('w', width=1))
                    self.plot_widget.addItem(point_item)
                    self.point_plot_items[action_id] = point_item
                else:
                    point_item.setData(x=[p[0] for p in pts], y=[p[1] for p in pts])
            else:
                # Verwijder bewerkingspunten als de lijn niet geselecteerd is
                if action_id in self.point_plot_items:
                    self.plot_widget.removeItem(self.point_plot_items[action_id])
                    del self.point_plot_items[action_id]

    def change_effect(self):
        """
        Wijzigt het actieve visuele effect.
        """
        self.effect_index = self.effect_combo.currentIndex()
        for action in self.actions:
            action['reset_effect_state'] = True # Forceer reset van effect instanties
        self.show_status_message(f"Effect gewijzigd naar: {self.effect_names[self.effect_index]}")
        self.update_drawing()

    def choose_led_color(self):
        """
        Opent een kleurkiezer dialoog om de LED kleur in te stellen.
        """
        color = QColorDialog.getColor(QColor(*self.led_color)) # Start met huidige kleur
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
        """
        Laadt een achtergrondafbeelding en stelt de plotweergave in.
        """
        file_path, _ = QFileDialog.getOpenFileName(self, "Afbeelding Laden", "", "Afbeeldingen (*.png *.jpg *.jpeg *.bmp)")
        if file_path:
            try:
                # Gebruik PIL om afbeelding te laden, inclusief alpha-kanaal
                pil_image = Image.open(file_path).convert("RGBA")
                self.original_image = np.array(pil_image)
                
                self.darkness_slider.setValue(0) # Reset duisternis bij nieuwe afbeelding
                self.update_background_darkness(0) # Pas duisternis toe (0%)

                self.clear_all_lines(False) # Wis lijnen, maar niet de afbeelding zelf
                self.push_undo_state() # Sla de staat op na het laden van de afbeelding

                # Zorg ervoor dat de viewbox de nieuwe afbeelding past
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
        """
        Werkt de weergave van de achtergrondafbeelding op de plot bij.
        """
        if self.image is not None:
            if not self.image_item:
                self.image_item = pg.ImageItem()
                self.plot_widget.addItem(self.image_item)
            
            # Pyqtgraph's y-as is standaard omgekeerd, dus we draaien de afbeelding om.
            # ImageItem verwacht data in (rows, cols) formaat (hoogte, breedte).
            # Als de afbeelding (breedte, hoogte, kanalen) is van PIL, moeten we transponeren.
            # np.transpose(np.flipud(self.image), (1, 0, 2)) handelt dit correct af.
            transposed_image = np.transpose(np.flipud(self.image), (1, 0, 2))
            self.image_item.setImage(transposed_image)
            h, w, _ = self.image.shape
            self.image_item.setRect(0, 0, w, h)
        else:
            if self.image_item:
                self.plot_widget.removeItem(self.image_item)
                self.image_item = None
        self.update_drawing() # Zorg ervoor dat lijnen ook worden bijgewerkt

    def clear_all_lines(self, push_undo=True):
        """
        Verwijdert alle getekende lijnen van de plot.
        """
        for action_id, item in self.line_plot_items.items():
            self.plot_widget.removeItem(item)
        self.line_plot_items.clear()
        
        for action_id, item in self.point_plot_items.items():
            self.plot_widget.removeItem(item)
        self.point_plot_items.clear()

        self.effect_instances.clear() # Wis alle effect instanties
        self.actions.clear()
        self.current_action = None
        self.selected_action_index = -1
        self.selected_point_index = -1
        if push_undo:
            self.push_undo_state()
            self.show_status_message("Alle lijnen gewist.")
        self.update_drawing() # Zorg voor een schone weergave
        self.update_ui_for_selected_action() # Reset UI sliders

    def clear_image(self):
        """
        Verwijdert de achtergrondafbeelding van de plot.
        """
        if self.image_item:
            self.plot_widget.removeItem(self.image_item)
            self.image_item = None
        self.image = None
        self.original_image = None
        self.clear_all_lines(False) # Wis ook lijnen, want ze zijn nu zinloos zonder afbeelding
        self.push_undo_state()
        self.show_status_message("Afbeelding gewist.")
        self.plot_widget.getViewBox().autoRange() # Reset zoom

    def update_background_darkness(self, value):
        """
        Past de duisternis van de achtergrondafbeelding aan.
        """
        if self.original_image is None:
            return
        
        brightness_factor = 1.0 - (value / 100.0)
        # Maak een kopie om de originele afbeelding te behouden
        self.image = self.original_image.copy()
        
        # Pas helderheid toe op de RGB-kanalen
        rgb_channels = self.image[:, :, :3].astype('float')
        rgb_channels *= brightness_factor
        rgb_channels = np.clip(rgb_channels, 0, 255) # Zorg ervoor dat waarden binnen 0-255 blijven
        self.image[:, :, :3] = rgb_channels.astype('uint8')
        
        self.update_display()
        self.show_status_message(f"Achtergrond duisternis ingesteld op {value}%")

    def merge_lines(self):
        """
        Voegt lijnen samen die dicht bij elkaar liggen.
        """
        if len(self.actions) < 2:
            self.show_status_message("Minstens twee lijnen nodig om samen te voegen.")
            return

        self.push_undo_state() # Sla de huidige staat op voor undo
        merge_threshold = 25 # Pixel drempelwaarde voor samenvoegen
        merged_in_pass = True
        
        # Loop totdat er geen merges meer plaatsvinden in een pass
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
                    
                    # Controleer alle 4 mogelijke verbindingen tussen lijnuiteinden
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
                        # Verwijder plot items en effect instantie van de samengevoegde lijn
                        removed_action_id = self.actions[j]['id']
                        if removed_action_id in self.line_plot_items:
                            self.plot_widget.removeItem(self.line_plot_items[removed_action_id])
                            del self.line_plot_items[removed_action_id]
                        if removed_action_id in self.point_plot_items:
                            self.plot_widget.removeItem(self.point_plot_items[removed_action_id])
                            del self.point_plot_items[removed_action_id]
                        if removed_action_id in self.effect_instances:
                            del self.effect_instances[removed_action_id]

                        self.actions.pop(j) # Verwijder de samengevoegde lijn
                        self.actions[i]['reset_effect_state'] = True # Reset effect van de nieuwe lijn
                        self.actions[i]['recalculate_resample'] = True # Forceer resampling
                        merged_in_pass = True
                        i = -1 # Herstart de buitenste lus om verdere samenvoegingen met de nieuwe lijn te controleren
                        break # Breek de binnenste lus af, want de lijst is gewijzigd
                    else:
                        j += 1
                if i == -1: break # Als i is gereset, herstart de buitenste lus
                i += 1
        
        self.update_drawing()
        self.push_undo_state() # Sla de nieuwe staat op na samenvoegen
        self.show_status_message("Lijnen samengevoegd.")

    def push_undo_state(self):
        """
        Slaat de huidige staat van de acties op in de undo-stapel.
        """
        state_to_save = []
        for action in self.actions:
            # Maak een schone kopie, exclusief niet-serialiseerbare objecten zoals effect_instance
            clean_action = {k: v for k, v in action.items() if k not in ['effect_instance', 'plot_items', 'resampled_points']}
            state_to_save.append(clean_action)
        self.undo_stack.append(copy.deepcopy(state_to_save))
        self.redo_stack.clear() # Wis de redo-stapel wanneer een nieuwe actie wordt uitgevoerd
        self.show_status_message("Staat opgeslagen voor ongedaan maken.")

    def undo_action(self):
        """
        Maakt de laatste actie ongedaan.
        """
        if len(self.undo_stack) > 1: # Er moet minstens één staat voor de huidige zijn om ongedaan te maken
            current_state = self.undo_stack.pop()
            self.redo_stack.append(current_state) # Voeg de huidige staat toe aan de redo-stapel
            
            # Verwijder alle huidige plot-items van de plot
            for action_id, item in self.line_plot_items.items():
                self.plot_widget.removeItem(item)
            self.line_plot_items.clear()
            for action_id, item in self.point_plot_items.items():
                self.plot_widget.removeItem(item)
            self.point_plot_items.clear()
            self.effect_instances.clear() # Wis alle effect instanties

            # Herstel de vorige staat
            previous_state = self.undo_stack[-1]
            self.actions = copy.deepcopy(previous_state)
            
            # Markeer alle effecten als te resetten
            for action in self.actions:
                action['reset_effect_state'] = True
                action['recalculate_resample'] = True # Forceer resampling bij undo/redo
            
            self.selected_action_index = -1 # Deselecteer eventuele geselecteerde lijnen
            self.selected_point_index = -1
            self.update_drawing()
            self.update_ui_for_selected_action()
            self.show_status_message("Actie ongedaan gemaakt.")
        else:
            self.show_status_message("Niets om ongedaan te maken.")

    def redo_action(self):
        """
        Voert de laatst ongedaan gemaakte actie opnieuw uit.
        """
        if self.redo_stack:
            restored_state = self.redo_stack.pop()
            self.undo_stack.append(restored_state) # Voeg de herstelde staat toe aan de undo-stapel

            # Verwijder alle huidige plot-items van de plot
            for action_id, item in self.line_plot_items.items():
                self.plot_widget.removeItem(item)
            self.line_plot_items.clear()
            for action_id, item in self.point_plot_items.items():
                self.plot_widget.removeItem(item)
            self.point_plot_items.clear()
            self.effect_instances.clear() # Wis alle effect instanties

            # Herstel de staat
            self.actions = copy.deepcopy(restored_state)
            
            # Markeer alle effecten als te resetten
            for action in self.actions:
                action['reset_effect_state'] = True
                action['recalculate_resample'] = True # Forceer resampling bij undo/redo

            self.selected_action_index = -1 # Deselecteer eventuele geselecteerde lijnen
            self.selected_point_index = -1
            self.update_drawing()
            self.update_ui_for_selected_action()
            self.show_status_message("Actie opnieuw uitgevoerd.")
        else:
            self.show_status_message("Niets om opnieuw uit te voeren.")
    
    def rotate_image(self, angle):
        """
        Roteert de achtergrondafbeelding met de opgegeven hoek (90 of -90 graden).
        """
        if self.original_image is None:
            self.show_status_message("Geen afbeelding geladen om te roteren.")
            return

        try:
            # OpenCV rotatiefuncties: ROTATE_90_CLOCKWISE, ROTATE_90_COUNTERCLOCKWISE
            if angle == 90:
                self.original_image = cv2.rotate(self.original_image, cv2.ROTATE_90_CLOCKWISE)
            elif angle == -90:
                self.original_image = cv2.rotate(self.original_image, cv2.ROTATE_90_COUNTERCLOCKWISE)
            
            # Na rotatie kunnen de afbeeldingsafmetingen veranderen, dus update het viewbox bereik
            h, w, _ = self.original_image.shape
            self.plot_widget.getViewBox().setRange(xRange=(0, w), yRange=(0, h), padding=0)
            self.update_background_darkness(self.darkness_slider.value()) # Pas duisternis opnieuw toe
            
            # Wis bestaande lijnen, omdat hun coördinaten ongeldig zijn na rotatie
            self.clear_all_lines(False) # Wis lijnen, maar niet de afbeelding zelf
            self.push_undo_state() # Sla de staat op na rotatie
            self.show_status_message(f"Afbeelding {angle} graden geroteerd.")
        except Exception as e:
            QMessageBox.critical(self, "Rotatie Fout", f"Fout bij roteren van afbeelding: {e}")
            self.show_status_message(f"Fout bij roteren van afbeelding: {e}")


    def change_mode(self):
        """
        Wijzigt de huidige tekenmodus.
        """
        self.draw_mode = self.mode_combo.currentText()
        self.selected_action_index = -1 # Deselecteer lijnen bij moduswisseling
        self.selected_point_index = -1
        self.line_drawing_first_click = False # Reset voor lijn tekenen modus
        self.update_ui_for_selected_action()
        self.update_drawing()
        self.show_status_message(f"Tekenmodus gewijzigd naar: {self.draw_mode}")

    def eventFilter(self, source, event):
        """
        Filtert muisgebeurtenissen op de plotwidget voor teken- en bewerkingsfunctionaliteit.
        """
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
        """
        Verwerkt muisklikken op de plotwidget.
        """
        pos = self.plot_widget.getViewBox().mapSceneToView(event.pos())
        point = (pos.x(), pos.y())

        if self.draw_mode == "Vrij Tekenen":
            self.drawing = True
            # Geef de nieuwe actie een unieke ID
            self.current_action = {
                "id": str(uuid.uuid4()), 
                "mode": self.draw_mode, 
                "points": [point], 
                "color": self.led_color, 
                'speed': self.default_speed, 
                'brightness': self.default_brightness,
                'reset_effect_state': True,
                'recalculate_resample': True
            }
            self.show_status_message("Vrij tekenen gestart.")
        elif self.draw_mode == "Lijn Tekenen":
            if not self.line_drawing_first_click:
                self.drawing = True
                self.line_drawing_first_click = True
                # Geef de nieuwe actie een unieke ID
                self.current_action = {
                    "id": str(uuid.uuid4()), 
                    "mode": self.draw_mode, 
                    "points": [point, point], # Begin- en eindpunt zijn initieel hetzelfde
                    "color": self.led_color, 
                    'speed': self.default_speed, 
                    'brightness': self.default_brightness,
                    'reset_effect_state': True,
                    'recalculate_resample': True
                }
                self.show_status_message("Beginpunt van lijn geselecteerd.")
            else:
                # Tweede klik voltooit de lijn
                if self.current_action:
                    self.current_action["points"][1] = point
                    self.actions.append(self.current_action)
                    self.push_undo_state()
                    self.show_status_message("Lijn voltooid.")
                self.current_action, self.drawing, self.line_drawing_first_click = None, False, False
        elif self.draw_mode == "Lijn Bewerken":
            self.selected_action_index, self.selected_point_index = -1, -1
            min_dist = float('inf')
            
            # Zoek eerst naar het dichtstbijzijnde punt op een lijn
            for i, action in enumerate(self.actions):
                for j, p in enumerate(action["points"]):
                    dist = distance(point, p)
                    if dist < 15 and dist < min_dist: # Drempelwaarde voor puntselectie
                        min_dist = dist
                        self.selected_action_index = i
                        self.selected_point_index = j
            
            if self.selected_action_index == -1: # Als geen punt is geselecteerd, probeer dan een lijn te selecteren
                min_dist_line = float('inf')
                closest_action_idx = -1
                for i, action in enumerate(self.actions):
                    if len(action["points"]) < 2: continue
                    # Controleer afstand tot elk segment van de lijn
                    for k in range(len(action["points"]) - 1):
                        dist = point_line_distance(point, action["points"][k], action["points"][k+1])
                        if dist < min_dist_line:
                            min_dist_line = dist
                            closest_action_idx = i
                
                if min_dist_line < 15: # Drempelwaarde om een lijn te selecteren
                    self.selected_action_index = closest_action_idx
                    self.selected_point_index = -1 # Geen specifiek punt geselecteerd, hele lijn wordt verplaatst

            if self.selected_action_index != -1:
                self.drawing = True
                self.drag_start_pos = point
                self.show_status_message(f"Lijn {self.selected_action_index + 1} geselecteerd voor bewerking.")
            else:
                self.show_status_message("Geen lijn of punt geselecteerd.")

            self.update_ui_for_selected_action() # Update UI sliders
        self.update_drawing() # Zorg voor visuele feedback van selectie

    def handle_mouse_move(self, event):
        """
        Verwerkt muisbewegingen voor tekenen en bewerken.
        """
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
                # Verplaats een specifiek punt
                action["points"][self.selected_point_index] = point
                self.show_status_message(f"Punt {self.selected_point_index + 1} van lijn {self.selected_action_index + 1} verplaatst.")
            elif self.drag_start_pos:
                # Verplaats de hele lijn
                dx, dy = point[0] - self.drag_start_pos[0], point[1] - self.drag_start_pos[1]
                action["points"] = [(px + dx, py + dy) for px, py in action["points"]]
                self.drag_start_pos = point # Update de startpositie voor de volgende beweging
                self.show_status_message(f"Lijn {self.selected_action_index + 1} verplaatst.")
            action['reset_effect_state'] = True # Reset effect bij wijziging van punten
            action['recalculate_resample'] = True # Forceer resampling bij wijziging van punten
        self.update_drawing()

    def handle_mouse_release(self, event):
        """
        Verwerkt het loslaten van de muisknop.
        """
        # Voor Lijn Tekenen, de release event voltooit de actie niet; de tweede klik doet dat.
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
                self.push_undo_state() # Sla staat op na bewerking
                self.show_status_message("Lijn bewerking voltooid.")

        self.drawing = False
        self.drag_start_pos = None
        self.current_action = None # Reset de huidige actie
        self.update_drawing() # Zorg voor de laatste update


    def _capture_and_crop_frame(self):
        """
        Maakt een schermafbeelding van de plot en exporteert deze als 1920x1080.
        Het zal de inhoud van de plot uitrekken om de 1920x1080 afmetingen te vullen
        als de oorspronkelijke beeldverhouding afwijkt.
        """
        if not self.image_item and not self.actions:
            QMessageBox.warning(self, "Export Fout", "Geen afbeelding of lijnen geladen om te exporteren!")
            return None

        # Zorg ervoor dat alle UI-updates zijn verwerkt
        QApplication.processEvents()

        # Definieer de doel export resolutie
        EXPORT_WIDTH = 1920
        EXPORT_HEIGHT = 1080
        target_qimage_size = QSize(EXPORT_WIDTH, EXPORT_HEIGHT)

        # Maak een QImage met de gewenste export afmetingen
        qimage = QImage(target_qimage_size, QImage.Format_ARGB32)
        qimage.fill(Qt.transparent) # Vul met transparante achtergrond

        painter = QPainter(qimage)
        # Gebruik een try-finally blok om te garanderen dat painter.end() altijd wordt aangeroepen
        try:
            painter.setRenderHint(QPainter.Antialiasing) # Optioneel: voor mooiere lijnen

            # Haal de scene en de viewbox op
            scene = self.plot_widget.getPlotItem().scene()
            view_box = self.plot_widget.getViewBox()

            # Sla de huidige staat van de viewbox op
            # We gebruiken view_box.getState() en view_box.restoreState()
            # Dit is robuuster dan individuele eigenschappen zoals aspectLocked
            current_view_state = view_box.getState()

            # Tijdelijk de viewbox aanpassen om de exportverhouding te vullen
            view_box.setAspectLocked(False) # Ontgrendel de beeldverhouding tijdelijk
            # Stel het bereik van de viewbox in op de exportafmetingen.
            # Dit zal de inhoud uitrekken/comprimeren om dit bereik te vullen.
            view_box.setRange(xRange=(0, EXPORT_WIDTH), yRange=(0, EXPORT_HEIGHT), padding=0)
            
            # De source_rect is nu het volledige bereik van de viewbox, wat overeenkomt met de exportafmetingen
            source_rect_for_render = QRectF(0, 0, EXPORT_WIDTH, EXPORT_HEIGHT)

            # Render de scene naar de QImage.
            # De inhoud van source_rect_for_render (de 1920x1080 data-ruimte) wordt geschaald
            # om precies in qimage.rect() (de 1920x1080 pixel-ruimte) te passen.
            scene.render(painter, QRectF(qimage.rect()), source_rect_for_render)

        finally:
            painter.end() # Garandeer dat de painter wordt beëindigd
            # Herstel de oorspronkelijke staat van de viewbox
            view_box.restoreState(current_view_state)


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
        """
        Slaat de huidige weergave van de plot op als een afbeelding (PNG of JPG).
        """
        if not self.image_item and not self.actions:
            QMessageBox.warning(self, "Opslaan Fout", "Geen afbeelding of lijnen geladen om op te slaan!")
            self.show_status_message("Opslaan mislukt: geen inhoud om op te slaan.")
            return

        file_path, _ = QFileDialog.getSaveFileName(self, "Sla Afbeelding Op", "", "PNG Afbeeldingen (*.png);;JPEG Afbeeldingen (*.jpg)")
        if not file_path: return

        try:
            frame_pil = self._capture_and_crop_frame()
            if frame_pil:
                # Voor JPG, converteer naar RGB omdat JPG geen transparantie ondersteunt.
                if file_path.lower().endswith('.jpg') or file_path.lower().endswith('.jpeg'):
                    # Maak een witte achtergrond voor JPG-conversie om zwarte transparante gebieden te voorkomen
                    background = Image.new("RGB", frame_pil.size, (255, 255, 255))
                    background.paste(frame_pil, (0, 0), frame_pil) # Plak de RGBA-afbeelding met behulp van het alfakanaal
                    frame_pil = background
                frame_pil.save(file_path)
                
                self.show_status_message(f"Afbeelding opgeslagen naar {os.path.basename(file_path)}")
                QMessageBox.information(self, "Opslaan Voltooid", f"Afbeelding opgeslagen als {os.path.basename(file_path)}")
            else:
                raise ValueError("Kon de afbeelding niet correct vastleggen/bijsnijden.")
        except Exception as e:
            self.show_status_message(f"Fout bij opslaan van afbeelding: {e}")
            QMessageBox.critical(self, "Opslaan Mislukt", f"Er is een fout opgetreden:\n{e}")

    def export_video(self):
        """
        Exporteert een animatie van de effecten als een MP4-video.
        """
        if not self.image_item and not self.actions:
            QMessageBox.warning(self, "Export Fout", "Geen afbeelding of lijnen geladen om te exporteren!")
            self.show_status_message("Export mislukt: geen inhoud om te exporteren.")
            return

        file_path, _ = QFileDialog.getSaveFileName(self, "Sla MP4 op", "", "MP4 Bestanden (*.mp4)")
        if not file_path: return
        
        duration = 5 # seconden
        fps = 30     # frames per seconde
        watermark_path = os.path.join(script_dir, "images", "pulseline1.png") # Correct pad voor watermerk
        watermark_image = None
        
        try:
            watermark_image = Image.open(watermark_path).convert("RGBA")
            self.show_status_message(f"Watermerk '{os.path.basename(watermark_path)}' succesvol geladen.")
        except FileNotFoundError:
            self.show_status_message(f"WAARSCHUWING: Watermerk niet gevonden op '{watermark_path}'. Video wordt zonder watermerk gemaakt.")
        except Exception as e:
            self.show_status_message(f"WAARSCHUWING: Fout bij laden watermerk: {e}. Video wordt zonder watermerk gemaakt.")


        self.timer.stop() # Stop de timer tijdens export om interferentie te voorkomen
        
        frames_written = 0
        total_frames = duration * fps
        
        try:
            # Gebruik 'h264' codec voor bredere compatibiliteit
            with imageio.get_writer(file_path, fps=fps, codec='h264', quality=8) as writer:
                for i in range(total_frames):
                    self.update_drawing() # Update de tekening voor het huidige frame
                    QApplication.processEvents() # Verwerk UI-events om te zorgen dat de tekening compleet is
                    
                    frame_pil = self._capture_and_crop_frame()
                    if not frame_pil:
                        self.show_status_message(f"Frame {i+1}/{total_frames} mislukt, wordt overgeslagen.")
                        continue

                    # Converteer het frame naar RGBA voor consistente verwerking
                    base_image_rgba = frame_pil.convert('RGBA')

                    if watermark_image:
                        img_width, img_height = base_image_rgba.size
                        wm_width, wm_height = watermark_image.size
                        
                        # Schaal watermerk indien te groot (max 20% van de breedte)
                        max_wm_width = int(img_width * 0.2)
                        if wm_width > max_wm_width:
                            ratio = max_wm_width / wm_width
                            wm_width = max_wm_width
                            wm_height = int(wm_height * ratio)
                            watermark_resized = watermark_image.resize((wm_width, wm_height), Image.LANCZOS)
                        else:
                            watermark_resized = watermark_image

                        # Plaats watermerk linksonder
                        position = (10, img_height - watermark_resized.height - 10)
                        
                        # Maak een transparante laag voor het watermerk en plak het
                        txt_layer = Image.new('RGBA', base_image_rgba.size, (255,255,255,0))
                        txt_layer.paste(watermark_resized, position, watermark_resized)
                        
                        # Voeg het watermerk samen met de afbeelding
                        final_frame = Image.alpha_composite(base_image_rgba, txt_layer)
                    else:
                        final_frame = base_image_rgba

                    # Converteer het uiteindelijke frame naar RGB voor de MP4-codec
                    writer.append_data(np.array(final_frame.convert('RGB')))
                    frames_written += 1
                    self.show_status_message(f"Exporteren: {frames_written}/{total_frames} frames geschreven...")
                
            if frames_written > 0:
                self.show_status_message(f"Export naar {os.path.basename(file_path)} voltooid! {frames_written}/{total_frames} frames geschreven.")
                QMessageBox.information(self, "Export Voltooid", f"Video opgeslagen als {os.path.basename(file_path)}")
            else:
                self.show_status_message("Export mislukt: geen enkele frame kon worden vastgelegd.")
                QMessageBox.critical(self, "Export Mislukt", "Kon geen frames vastleggen. Controleer of de afbeelding correct wordt weergegeven.")
                if os.path.exists(file_path): os.remove(file_path) # Verwijder onvolledig bestand

        except Exception as e:
            self.show_status_message(f"Fout bij opslaan van MP4: {e}")
            QMessageBox.critical(self, "Fout bij Exporteren", f"Er is een onverwachte fout opgetreden:\n{e}\nZorg ervoor dat 'imageio-ffmpeg' is geïnstalleerd: pip install imageio-ffmpeg")
        finally:
            self.timer.start(30) # Herstart de timer na export


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = LEDVisualizer()
    ex.show()
    sys.exit(app.exec_())

