#!/usr/bin/python3

# Rack management for the project
# If the CNC has automated changes, you want to create a standard
# rack, so most jobs will reuse the same tool position
# Can also be used to compute the wear of the bits in the rack

# Complex number are used where real part is a drill bit and the imaginary a router

from pathlib import Path
from typing import Dict

from settings import RACK_FILE_PATH

import yaml
import jsonschema
import logging
import os

from settings import DRILLBIT_SIZES, ROUTERBIT_SIZES, CHECK_WITHIN_DIAMETERS_ABSOLUTE_RANGE

# This directory
this_path = Path(__file__).parent
rack_schema_file = this_path / "rack_schema.json"
template_rack_file = this_path / "default_rack_template.yaml"
rack_file = Path(os.path.expanduser(RACK_FILE_PATH))


logger = logging.getLogger(__name__)

Rack = dict[int, complex]
Racks = dict[str, Rack]

class Rack:
    """
    Defines a rack object which behaves like a map where the key is the diameter,
    and an array which maps the rack physically and has a size
    """
    def __init__(self, size=0):
        self.rack = [None] * size
        self.size = size

    def __getitem__(self, key):
        return self.rack[key - 1]

    def __setitem__(self, key, value):
        self.rack[key - 1] = value

    def __delitem__(self, key):
        del self.rack[key - 1]

    def __len__(self):
        return len(self.rack)
    
    def items(self):
        return [(bit, i) for i, bit in enumerate(self.rack, start=1)]

    def keys(self):
        return self.rack

    def values(self):
        return list(range(1, len(self.rack) + 1))
    
    def add_bit(self, bit, position=None):
        if position is None:
            position = self.find_free_position()
        elif position < 1 or position > len(self.rack) + 1:
            raise ValueError("Invalid position")

        if self.rack[position - 1] is not None:
            logger.warning(f"Warning: Slot {position} already occupied with {self.rack[position - 1]}")

        # Chech if the same diameter is not already occupied
        for dia, slot in self.items():
            if bit == dia:
                bit_str = str(bit) if not bit.imag else 'R' + str(bit.imag)
                logger.warning(f"Warning: Bit {bit_str}mm in T{position:02} is already present in the rack at T{slot:02}. This slot will not be used.")
    
        self.rack[position - 1] = bit

    def remove_bit(self, bit):
        self.rack.remove(bit)

    def find_free_position(self):
        for i in range(len(self.rack), 0, -1):
            if self.rack[i - 1] is None:
                continue
            return i + 1
        self.rack.append(None)
        return len(self.rack)
    
    def __repr__(self):
        rack_str = ""
        for (id, dia) in enumerate(self.rack):
            if dia is None:
                rack_str += f"T{id+1:02}:x "
            elif dia.imag:
                rack_str += f"T{id+1:02}:R{dia.imag} "
            else:
                rack_str += f"T{id+1:02}:{dia} "
        return rack_str

class RackManager:
    """
    Object which manages the racks of the CNC.
    If the CNC has automated tool change, this is very important to
    allow the operator from reusing existing racks and speed operations.
    Depending on the CNC, the racks could be loadable, so each Job could
    have its own rack.
    A file (path defined in the settings) is used to create the rack
    configuration.
    The machining code can also create a new rack from scratch, and it
    can be saved.
    Finally for the less fortunate, the rack 'manual', is used to manually
    change the tools, and is considered of size unlimited.
    """
    def __init__(self) -> None:
        # Rack 0 is manual
        self.current_rack = 0

        # Our racks
        self.racks = Racks()

        # Contains the parse Yaml
        rack_data = {}

        # Load the YAML schema
        try:
            with open(rack_schema_file) as schema_file:
                schema = yaml.safe_load(schema_file)
                compiled_schema = jsonschema.Draft7Validator(schema)
        except OSError:
            logger.error(f"The schema file {rack_schema_file.absolute()} could not be opened!")
        except yaml.YAMLError:
            logger.error(f"The schema file {rack_schema_file.absolute()} is not a valid Yaml document!")
            logger.error(e)
        except jsonschema.ValidationError:
            logger.error(f"The schema file {rack_schema_file.absolute()} is invalid!")
        else:
            # Load the rack file
            if rack_file.exists():
                try:
                    with open(rack_file) as rack_yaml:
                        rack_data = yaml.safe_load(rack_yaml)

                    # Perform the validation using the compiled schema
                    errors = list(compiled_schema.iter_errors(rack_data))
                    
                    if errors:
                        rack_data = None
                        for error in errors:
                            logger.error("Rack validation error:" + error.message)
                except OSError:
                    logger.error(f"Failed to open {rack_file.absolute()}. No rack loaded.")
                except yaml.YAMLError as e:
                    logger.error(f"The rack file {rack_file.absolute()} is not a valid Yaml document")
                    logger.error(e)
                else:
                    logger.debug(rack_data)
            else:
                # If we don't have a rack - create one!
                if rack_data is None:
                    logger.info("No suitable rack file found. Creating a new rack file.")

                    from datetime import datetime
                    formatted_date_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                    # Load the template file
                    try:
                        template_content = template_rack_file.read_text()
                        rack_file.write_text(template_content.format(datetime=formatted_date_time, schema_file=rack_schema_file))
                    except:
                        logger.error(f"Failed to create {rack_file.absolute}. Check permissions")

        # Process the rack_data
        self.issue = rack_data.get("issue", 0)
        self.size = rack_data.get("size", 0)
        self.rack = Rack(self.size)
        
        selection = rack_data.get("use")
        racks_definition = rack_data.get("racks", {})

        try:
            if selection:
                if selection not in racks_definition:
                    raise Exception(f"Cannot find the rack named '{selection}' in the 'use' statement.")
                
                if self.size == 0:
                    raise Exception(f"You must specify the size of the racks other than 0.")
                
                for tool_definition in racks_definition[selection]:
                    number = tool_definition.get("number", None)

                    bit_dia = tool_definition.get("drill", tool_definition.get("router"))
                    
                    # Magic values to avoid stupid value done simply
                    if CHECK_WITHIN_DIAMETERS_ABSOLUTE_RANGE(bit_dia):
                        # Check the diameter matches with the declared drill sizes
                        if "router" in tool_definition: 
                            if bit_dia not in ROUTERBIT_SIZES:
                                logger.warn(f"T{number} in the rack '{selection}' has a non standard diameter {bit_dia}.")

                            # Make into imaginary number to indicate it is a router
                            bit_dia *= 1j
                        elif bit_dia not in DRILLBIT_SIZES:
                            logger.warn(f"T{number} in the rack '{selection}' has a non standard diameter {bit_dia}.")

                        # The rack will fill the slot by increment if number is None
                        self.rack.add_bit(bit_dia, number)
                    else:
                        raise Exception(f"Bit size {bit_dia} is not supported")

        except Exception as e:
            logger.error(e)
            # Reset the rack to manuak
            logger.warning("Back rack configuration detected. Using manual rack.")
            self.rack = Rack()

    def add_tool(self, diameter: complex):
        self.rack.add_bit(diameter)

    def save(self, rack_file):
        pass

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')    
    r = RackManager()
    print(r.rack)
