# converts.py
def rgb_to_rgbw(r, g, b):
    """
    Simplistische conversie van RGB naar RGBW voor visualisatiedoeleinden.
    De daadwerkelijke RGBW-conversie is afhankelijk van de specifieke LED-strip en controller.
    Voor weergave retourneren we alleen RGB en een dummy witte component.
    """
    return int(r), int(g), int(b), 0 # Dummy witte component
