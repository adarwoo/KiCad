#!/usr/bin/python3
import pcbnew

from inventory import Inventory
from machining import Machining, MachiningWhat

pcb_file_path = "/home/eng/KiCad/pulsegen/pulsegen.kicad_pcb"
board = pcbnew.LoadBoard(pcb_file_path)

inventory = Inventory(board)
machining = Machining(inventory, MachiningWhat.DRILL_PTH)
gcode = machining.gcode()

print(gcode)
