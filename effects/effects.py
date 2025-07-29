from .schemas import EffectModel

class Effects:
    """
    Basisklasse voor alle LED-effecten, aangepast voor delta-time.
    """
    def __init__(self, model: EffectModel):
        self.model = model
        self.params = model.params
        # We gebruiken nu model.speed in plaats van de oude fps/frame_skip
        self.speed = model.speed
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
        """Wordt aangeroepen wanneer het aantal LEDs verandert."""
        pass

    def get_next_frame(self, delta_time: float):
        """
        Berekent en retourneert de volgende frame van de animatie.
        Deze methode MOET door elke subklasse (elk effect) worden geïmplementeerd.

        :param delta_time: De tijd in seconden sinds de laatste frame.
        :return: Een lijst van [R, G, B, W] lijsten voor elke LED.
        """
        raise NotImplementedError("get_next_frame(delta_time) moet geïmplementeerd worden door subclasses")

# De alias is niet strikt nodig, maar kan behouden blijven voor compatibiliteit
BaseEffect = Effects
