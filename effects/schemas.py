# schemas.py
from pydantic import BaseModel
from typing import List, Tuple, Dict, Any

# Basis Color model voor RGB
class Color(BaseModel):
    red: int
    green: int
    blue: int

# Algemeen model voor effectparameters
class EffectModel(BaseModel):
    params: Any # Dit zal worden vervangen door specifieke Params modellen
    frame_skip: int
    fps: int
    num_leds: int

# Specifieke Params modellen voor elk effect
class StaticParams(BaseModel):
    color: List[Color]
    brightness: int

class BreathingParams(BaseModel):
    color: List[Color]
    brightness: int

class KnightRiderParams(BaseModel):
    color: List[Color]
    brightness: int
    line_length: int

class MeteorParams(BaseModel):
    color: List[Color]
    brightness: int
    meteor_width: int
    spark_intensity: int

class MulticolorParams(BaseModel):
    brightness: int

class RunningLineParams(BaseModel):
    color: List[Color]
    brightness: int
    line_width: int
    number_of_lines: int
    background_color: Color

class ChristmasSnowParams(BaseModel):
    brightness: int
    red_chance: int
    dark_green_chance: int

class FlagParams(BaseModel):
    color: List[Color]
    width: List[int]
    background_color: Color
    brightness: int
