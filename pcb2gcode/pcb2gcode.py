#!/usr/bin/python3

__author__ = "guillaume arreckx"
__copyright__ = "Copyright 2023, ARex"
__license__ = "GPL"
__version__ = 3.1
__email__ = "software@arreckx.com"

"""
Example file to convert a PCB to gcode
Note : Work in progress
"""
import pcbnew

from pathlib import Path

from inventory import Inventory
from machining import Machining, MachiningWhat

# Load from this folder
this_path = Path(__file__).resolve().parent
pcb_file_path = this_path.parent / "pulsegen/pulsegen.kicad_pcb"
board = pcbnew.LoadBoard(str(pcb_file_path))

# Create an inventory of all things which could be machined in the PCB
inventory = Inventory(board)

# Create an object to machine PTH only
machining = Machining(inventory, MachiningWhat.DRILL_PTH)

# Generate the GCode
gcode = machining.gcode()

print(gcode)
