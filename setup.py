import sys
from cx_Freeze import setup,Executable

setup(
    name = "Lotto GUI",
    version = "0.0.1",
    options = {"build_exe": {"packages":["idna"]}},
    description = "A GUI for the Lotto Cryptocurrency",
    executables = [Executable("wallet.py", base = "Win32GUI")])
