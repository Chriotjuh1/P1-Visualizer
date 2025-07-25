from effects.base_effect import BaseEffect
from effects.schemas import EffectModel, StaticParams

class StaticEffect(BaseEffect):
    """
    Een statisch effect dat alle LEDs een vaste kleur en helderheid geeft.
    """
    def __init__(self, model: EffectModel):
        super().__init__(model)
        # Zorg ervoor dat Pydantic het juiste type params herkent voor type hinting.
        self.params: StaticParams = self.params

    def get_next_frame(self):
        """
        Genereert het volgende frame voor het statische effect.
        Leest de kleur en helderheid direct uit self.params voor elke frame.
        """
        # Haal de parameters op bij elke aanroep voor real-time updates.
        color = (self.params.color[0].red, self.params.color[0].green, self.params.color[0].blue)
        brightness = self.params.brightness / 100.0

        # Bereken de uiteindelijke kleur.
        r = int(color[0] * brightness)
        g = int(color[1] * brightness)
        b = int(color[2] * brightness)

        # Geef voor elke LED dezelfde kleur terug.
        return [(r, g, b) for _ in range(self.num_leds)]
