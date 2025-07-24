import sys
from cx_Freeze import setup, Executable

build_exe_options = {
    "packages": ["numpy", "cv2", "PyQt5", "pyqtgraph", "PIL"],
    "include_files": ["logo.ico"],
    "excludes": ["msilib"],  # Voeg 'msilib' toe aan de excludes lijst
    "optimize": 2,
}

base = None
if sys.platform == "win32":
    base = "Win32GUI"

setup(
    name="Pulseline1 Visualizer",
    version="1.0.0",
    description="Visualisatie van LED-effecten",
    options={"build_exe": build_exe_options},
    executables=[Executable("main.py", base=base, icon="logo.ico")]
)