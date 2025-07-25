# P1-Visualizer/effects/base_effect.py

# Importeer EffectModel vanuit schemas.py, ervan uitgaande dat schemas.py in dezelfde map staat
from .schemas import EffectModel

class Effects:
    """
    Basisklasse voor alle LED-effecten.
    Definieert de gemeenschappelijke attributen en de interface voor het ophalen van het volgende frame.
    """
    def __init__(self, model: EffectModel):
        self.model = model # Sla het hele model object op
        self.params = model.params
        self.frame_skip = model.frame_skip
        self.fps = model.fps
        self.num_leds = model.num_leds

    def get_next_frame(self):
        """
        Moet worden geïmplementeerd door subklassen om het volgende LED-frame te retourneren.
        """
        raise NotImplementedError("Do not call get next frame on the base class")

# Voeg een alias toe zodat 'BaseEffect' ook geïmporteerd kan worden,
# voor compatibiliteit met andere modules die mogelijk deze naam verwachten.
BaseEffect = Effects
