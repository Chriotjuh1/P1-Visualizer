# In effects/base_effect.py

from .schemas import EffectModel

class Effects:
    def __init__(self, model: EffectModel):
        self.model = model
        self.params = model.params
        self.speed = model.speed
        self._num_leds = model.num_leds
        self.current_frame = 0.0
        self._on_num_leds_change()

    # TOEGEVOEGD: Een standaard implementatie van de functie.
    # Dit zorgt ervoor dat alle effecten deze functie hebben.
    def _on_num_leds_change(self):
        """
        Deze functie wordt aangeroepen als het aantal LEDs verandert.
        Subklassen kunnen deze overschrijven als ze specifieke logica nodig hebben.
        """
        pass

    @property
    def num_leds(self):
        return self._num_leds

    @num_leds.setter
    def num_leds(self, value):
        if self._num_leds != value:
            self._num_leds = value
            self._on_num_leds_change()

    def get_next_frame(self, delta_time: float = 0.0):
        raise NotImplementedError("get_next_frame() must be implemented by subclasses")