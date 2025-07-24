resultaat = 0

while resultaat == 0:
    try:
        invoer_deelgetal = float(input("Voer hier het deelgetal in: "))
        # Probeer deze code uit te voeren
        resultaat = 10 / invoer_deelgetal
        print(resultaat)
    except ZeroDivisionError:
        # Uitvoeren als er een ZeroDivisionError optreedt
        print("Je kunt niet delen door nul!")
    except ValueError:
        # Uitvoeren als er een ValueError komt
        print("Je kunt niet delen door een letter of een teken!")
