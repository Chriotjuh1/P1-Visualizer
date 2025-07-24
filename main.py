import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon

# Importeer de hoofd-class van de applicatie uit visualizer.py
from visualizer import LEDVisualizer

def main():
    """
    Hoofdfunctie om de applicatie te initialiseren en te starten.
    """
    # Schakel High DPI scaling in voor betere weergave op hoge resolutie schermen
    if hasattr(Qt, 'AA_EnableHighDpiScaling'):
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    # Maak de applicatie-instantie
    app = QApplication(sys.argv)
    
    # Probeer het icoon in te stellen (optioneel)
    try:
        app.setWindowIcon(QIcon("logo.ico"))
    except Exception as e:
        print(f"Kon logo.ico niet laden: {e}")

    # Maak en toon het hoofdvenster
    window = LEDVisualizer()
    window.showMaximized() # Start gemaximaliseerd voor een betere ervaring
    
    # Start de event loop
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
