# P1-Visualizer/effects/effects.py

# Importeer de schema's direct, ervan uitgaande dat schemas.py in dezelfde map staat
from .schemas import EffectModel, StaticParams, BreathingParams, KnightRiderParams, MeteorParams, MulticolorParams, RunningLineParams, ChristmasSnowParams, FlagParams

# Importeer de basisklasse Effects vanuit base_effect.py
from .base_effect import Effects 

# Importeer alle specifieke effectklassen direct, ervan uitgaande dat ze in dezelfde map staan
from .static import StaticEffect
from .breathing import BreathingEffect
from .meteor import MeteorEffect
from .multicolor import MulticolorEffect
from .running_line import RunningLineEffect
from .christmas_snow import ChristmasSnowEffect
from .flag import FlagEffect
from .knight_rider import KnightRiderEffect # Importeer KnightRiderEffect vanuit zijn eigen bestand


def get_effect_class(effect_name: str):
    """
    Retourneert de juiste Effect-klasse op basis van de effectnaam.
    """
    effect_map = {
        "Static": StaticEffect,
        "Pulseline": BreathingEffect,
        "Knight Rider": KnightRiderEffect,
        "Meteor": MeteorEffect,
        "Multicolor": MulticolorEffect,
        "Running Line": RunningLineEffect,
        "Christmas Snow": ChristmasSnowEffect,
        "Flag": FlagEffect,
    }
    return effect_map.get(effect_name)