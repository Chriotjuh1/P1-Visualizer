import sys
import math
import time
import copy
import random
import numpy as np
import cv2
import imageio
import colorsys

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QSlider, QComboBox, QFileDialog, QColorDialog, QApplication
)
from PyQt5.QtCore import Qt, QTimer, QEvent
from PyQt5.QtGui import QMouseEvent, QIcon, QImage, QPixmap
import pyqtgraph as pg
from PIL import Image

from utils import distance, resample_points, smooth_points, point_line_distance

# Importeer de functie om effectklassen op te halen
from effects.effects import get_effect_class

# Importeer de schema's en conversiefuncties vanuit de 'effects' map
from effects.schemas import (
    EffectModel, StaticParams, BreathingParams, KnightRiderParams,
    MeteorParams, MulticolorParams, RunningLineParams, ChristmasSnowParams,
    FlagParams, Color
)
from effects.converts import rgb_to_rgbw # Nodig voor de visualisatie van kleuren

class LEDVisualizer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Pulseline1 Visualizer")
        self.setGeometry(100, 100, 1920, 1080)
        # self.setWindowIcon(QIcon("logo.ico")) # Assuming 'logo.ico' is available

        # --- Attributen ---
        self.image = None
        self.rotated_image = None
        self.image_item = None
        self.actions = [] # Opgeslagen lijnen/acties
        self.current_action = None # De lijn die momenteel wordt getekend
        
        # Algemene parameters
        self.effect_index = 0 # Index van het geselecteerde effect
        self.default_brightness = 1.0 # Standaard helderheid voor nieuwe lijnen
        self.line_width = 3 # Breedte van de getekende lijn
        self.led_color = (255, 0, 0) # Standaard LED-kleur (voor statische/ademhaling etc.)
        self.default_speed = 5 # Standaard snelheid voor nieuwe lijnen
        
        # Teken- en edit-modus
        self.draw_mode = "Vrij Tekenen" # Tekenmodus
        self.drawing = False # Geeft aan of er wordt getekend (voor vrij tekenen/slepen)
        self.line_drawing_first_click = False # Nieuwe vlag voor "Lijn Tekenen" (eerste klik)
        self.edit_action_index = None # Index van de actie die wordt bewerkt
        self.edit_vertex_index = None # Index van het punt dat wordt bewerkt
        self.selected_action_index = -1 # Index van de geselecteerde actie voor bewerken
        self.selected_point_index = -1 # Index van het geselecteerde punt binnen de actie
        self.drag_start_pos = None # Startpositie voor slepen in bewerkingsmodus

        # Undo/Redo
        self.undo_stack = []
        self.redo_stack = []

        # Panning (niet direct gebruikt in de geüpdatete code, maar behouden indien nodig)
        self.right_mouse_pressed = False
        self.pan_start = None
        
        # Items op de plot
        self.segment_items = [] # Grafische items voor segmenten
        self.edit_points_items = [] # Grafische items voor bewerkingspunten

        # --- State voor specifieke effecten (deze attributen zijn nu alleen voor UI-parameters, niet animatietoestand) ---
        self.knight_rider_length = 20
        self.meteor_state = { # Bevat nu alleen parameters, niet de animatietoestand (position, sparkles)
            'width': 10,
            'spark_intensity': 20,
        }
        self.running_line_state = { # Bevat nu alleen parameters, niet de animatietoestand (position)
            'width': 10,
            'count': 1
        }
        self.christmas_snow_state = { # Bevat nu alleen parameters, niet de animatietoestand (led_states, fade_speed, bg_color)
            'density': 10,
        }
        self.flag_state = { # Bevat nu alleen parameters, niet de animatietoestand (position)
            'widths': [50, 50, 50], # Breedtes voor 3 vlagsegmenten
            'colors': [(255, 0, 0), (0, 255, 0), (0, 0, 255)], # Kleuren voor 3 vlagsegmenten
            'background_color': (0,0,0) # Achtergrondkleur van de vlag
        }
        self.selected_flag_segment = 0 # Welk vlagsegment wordt bewerkt

        self.init_ui()
        self.push_undo_state()

        # Timerfrequentie verhoogd voor soepelere animaties (100 FPS)
        self.timer = QTimer(self, timeout=self.timer_update)
        self.timer.start(10)

    def init_ui(self):
        """
        Initialiseert de gebruikersinterface van de visualizer.
        """
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        # Plot widget voor het tekengebied
        self.plot_widget = pg.PlotWidget(background='w')
        self.plot_widget.hideAxis('left')
        self.plot_widget.hideAxis('bottom')
        self.plot_widget.getViewBox().setMouseEnabled(x=False, y=False)
        main_layout.addWidget(self.plot_widget, 80)
        self.plot_widget.viewport().installEventFilter(self) # Installeer eventfilter voor muisinteractie

        # Besturingspaneel aan de rechterkant
        control_layout = QVBoxLayout()
        main_layout.addLayout(control_layout, 20)
        
        # --- UI Elementen in de gewenste volgorde ---
        # 1. Afbeelding laden
        control_layout.addWidget(QPushButton("Afbeelding Laden", clicked=self.load_image))

        # 2. Lijnen intekenen of vrij tekenen
        control_layout.addWidget(QLabel("Tekenmodus:"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Vrij Tekenen", "Lijn Tekenen", "Lijn Bewerken"])
        self.mode_combo.currentIndexChanged.connect(self.change_mode)
        control_layout.addWidget(self.mode_combo)
        control_layout.addWidget(QPushButton("Lijnen Samenvoegen", clicked=self.merge_lines))
        control_layout.addWidget(QPushButton("Wis Lijnen", clicked=self.clear_everything))

        # 3. Lijndikte slider
        control_layout.addWidget(QLabel("Lijndikte:"))
        self.line_width_slider = QSlider(Qt.Horizontal, minimum=1, maximum=20, value=self.line_width)
        self.line_width_slider.valueChanged.connect(lambda v: setattr(self, 'line_width', v))
        control_layout.addWidget(self.line_width_slider)

        # 4. Color picker
        control_layout.addWidget(QPushButton("Kies LED Kleur", clicked=self.choose_led_color))
        # Vlag specifieke kleurkiezer (alleen zichtbaar bij Vlag-effect)
        self.flag_segment_label = QLabel("Vlag Segment Kleur:")
        control_layout.addWidget(self.flag_segment_label)
        self.flag_segment_combo = QComboBox()
        self.flag_segment_combo.addItems(["Segment 1", "Segment 2", "Segment 3"])
        self.flag_segment_combo.currentIndexChanged.connect(self.set_selected_flag_segment)
        control_layout.addWidget(self.flag_segment_combo)
        self.choose_flag_color_button = QPushButton("Kies Vlag Segment Kleur", clicked=self.choose_flag_segment_color)
        control_layout.addWidget(self.choose_flag_color_button)

        # 5. Effect dropdown
        control_layout.addWidget(QLabel("Effect:"))
        self.effect_combo = QComboBox()
        self.effect_names = ["Static", "Breathing", "Knight Rider", "Meteor", "Multicolor", "Running Line", "Christmas Snow", "Flag"]
        self.effect_combo.addItems(self.effect_names)
        self.effect_combo.currentIndexChanged.connect(self.change_effect)
        control_layout.addWidget(self.effect_combo)

        # Algemene helderheid slider (wordt nu per-lijn beheerd, maar de slider blijft)
        control_layout.addWidget(QLabel("Helderheid (LED):"))
        self.brightness_slider = QSlider(Qt.Horizontal, minimum=0, maximum=100, value=int(self.default_brightness * 100), singleStep=1)
        self.brightness_slider.valueChanged.connect(self.set_current_action_brightness)
        control_layout.addWidget(self.brightness_slider)

        # Snelheid slider (wordt nu per-lijn beheerd)
        control_layout.addWidget(QLabel("Snelheid:"))
        self.speed_slider = QSlider(Qt.Horizontal, minimum=1, maximum=50, value=self.default_speed)
        self.speed_slider.valueChanged.connect(self.set_current_action_speed)
        control_layout.addWidget(self.speed_slider)

        # --- Context-afhankelijke sliders en knoppen (rechtsonderin) ---
        control_layout.addStretch() # Duwt de volgende widgets naar beneden

        self.sliders = {
            "Knight Rider Length": (QLabel("Knight Rider Lengte:"), QSlider(Qt.Horizontal, minimum=5, maximum=100, value=self.knight_rider_length)),
            "Meteor Width": (QLabel("Meteor Breedte:"), QSlider(Qt.Horizontal, minimum=2, maximum=50, value=self.meteor_state['width'])),
            "Spark Intensity": (QLabel("Vonk Intensiteit:"), QSlider(Qt.Horizontal, minimum=0, maximum=100, value=self.meteor_state['spark_intensity'])),
            "Running Line Width": (QLabel("Lopende Lijn Breedte:"), QSlider(Qt.Horizontal, minimum=2, maximum=100, value=self.running_line_state['width'])),
            "Running Line Count": (QLabel("Aantal Lopende Lijnen:"), QSlider(Qt.Horizontal, minimum=1, maximum=10, value=self.running_line_state['count'])),
            "Sparkle Density": (QLabel("Schittering Dichtheid:"), QSlider(Qt.Horizontal, minimum=1, maximum=100, value=self.christmas_snow_state['density'])),
            "Flag Width 1": (QLabel("Vlag Breedte 1:"), QSlider(Qt.Horizontal, minimum=1, maximum=200, value=self.flag_state['widths'][0])),
            "Flag Width 2": (QLabel("Vlag Breedte 2:"), QSlider(Qt.Horizontal, minimum=1, maximum=200, value=self.flag_state['widths'][1])),
            "Flag Width 3": (QLabel("Vlag Breedte 3:"), QSlider(Qt.Horizontal, minimum=1, maximum=200, value=self.flag_state['widths'][2])),
        }
        
        # Verbind de sliders met hun respectievelijke attributen/states en forceer een reset
        # Deze sliders blijven globaal voor hun specifieke effecten
        self.sliders["Knight Rider Length"][1].valueChanged.connect(lambda v: (setattr(self, 'knight_rider_length', v), self.force_effect_reset_on_all_actions()))
        self.sliders["Meteor Width"][1].valueChanged.connect(lambda v: (self.meteor_state.update({'width': v}), self.force_effect_reset_on_all_actions()))
        self.sliders["Spark Intensity"][1].valueChanged.connect(lambda v: (self.meteor_state.update({'spark_intensity': v}), self.force_effect_reset_on_all_actions()))
        self.sliders["Running Line Width"][1].valueChanged.connect(lambda v: (self.running_line_state.update({'width': v}), self.force_effect_reset_on_all_actions()))
        self.sliders["Running Line Count"][1].valueChanged.connect(lambda v: (self.running_line_state.update({'count': v}), self.force_effect_reset_on_all_actions()))
        self.sliders["Sparkle Density"][1].valueChanged.connect(lambda v: (self.christmas_snow_state.update({'density': v}), self.force_effect_reset_on_all_actions()))
        self.sliders["Flag Width 1"][1].valueChanged.connect(lambda v: (self.flag_state['widths'].__setitem__(0, v), self.force_effect_reset_on_all_actions()))
        self.sliders["Flag Width 2"][1].valueChanged.connect(lambda v: (self.flag_state['widths'].__setitem__(1, v), self.force_effect_reset_on_all_actions()))
        self.sliders["Flag Width 3"][1].valueChanged.connect(lambda v: (self.flag_state['widths'].__setitem__(2, v), self.force_effect_reset_on_all_actions()))


        for label, slider in self.sliders.values():
            control_layout.addWidget(label)
            control_layout.addWidget(slider)

        # Knoppen voor Undo/Redo en Export
        control_layout.addWidget(QPushButton("Ongedaan Maken", clicked=self.undo_action))
        control_layout.addWidget(QPushButton("Opnieuw Uitvoeren", clicked=self.redo_action))
        control_layout.addWidget(QPushButton("Exporteer GIF", clicked=self.export_gif))
        
        # Extra knoppen die rechtsonderin mogen
        control_layout.addWidget(QPushButton("Roteer Links", clicked=lambda: self.rotate_image(-90)))
        control_layout.addWidget(QPushButton("Roteer Rechts", clicked=lambda: self.rotate_image(90)))
        control_layout.addWidget(QPushButton("Wis Afbeelding", clicked=self.clear_image))

        self.change_effect() # Initialiseer de zichtbaarheid van de sliders
        self.change_mode() # Initialiseer de tekenmodus

    def set_current_action_brightness(self, value):
        """Stelt de helderheid in voor de geselecteerde actie of de standaardhelderheid."""
        brightness_val = value / 100.0
        if self.selected_action_index != -1:
            self.actions[self.selected_action_index]['brightness'] = brightness_val
            self.actions[self.selected_action_index]['reset_effect_state'] = True
        else:
            self.default_brightness = brightness_val
        self.update_drawing()

    def set_current_action_speed(self, value):
        """Stelt de snelheid in voor de geselecteerde actie of de standaardsnelheid."""
        if self.selected_action_index != -1:
            self.actions[self.selected_action_index]['speed'] = value
            self.actions[self.selected_action_index]['reset_effect_state'] = True
        else:
            self.default_speed = value
        self.update_drawing()

    def update_ui_for_selected_action(self):
        """
        Werkt de UI-sliders bij om de helderheid en snelheid van de geselecteerde actie weer te geven.
        Als er geen actie is geselecteerd, worden de standaardwaarden weergegeven.
        """
        if self.selected_action_index != -1:
            selected_action = self.actions[self.selected_action_index]
            # Blokkeer signalen tijdelijk om ongewenste triggering te voorkomen
            self.brightness_slider.blockSignals(True)
            self.speed_slider.blockSignals(True)

            self.brightness_slider.setValue(int(selected_action.get('brightness', self.default_brightness) * 100))
            self.speed_slider.setValue(selected_action.get('speed', self.default_speed))

            self.brightness_slider.blockSignals(False)
            self.speed_slider.blockSignals(False)
        else:
            # Geen actie geselecteerd, toon standaardwaarden
            self.brightness_slider.blockSignals(True)
            self.speed_slider.blockSignals(True)

            self.brightness_slider.setValue(int(self.default_brightness * 100))
            self.speed_slider.setValue(self.default_speed)

            self.brightness_slider.blockSignals(False)
            self.speed_slider.blockSignals(False)
        
        # Roep change_effect aan om de zichtbaarheid van context-afhankelijke sliders te updaten
        # Dit is belangrijk omdat de effecttype van de geselecteerde lijn de zichtbaarheid beïnvloedt.
        self.change_effect() # Dit zal de juiste sliders tonen/verbergen

    def force_effect_reset_on_all_actions(self):
        """
        Stelt een vlag in voor alle acties om hun effectinstanties opnieuw te initialiseren.
        Dit is nodig wanneer een globale sliderwaarde verandert die van invloed is op effecten.
        """
        for action in self.actions:
            action['reset_effect_state'] = True
        # update_drawing wordt al aangeroepen via de timer, dus geen extra aanroep nodig hier.

    def timer_update(self):
        """
        Update de animatiefase en roept de tekenfunctie aan.
        De interne staat van de effecten wordt nu beheerd binnen de effectklassen zelf.
        """
        # Alle animatietoestand updates zijn nu verplaatst naar de effectklassen zelf.
        # De timer hoeft alleen de tekening bij te werken.
        self.update_drawing()

    def update_drawing(self):
        """
        Verwijdert bestaande tekeningen en tekent de LED-lijnen opnieuw
        op basis van het geselecteerde effect en de parameters.
        """
        # Verwijder alle bestaande segmenten
        for item in self.segment_items:
            self.plot_widget.removeItem(item)
        self.segment_items.clear()
        # Verwijder bewerkingspunten
        for item in self.edit_points_items:
            self.plot_widget.removeItem(item)
        self.edit_points_items.clear()
        
        all_actions_to_draw = self.actions[:] # Maak een kopie van de opgeslagen acties

        # Als we actief tekenen, voeg dan de huidige actie toe voor directe weergave
        if self.current_action and len(self.current_action["points"]) > 0 and self.drawing:
            # Voeg de huidige actie toe aan de lijst die getekend moet worden
            # Zonder resampling om een vloeiende "kwast" ervaring te geven
            all_actions_to_draw.append(self.current_action)

        if not all_actions_to_draw:
            return

        # Teken alle acties
        for action_idx, action in enumerate(all_actions_to_draw):
            pts = action["points"] # Dit zijn de originele, onbewerkte punten
            if len(pts) < 2:
                # Voor "Lijn Tekenen" in de eerste klik fase, kan er maar een punt zijn
                if action == self.current_action and self.draw_mode == "Lijn Tekenen" and len(pts) == 1:
                    # Teken het startpunt als een klein bolletje
                    point_item = pg.ScatterPlotItem([pts[0][0]], [pts[0][1]], size=8, brush=pg.mkBrush('g'), pen=pg.mkPen('w', width=1))
                    self.plot_widget.addItem(point_item)
                    self.segment_items.append(point_item)
                continue # Minimaal 2 punten nodig voor de meeste effecten/lijnen

            base_color = action.get("color", self.led_color)
            
            # Bereken de totale lengte van de lijn voor een consistente LED-dichtheid
            total_line_length = 0
            for k in range(len(pts) - 1):
                total_line_length += distance(pts[k], pts[k+1])

            # Definieer een gewenste LED-dichtheid (bijv. 1 LED per 5 pixels)
            LED_PIXELS_PER_UNIT = 5 # Dit kan worden aangepast voor meer of minder "LED's" per lengte-eenheid
            
            # Bereken het *ideale* aantal LED's op basis van lengte en gewenste dichtheid
            ideal_num_leds = int(total_line_length / LED_PIXELS_PER_UNIT)

            # Zorg voor een minimum en maximum aantal LED's
            MIN_LEDS = 10 # Minimum aantal LED's om effecten goed te laten zien
            MAX_LEDS = 1000 # Maximum aantal LED's om prestaties te garanderen
            num_leds_for_this_line = max(MIN_LEDS, min(MAX_LEDS, ideal_num_leds))
            
            # Zorg ervoor dat num_leds_for_this_line minimaal 2 is om IndexError te voorkomen
            num_leds_for_this_line = max(2, num_leds_for_this_line)

            # Bereken het interval voor resampling op basis van het gewenste aantal LED's
            resampling_interval = total_line_length / (num_leds_for_this_line - 1) if num_leds_for_this_line > 1 else 1.0
            if resampling_interval <= 0: resampling_interval = 1.0 # Voorkom negatieve of nul interval

            # Bepaal de punten die gebruikt moeten worden voor de effectberekening EN de visuele weergave
            # Deze set van punten is nu uniform voor beide doeleinden.
            points_for_effect_and_visual = resample_points(pts, resampling_interval)
            
            # Pas smoothing toe als het een voltooide 'Vrij Tekenen' lijn is
            if action['mode'] == "Vrij Tekenen" and not self.drawing:
                points_for_effect_and_visual = smooth_points(points_for_effect_and_visual, window=5)
            
            # Update num_leds_for_this_line naar het werkelijke aantal punten dat is teruggegeven
            num_leds_for_this_line = len(points_for_effect_and_visual)


            effect_name = self.effect_names[self.effect_combo.currentIndex()]
            EffectClass = get_effect_class(effect_name)
            ParamsModel = None
            if effect_name == "Static": ParamsModel = StaticParams
            elif effect_name == "Breathing": ParamsModel = BreathingParams
            elif effect_name == "Knight Rider": ParamsModel = KnightRiderParams
            elif effect_name == "Meteor": ParamsModel = MeteorParams
            elif effect_name == "Multicolor": ParamsModel = MulticolorParams
            elif effect_name == "Running Line": ParamsModel = RunningLineParams
            elif effect_name == "Christmas Snow": ParamsModel = ChristmasSnowParams
            elif effect_name == "Flag": ParamsModel = FlagParams

            # Haal de snelheid en helderheid op van de huidige actie
            current_action_speed = action.get('speed', self.default_speed)
            current_action_brightness = action.get('brightness', self.default_brightness)

            # Bereid params_data voor op basis van het huidige effect en globale sliderwaarden
            params_data = {}
            if effect_name == "Static":
                params_data = {"color": [Color(red=base_color[0], green=base_color[1], blue=base_color[2])], "brightness": int(current_action_brightness * 100)}
            elif effect_name == "Breathing":
                params_data = {"color": [Color(red=base_color[0], green=base_color[1], blue=base_color[2])], "brightness": int(current_action_brightness * 100)}
            elif effect_name == "Knight Rider":
                params_data = {"color": [Color(red=base_color[0], green=base_color[1], blue=base_color[2])], "brightness": int(current_action_brightness * 100), "line_length": self.knight_rider_length}
            elif effect_name == "Meteor":
                params_data = {"color": [Color(red=base_color[0], green=base_color[1], blue=base_color[2])], "brightness": int(current_action_brightness * 100), "meteor_width": self.meteor_state['width'], "spark_intensity": self.meteor_state['spark_intensity']}
            elif effect_name == "Multicolor":
                params_data = {"brightness": int(current_action_brightness * 100)}
            elif effect_name == "Running Line":
                params_data = {
                    "color": [Color(red=base_color[0], green=base_color[1], blue=base_color[2])],
                    "brightness": int(current_action_brightness * 100),
                    "line_width": self.running_line_state['width'],
                    "number_of_lines": self.running_line_state['count'],
                    "background_color": Color(red=0, green=0, blue=0)
                }
            elif effect_name == "Christmas Snow":
                params_data = {
                    "brightness": int(current_action_brightness * 100),
                    "red_chance": self.christmas_snow_state['density'],
                    "dark_green_chance": self.christmas_snow_state['density']
                }
            elif effect_name == "Flag":
                params_data = {
                    "color": [Color(red=c[0], green=c[1], blue=c[2]) for c in self.flag_state['colors']],
                    "width": self.flag_state['widths'],
                    "background_color": Color(red=self.flag_state['background_color'][0], green=self.flag_state['background_color'][1], blue=self.flag_state['background_color'][2]),
                    "brightness": int(current_action_brightness * 100)
                }
            
            # Initialiseer of update de effect instantie voor DEZE lijn
            if EffectClass and ParamsModel:
                if 'effect_instance' not in action or not isinstance(action['effect_instance'], EffectClass) or action.get('reset_effect_state', False):
                    try:
                        effect_params_instance = ParamsModel(**params_data)
                        model = EffectModel(
                            params=effect_params_instance,
                            frame_skip=0,
                            fps=30 * (current_action_speed / 5.0), # Gebruik de snelheid van de actie
                            num_leds=num_leds_for_this_line # Gebruik num_leds gebaseerd op geresamplede punten
                        )
                        action['effect_instance'] = EffectClass(model)
                        action['reset_effect_state'] = False
                    except Exception as e:
                        print(f"Fout bij het maken van ParamsModel of EffectModel voor {effect_name} (lijn {action_idx}): {e}")
                        action['effect_instance'] = None
                
                if action.get('effect_instance'):
                    current_effect = action['effect_instance']
                    try:
                        updated_params_instance = ParamsModel(**params_data)
                        current_effect.params = updated_params_instance
                        current_effect.num_leds = num_leds_for_this_line # Update num_leds hier ook
                        current_effect.fps = 30 * (current_action_speed / 5.0) # Update fps hier ook
                    except Exception as e:
                        print(f"Fout bij het updaten van parameters voor {effect_name} (lijn {action_idx}): {e}")
                        action['effect_instance'] = None

            # Teken het frame van het effect
            if action.get('effect_instance'):
                current_effect = action['effect_instance']
                frame = current_effect.get_next_frame() # Dit frame heeft kleuren voor num_leds_for_this_line

                num_visual_segments = len(points_for_effect_and_visual) - 1
                if num_visual_segments <= 0: continue

                for j in range(num_visual_segments):
                    x1, y1 = points_for_effect_and_visual[j]
                    x2, y2 = points_for_effect_and_visual[j+1]

                    # Map de huidige visuele segmentindex (j) naar een index in het effect's frame
                    # Dit zorgt ervoor dat de kleuren van het effectframe correct worden uitgesmeerd
                    # over de visuele segmenten van de lijn.
                    effect_frame_index = int((j / num_visual_segments) * (len(frame) - 1))
                    effect_frame_index = min(effect_frame_index, len(frame) - 1) # Zorg ervoor dat het binnen de grenzen blijft

                    r, g, b, w = frame[effect_frame_index]
                    color_for_drawing = (r, g, b)
                    
                    pen = pg.mkPen(color=color_for_drawing, width=self.line_width, antialias=True)
                    segment_item = self.plot_widget.plot([x1, x2], [y1, y2], pen=pen)
                    self.segment_items.append(segment_item)
            else:
                # Terugval naar effen basiskleur lijn als effect niet kan worden toegepast
                for j in range(len(points_for_effect_and_visual) - 1):
                    x1, y1 = points_for_effect_and_visual[j]
                    x2, y2 = points_for_effect_and_visual[j+1]
                    pen = pg.mkPen(color=base_color, width=self.line_width, antialias=True)
                    segment_item = self.plot_widget.plot([x1, x2], [y1, y2], pen=pen)
                    self.segment_items.append(segment_item)
                
        # Teken bewerkingspunten als de modus "Lijn Bewerken" is
        if self.draw_mode == "Lijn Bewerken" and self.selected_action_index != -1:
            selected_action = self.actions[self.selected_action_index]
            for idx, (x, y) in enumerate(selected_action["points"]):
                # Teken een cirkel voor elk bewerkingspunt
                point_item = pg.ScatterPlotItem([x], [y], size=10, brush=pg.mkBrush('b'), pen=pg.mkPen('w', width=1))
                self.plot_widget.addItem(point_item)
                self.edit_points_items.append(point_item)

    def change_effect(self):
        """
        Wordt aangeroepen wanneer het geselecteerde effect in de dropdown verandert.
        Past de zichtbaarheid van de sliders aan op basis van het geselecteerde effect.
        """
        self.effect_index = self.effect_combo.currentIndex()
        effect_name = self.effect_names[self.effect_index]
        
        # Invalideer bestaande effect instanties voor alle lijnen
        # Dit dwingt een herinitialisatie af in de volgende update_drawing cyclus
        for action in self.actions:
            action['effect_instance'] = None

        # Bepaal welke sliders zichtbaar moeten zijn voor het geselecteerde effect
        # Let op: Speed en Brightness zijn nu altijd zichtbaar omdat ze per-lijn zijn.
        visible = {
            "Knight Rider Length": effect_name == "Knight Rider",
            "Meteor Width": effect_name == "Meteor",
            "Spark Intensity": effect_name == "Meteor",
            "Running Line Width": effect_name == "Running Line",
            "Running Line Count": effect_name == "Running Line",
            "Sparkle Density": effect_name == "Christmas Snow",
            "Flag Width 1": effect_name == "Flag",
            "Flag Width 2": effect_name == "Flag",
            "Flag Width 3": effect_name == "Flag",
        }

        for name, (label, slider) in self.sliders.items():
            label.setVisible(visible.get(name, False))
            slider.setVisible(visible.get(name, False))
        
        # Pas de zichtbaarheid van vlag specifieke kleurkiezers aan
        is_flag_effect = (effect_name == "Flag")
        self.flag_segment_label.setVisible(is_flag_effect)
        self.flag_segment_combo.setVisible(is_flag_effect)
        self.choose_flag_color_button.setVisible(is_flag_effect)

        self.update_drawing() # Teken de nieuwe effectweergave

    def choose_led_color(self):
        """
        Opent een kleurkiezer en stelt de algemene LED-kleur in.
        """
        color = QColorDialog.getColor()
        if color.isValid():
            new_color = (color.red(), color.green(), color.blue())
            self.led_color = new_color
            # Update de kleur van ALLE bestaande acties
            for action in self.actions:
                action['color'] = new_color
                # Invalideer ook de effect instantie om ervoor te zorgen dat de kleurwijziging wordt toegepast
                action['effect_instance'] = None
            self.update_drawing()

    def set_selected_flag_segment(self, index):
        """
        Stelt het geselecteerde vlagsegment in voor kleurbewerking.
        """
        self.selected_flag_segment = index

    def choose_flag_segment_color(self):
        """
        Opent een kleurkiezer en stelt de kleur in voor het geselecteerde vlagsegment.
        """
        color = QColorDialog.getColor()
        if color.isValid():
            new_color = (color.red(), color.green(), color.blue())
            if 0 <= self.selected_flag_segment < len(self.flag_state['colors']):
                self.flag_state['colors'][self.selected_flag_segment] = new_color
            self.update_drawing()

    def load_image(self):
        """
        Laadt een achtergrondafbeelding voor de visualizer.
        """
        file_path, _ = QFileDialog.getOpenFileName(self, "Afbeelding Laden", "", "Afbeeldingen (*.png *.jpg *.jpeg *.bmp)")
        if file_path:
            self.image = np.array(Image.open(file_path).convert("RGBA"))
            self.clear_everything() # Wis lijnen bij het laden van een nieuwe afbeelding
            self.update_display()
            self.plot_widget.getViewBox().autoRange() # Pas de weergave aan op de afbeelding

    def update_display(self):
        """
        Update de weergave van de achtergrondafbeelding.
        """
        if self.image is not None:
            if not hasattr(self, 'image_item') or self.image_item is None:
                self.image_item = pg.ImageItem()
                self.plot_widget.addItem(self.image_item)
            
            # Afbeeldingen moeten mogelijk worden omgedraaid/getransponeerd voor pyqtgraph
            flipped_image = np.flipud(self.image)
            transposed_image = np.transpose(flipped_image, (1, 0, 2))
            self.image_item.setImage(transposed_image)
            h, w, _ = self.image.shape
            self.image_item.setRect(0, 0, w, h) # Stel de grootte en positie van de afbeelding in
        self.update_drawing()

    def clear_everything(self):
        """
        Wist alle getekende lijnen en de undo/redo stapels.
        """
        self.actions, self.current_action = [], None
        self.undo_stack, self.redo_stack = [], []
        self.push_undo_state() # Voeg een lege staat toe aan de undo-stapel
        self.update_drawing()
        
    def clear_image(self):
        """
        Wist de achtergrondafbeelding.
        """
        if hasattr(self, 'image_item') and self.image_item:
            self.plot_widget.removeItem(self.image_item)
            self.image_item = None
        self.image = None
        self.clear_everything() # Wis ook de lijnen

    def merge_lines(self):
        """
        Voegt lijnen samen als hun uiteinden binnen een bepaalde drempel van elkaar liggen.
        Dit gebeurt iteratief totdat er geen verdere samenvoegingen mogelijk zijn.
        """
        if not self.actions:
            return

        self.push_undo_state() # Sla de huidige staat op voor ongedaan maken

        merge_threshold = 25 # Drempel in pixels voor het samenvoegen van lijnen

        merged_something_in_iteration = True
        while merged_something_in_iteration:
            merged_something_in_iteration = False
            lines_to_process = self.actions[:] # Maak een kopie om te itereren
            self.actions = [] # Begin met een lege lijst voor de volgende iteratie

            lines_merged_in_this_pass = set() # Houd bij welke lijnen zijn samengevoegd in deze pass

            for i in range(len(lines_to_process)):
                if i in lines_merged_in_this_pass:
                    continue

                line1 = lines_to_process[i]
                line1_points = line1["points"]
                line1_start = line1_points[0]
                line1_end = line1_points[-1]

                best_merge_candidate = None # (line2_idx, line2_reversed, distance, connection_type)

                for j in range(len(lines_to_process)):
                    if i == j or j in lines_merged_in_this_pass:
                        continue

                    line2 = lines_to_process[j]
                    line2_points = line2["points"]
                    line2_start = line2_points[0]
                    line2_end = line2_points[-1]

                    # Controleer alle 4 mogelijke eindpuntverbindingen
                    # 1. line1_end naar line2_start
                    dist_e1_s2 = distance(line1_end, line2_start)
                    if dist_e1_s2 < merge_threshold:
                        if best_merge_candidate is None or dist_e1_s2 < best_merge_candidate[2]:
                            best_merge_candidate = (j, False, dist_e1_s2, "end1-start2")
                    
                    # 2. line1_end naar line2_end (line2 moet omgedraaid worden)
                    dist_e1_e2 = distance(line1_end, line2_end)
                    if dist_e1_e2 < merge_threshold:
                        if best_merge_candidate is None or dist_e1_e2 < best_merge_candidate[2]:
                            best_merge_candidate = (j, True, dist_e1_e2, "end1-end2")

                    # 3. line1_start naar line2_start (line1 moet omgedraaid worden)
                    dist_s1_s2 = distance(line1_start, line2_start)
                    if dist_s1_s2 < merge_threshold:
                        if best_merge_candidate is None or dist_s1_s2 < best_merge_candidate[2]:
                            best_merge_candidate = (j, True, dist_s1_s2, "start1-start2") # line1 wordt omgedraaid

                    # 4. line1_start naar line2_end (line1 moet omgedraaid worden)
                    dist_s1_e2 = distance(line1_start, line2_end)
                    if dist_s1_e2 < merge_threshold:
                        if best_merge_candidate is None or dist_s1_e2 < best_merge_candidate[2]:
                            best_merge_candidate = (j, False, dist_s1_e2, "start1-end2") # line1 wordt omgedraaid

                if best_merge_candidate:
                    line2_idx, line2_reversed, dist_val, connection_type = best_merge_candidate
                    line2_to_merge_points = lines_to_process[line2_idx]["points"]

                    merged_points = []
                    if connection_type == "end1-start2":
                        merged_points = line1_points + line2_to_merge_points
                    elif connection_type == "end1-end2":
                        merged_points = line1_points + line2_to_merge_points[::-1] # Draai line2 om
                    elif connection_type == "start1-start2":
                        merged_points = line1_points[::-1] + line2_to_merge_points # Draai line1 om
                    elif connection_type == "start1-end2":
                        merged_points = line1_points[::-1] + line2_to_merge_points[::-1] # Draai beide om

                    # Maak een nieuwe actie voor de samengevoegde lijn
                    merged_action = {
                        "mode": "Vrij Tekenen", # Samengevoegde lijnen worden als vrij getekend beschouwd
                        "points": merged_points,
                        "color": line1["color"], # Behoud de kleur van de eerste lijn
                        'effect_instance': None,
                        'reset_effect_state': True,
                        'speed': line1.get('speed', self.default_speed), # Behoud snelheid
                        'brightness': line1.get('brightness', self.default_brightness) # Behoud helderheid
                    }
                    self.actions.append(merged_action)
                    lines_merged_in_this_pass.add(i)
                    lines_merged_in_this_pass.add(line2_idx)
                    merged_something_in_iteration = True
                    break # Begin de buitenste lus opnieuw om nieuwe samenvoegingen te vinden
            
            # Voeg lijnen toe die niet zijn samengevoegd in deze pass
            for i in range(len(lines_to_process)):
                if i not in lines_merged_in_this_pass:
                    self.actions.append(lines_to_process[i])
            
            # Als er iets is samengevoegd, gaan we door met de volgende iteratie
            # anders stoppen we. De self.actions lijst is nu de basis voor de volgende pass.

        self.update_drawing()
        print("Lijnen samengevoegd op basis van nabijheid!")


    def push_undo_state(self):
        """
        Voegt de huidige staat van de acties toe aan de undo-stapel.
        """
        self.undo_stack.append(copy.deepcopy(self.actions))
        self.redo_stack.clear() # Wis de redo-stapel bij een nieuwe actie

    def undo_action(self):
        """
        Maakt de laatste actie ongedaan.
        """
        if len(self.undo_stack) > 1:
            self.redo_stack.append(self.undo_stack.pop())
            self.actions = copy.deepcopy(self.undo_stack[-1])
            self.update_drawing()
            self.update_ui_for_selected_action() # Update UI na undo

    def redo_action(self):
        """
        Voert een ongedaan gemaakte actie opnieuw uit.
        """
        if self.redo_stack:
            self.actions = self.redo_stack.pop()
            self.undo_stack.append(copy.deepcopy(self.actions))
            self.update_drawing()
            self.update_ui_for_selected_action() # Update UI na redo
    
    def rotate_image(self, angle):
        """
        Roteert de achtergrondafbeelding.
        """
        if self.image is not None:
            # Gebruik OpenCV voor rotatie
            if angle == 90:
                self.image = cv2.rotate(self.image, cv2.ROTATE_90_CLOCKWISE)
            elif angle == -90:
                self.image = cv2.rotate(self.image, cv2.ROTATE_90_COUNTERCLOCKWISE)
            self.update_display()

    def change_mode(self):
        """
        Verandert de tekenmodus (Vrij Tekenen, Lijn Tekenen, Lijn Bewerken).
        """
        self.draw_mode = self.mode_combo.currentText()
        # Reset selectie wanneer modus verandert
        self.selected_action_index = -1
        self.selected_point_index = -1
        self.update_ui_for_selected_action() # Update UI om standaardwaarden te tonen
        self.update_drawing() # Update de weergave om bewerkingspunten te tonen/verbergen

    def eventFilter(self, source, event):
        """
        Filtert muisgebeurtenissen op de plot widget voor teken- en bewerkingsfunctionaliteit.
        """
        if source == self.plot_widget.viewport():
            if event.type() == QEvent.MouseButtonPress and event.button() == Qt.LeftButton:
                self.handle_mouse_press(event)
                return True
            elif event.type() == QEvent.MouseMove and event.buttons() & Qt.LeftButton:
                self.handle_mouse_move(event)
                return True
            elif event.type() == QEvent.MouseButtonRelease and event.button() == Qt.LeftButton:
                self.handle_mouse_release(event)
                return True
        return super().eventFilter(source, event)
    
    def handle_mouse_press(self, event):
        """
        Verwerkt het indrukken van de muisknop om een nieuwe teken- of bewerkingsactie te starten.
        """
        pos = self.plot_widget.getViewBox().mapSceneToView(event.pos())
        point = (pos.x(), pos.y())
        self.push_undo_state() # Sla de huidige staat op voor ongedaan maken

        if self.draw_mode == "Vrij Tekenen":
            self.drawing = True
            self.current_action = {
                "mode": self.draw_mode,
                "points": [point],
                "color": self.led_color,
                'effect_instance': None,
                'reset_effect_state': True,
                'speed': self.default_speed, # Gebruik standaard snelheid
                'brightness': self.default_brightness # Gebruik standaard helderheid
            }
        elif self.draw_mode == "Lijn Tekenen":
            # Als dit de eerste klik is voor een lijn
            if not self.line_drawing_first_click:
                self.current_action = {
                    "mode": self.draw_mode,
                    "points": [point, point],
                    "color": self.led_color,
                    'effect_instance': None,
                    'reset_effect_state': True,
                    'speed': self.default_speed, # Gebruik standaard snelheid
                    'brightness': self.default_brightness # Gebruik standaard helderheid
                }
                self.line_drawing_first_click = True
                self.drawing = True # Begin met slepen om de lijn te visualiseren
            else: # Dit is de tweede klik, voltooi de lijn
                if self.current_action and len(self.current_action["points"]) == 2:
                    self.current_action["points"][1] = point # Bevestig het eindpunt
                    self.actions.append(self.current_action) # Voeg de voltooide lijn toe
                self.current_action = None
                self.line_drawing_first_click = False
                self.drawing = False # Stop met tekenen na de tweede klik
        elif self.draw_mode == "Lijn Bewerken":
            self.selected_action_index = -1
            self.selected_point_index = -1
            
            # Zoek de dichtstbijzijnde lijn en punt
            min_dist_line = float('inf')
            min_dist_point = float('inf')
            
            for i, action in enumerate(self.actions):
                if action["mode"] in ["Vrij Tekenen", "Lijn Tekenen"]:
                    # Zoek dichtstbijzijnde punt op de lijn
                    for j, p in enumerate(action["points"]):
                        dist = distance(point, p)
                        if dist < min_dist_point and dist < 15: # Binnen 15 pixels van een punt
                            self.selected_action_index = i
                            self.selected_point_index = j
                            min_dist_point = dist
                    
                    # Zoek dichtstbijzijnde lijnsegment (als geen punt geselecteerd)
                    if self.selected_action_index == -1: # Alleen als geen punt is geselecteerd
                        for j in range(len(action["points"]) - 1):
                            p1 = action["points"][j]
                            p2 = action["points"][j+1]
                            dist_to_segment = point_line_distance(point, p1, p2)
                            if dist_to_segment < min_dist_line and dist_to_segment < 10: # Binnen 10 pixels van een lijn
                                self.selected_action_index = i
                                min_dist_line = dist_to_segment

            if self.selected_point_index != -1:
                self.drawing = True # Begin met slepen van punt
                self.drag_start_pos = point
            elif self.selected_action_index != -1:
                self.drawing = True # Begin met slepen van hele lijn
                self.drag_start_pos = point
            
            self.update_ui_for_selected_action() # Update UI om geselecteerde lijnwaarden te tonen
        self.update_drawing()

    def handle_mouse_move(self, event):
        """
        Verwerkt het bewegen van de muis tijdens het tekenen of bewerken.
        """
        if not self.drawing:
            return
        pos = self.plot_widget.getViewBox().mapSceneToView(event.pos())
        point = (pos.x(), pos.y())

        if self.draw_mode == "Vrij Tekenen":
            if self.current_action:
                self.current_action["points"].append(point)
        elif self.draw_mode == "Lijn Tekenen":
            if self.current_action and len(self.current_action["points"]) == 2:
                self.current_action["points"][1] = point
        elif self.draw_mode == "Lijn Bewerken" and self.selected_action_index != -1:
            if self.selected_point_index != -1: # Punt slepen
                self.actions[self.selected_action_index]["points"][self.selected_point_index] = point
                self.actions[self.selected_action_index]['reset_effect_state'] = True # Forceer effect reset
            elif self.drag_start_pos: # Hele lijn slepen
                dx = point[0] - self.drag_start_pos[0]
                dy = point[1] - self.drag_start_pos[1]
                
                new_points = []
                for p_x, p_y in self.actions[self.selected_action_index]["points"]:
                    new_points.append((p_x + dx, p_y + dy))
                self.actions[self.selected_action_index]["points"] = new_points
                self.drag_start_pos = point # Update startpositie voor volgende beweging
                self.actions[self.selected_action_index]['reset_effect_state'] = True # Forceer effect reset
        
        self.update_drawing()

    def handle_mouse_release(self, event):
        """
        Verwerkt het loslaten van de muisknop om een teken- of bewerkingsactie te voltooien.
        """
        # Als we in "Lijn Tekenen" modus zijn en de eerste klik is gedaan,
        # dan is de release van de muis NIET het einde van de actie.
        # Alleen in "Vrij Tekenen" en "Lijn Bewerken" is mouse_release het einde van de actieve tekening/sleep.
        if self.draw_mode == "Lijn Tekenen" and self.line_drawing_first_click and self.drawing:
            # Als de gebruiker alleen klikt zonder te slepen, moet de lijn nog steeds worden getekend
            # Dit is de release na de eerste klik, dus we blijven in tekenmodus
            self.drawing = False # Stop met slepen, maar niet met de lijn tekenen
            self.drag_start_pos = None
            self.update_drawing()
            return # Wacht op de tweede klik


        if self.drawing and self.current_action:
            if self.draw_mode == "Vrij Tekenen":
                if len(self.current_action["points"]) > 1:
                    self.actions.append(self.current_action) # Voeg de nieuwe lijn toe
            # "Lijn Tekenen" wordt nu afgehandeld in handle_mouse_press voor de tweede klik
            
            self.current_action = None
        
        self.drawing = False
        self.drag_start_pos = None

        # Reset selectie-indices na het loslaten van de muis in bewerkingsmodus
        if self.draw_mode == "Lijn Bewerken":
            self.selected_action_index = -1
            self.selected_point_index = -1
            self.update_ui_for_selected_action() # Update UI om standaardwaarden te tonen

        self.update_drawing()

    def export_gif(self):
        """
        Exporteert de animatie als een GIF-bestand met een watermerk.
        """
        file_path, _ = QFileDialog.getSaveFileName(self, "Sla GIF op", "", "GIF Bestanden (*.gif)")
        if not file_path:
            return
        
        duration, fps, frames = 10, 30, []
        self.timer.stop() # Stop de timer tijdens het exporteren
        
        # Laad het watermerk
        watermark_path = "effects/pulseline1.png" # Pad naar het watermerk
        try:
            watermark_image = Image.open(watermark_path).convert("RGBA")
        except FileNotFoundError:
            print(f"Watermerk afbeelding niet gevonden op: {watermark_path}")
            watermark_image = None
        
        # Genereer frames voor de export
        for _ in range(duration * fps):
            self.timer_update() # Update de animatiestatus
            QApplication.processEvents() # Verwerk Qt-events om de UI bij te werken
            pixmap = self.plot_widget.grab() # Maak een screenshot van de plot widget
            image = pixmap.toImage().convertToFormat(QImage.Format_ARGB32)
            
            # Converteer QImage naar NumPy array voor OpenCV
            ptr = image.bits()
            ptr.setsize(image.byteCount())
            arr = np.array(ptr).reshape(image.height(), image.width(), 4)
            frame_cv2 = cv2.cvtColor(arr, cv2.COLOR_BGRA2RGB) # Converteer naar RGB voor imageio

            # Voeg watermerk toe
            if watermark_image:
                frame_pil = Image.fromarray(frame_cv2)
                # Resize watermerk als het te groot is (optioneel)
                wm_width, wm_height = watermark_image.size
                img_width, img_height = frame_pil.size
                
                # Bepaal de positie linksonder
                position = (10, img_height - wm_height - 10) # 10 pixels marge

                # Maak een transparante overlay
                temp_img = Image.new('RGBA', frame_pil.size, (255, 255, 255, 0))
                temp_img.paste(watermark_image, position, watermark_image)
                
                # Combineer de afbeeldingen
                frame_pil = Image.alpha_composite(frame_pil.convert("RGBA"), temp_img)
                frame_cv2 = cv2.cvtColor(np.array(frame_pil), cv2.COLOR_RGBA2RGB) # Terug naar RGB

            frames.append(frame_cv2) # Voeg het frame toe aan de lijst
        
        self.timer.start(10) # Herstart de timer met de snellere frequentie
        
        # Sla de frames op in het gewenste formaat
        imageio.mimsave(file_path, frames, fps=fps)
        print(f"Exporteren naar {file_path} voltooid!")

    # De export_mp4 functie is verwijderd zoals gevraagd
