#!/usr/bin/python3

# Provides the 'Machining' class which uses the Inventory to check
#  all machining aspects, like creating the rack and generating the GCode.
# Dimensions are kept as um until the GCode rendering
import re

from math import tan, radians
from enum import IntEnum
from typing import List, Tuple, Dict

from settings import *
from inventory import Inventory, Oblong
from utils import Coordinate, interpolate_points, optimize_travel, M2U, U2M


# Convert mm constants locally in um constants
DRILL_BIT_SIZES_UM = [M2U(s) for s in DRILL_BIT_SIZES_MM]
MAX_DRILL_DEPTH_INTO_BACKBOARD_UM = M2U(MAX_DRILL_DEPTH_INTO_BACKBOARD_MM)
MIN_EXIT_DEPTH_UM = M2U(MIN_EXIT_DEPTH_MM)

# Multiple the diameter by this number to find the length of the tip of the bit
HEIGHT_TO_DIA_RATIO = tan(radians((180-DRILLBIT_POINT_ANGLE_DEGREE)/2))
# Regex to split the rack string
SPLIT_RACK_RE = re.compile(r"T(\d+):(R?[\d.]+)")

MAX_DRILL_BIT_DIAMETER_FOR_CLEAN_EXIT_UM = \
    int(MAX_DRILL_DEPTH_INTO_BACKBOARD_UM - MIN_EXIT_DEPTH_UM) / HEIGHT_TO_DIA_RATIO


class MachiningWhat(IntEnum):
    """ Used to tell the Machining class which holes to do """
    DRILL_PTH = 0b0001        # Includes routing oblongs
    DRILL_NPTH = 0b0010      # Includes routing oblongs
    ROUTE_OUTLINE = 0b0100
    DRILL_NPTH_AND_ROUTE_OUTLINE = DRILL_NPTH | ROUTE_OUTLINE
    DRILL_ALL = DRILL_PTH | DRILL_NPTH
    DRILL_AND_ROUTE_ALL = DRILL_ALL | ROUTE_OUTLINE


def find_nearest_drillbit_size(n, sizes=DRILL_BIT_SIZES_UM, allow_bigger=True):
    """
    Find from the standard size, the nearest bit.
    Grab the neareast smaller and nearest larger and check within acceptable
    margin. The smallest difference wins.
    @param n The diameter to drill
    @param sizes An array of sizes to choose from
    @return The best matching bit size or None
    """
    # Find the nearest number using the min function with a custom key function
    standard_sizes = sorted([s for s in sizes if isinstance(s, int)])
    min_so_far = n
    retval = None
    lower = lambda n: n - n*MAX_DOWNSIZING_PERCENT/100
    upper = lambda n: n + n*MAX_OVERSIZING_PERCENT/100

    # Start with the largest bit - rational : A bigger hole will accomodate the part
    # In most cases, the plating (0.035 nominal) will make the hole smaller in the end
    for s in reversed(standard_sizes):
        # Skip too large of a hole
        if allow_bigger:
            if s > upper(n):
                continue
        elif s > n:
            continue

        # Stop if too small - won't get better!
        if s < lower(n):
            break
        
        # Whole size is ok, promote if difference is less
        if abs(n-s) < min_so_far:
            min_so_far = abs(n-s)
            
            if min_so_far == 0:
                return s
            
            retval = s

    return retval


class DrillCoordinate(Coordinate):
    pass


class RouteVector:
    def __init__(self):
        pass

    def add_segment(start: Coordinate, end: Coordinate):
        pass

    def add_arc(start: Coordinate, end: Coordinate, center: Coordinate, diameter: int):
        pass


class Machining:
    def __init__(self, inventory: Inventory, what_to_do : MachiningWhat):
        # Create a list of drills
        self.inventory = inventory

        # To contain the final rack descrption. Sizes in um
        # The real part of the number is the conventional drillbit, whilst the complex part indicate a router bit
        # The dictionary then points to a list of coordinates to be drilled with this tool
        self.rack = {} # type: Dict[complex, List[Tuple(int,int)]]

        # Warnings to display
        self.warnings = []

        # Create the rack to use
        self.parse_rack_config()

        # Create the rack and start locating the holes and routes
        self.create_tool_rack(what_to_do)

    def parse_rack_config(self):
        # Pick the rack from the configuration (exception if not found)
        rack_str = STANDARD_RACKS_MM.get(USE_RACK_ID)
        
        if rack_str is None:
            self.warn("Invalid rack configuration detected. Defaulting to no rack")
            rack_str = ""

        # Create the rack lookup
        # Use re.findall() to find all matches in the string
        matches = re.findall(SPLIT_RACK_RE, rack_str)

        if not matches:
            self.warn(
                f"Bad syntax in rack {USE_RACK_ID}",
                "Defaulting to manual."
                "It is recommended to ABORT the machining and fix the rack"
            )
        else:
            matches = []

        for tool_number, tool_diameter in matches:
            is_router_bit = tool_diameter.startswith('R')
            tool_diameter = tool_diameter[1:] if is_router_bit else tool_diameter                
            tool_diameter = float(tool_diameter)

            # Check the tool number is not repeated
            if tool_number in self.rack:
                self.warn(
                    f"Bad rack {USE_RACK_ID}: Tool {tool_number} appears more than once",
                    "Ignoring the tool diameter {tool_diameter:.2f}",
                    "It is recommended to ABORT the machining and fix the rack"
                )
                continue

            if 0.1 <= tool_diameter <= 6.0:
                print(f"Tool Number: {tool_number}, Tool Diameter: {tool_diameter:.2f}, Router: {is_router_bit}")
            else:
                self.warn(
                    f"Invalid tool diameter {tool_diameter:.2f} mm for T{tool_number} found in the rack",
                    "Ignoring this tool.",
                    "It is recommended to ABORT the machining and fix the rack"
                )
                continue

            # Make sure the diameter matches with the standard drill sizes - simply warn
            if tool_diameter not in DRILL_BIT_SIZES_MM:
                self.warn(
                    f"T{tool_number} in the rack {USE_RACK_ID} has a non standard diameter {tool_diameter}."
                )

            # Insert into our rack in um
            self.rack[tool_number] = M2U(tool_diameter)

    def warn(self, *args):
        self.warnings.append('\n'.join(args))
    
    def create_tool_rack(self, operation: MachiningWhat):
        # Create a unique list of all the holes sizes
        holes = dict()

        for h in self.inventory.holes:
            c = DrillCoordinate(h.x, h.y)

            if (operation & MachiningWhat.DRILL_PTH and h.pth) or (operation & MachiningWhat.DRILL_NPTH and not h.pth):
                coordinates = holes.setdefault(h.diameter, [])
                coordinates.append(c)

                if isinstance(h, Oblong):
                    # Add an end hole of the distance > 3/4 D - else the bit has nothing to bite into
                    if h.distance >= 3 * h.diameter / 4:
                        coordinates.append(c)

                    # If the distance < 2xdia, add intermediate drills every 1/4dia
                    if h.distance <= 2 * h.diameter:
                        coordinates.extend(interpolate_points((c.x, c.y), (h.x2, h.y2), h.diameter/4))

                    # Is routing required? - Create a simple segment start to end
                    if h.distance > 2 * h.diameter:
                        coordinates = holes.setdefault(1j * h.diameter, [])
                        v = RouteVector()
                        v.add_segment(c, (h.x2, h.y2))
                        coordinates.append(v)

        for bit_dia_um, coordinates in holes.items():
            # Do we have a matching bit currently in our rack?
            dia = find_nearest_drillbit_size(bit_dia_um, self.rack.keys())

            if dia is None:
                # Do we have a spare slot in the rack (yes for manual change)
                if RACK_SIZE==0 or len(self.rack) < RACK_SIZE:
                    # Look for the bit size in the standard set
                    dia = find_nearest_drillbit_size(bit_dia_um)

            if dia is None or dia > MAX_DRILL_BIT_DIAMETER_FOR_CLEAN_EXIT_UM:
                # If not found or too deep - the hole must be routed
                # - but let's drill the largest hole first
                # But to do so - since the router dia can be any smaller size
                # - we need to wait for the drill rack to be completed
                exit_depth_required = U2M(HEIGHT_TO_DIA_RATIO * bit_dia_um + MIN_EXIT_DEPTH_UM)

                self.warn(
                    f"Exit depth required {exit_depth_required}mm",
                    f"is greater than the depth allowed {MAX_DRILL_DEPTH_INTO_BACKBOARD_MM}mm"
                    "Switching to routing"
                )

                # Pick the biggest bit allowed to prepare the hole before routing it
                nearest = find_nearest_drillbit_size(
                    MAX_DRILL_BIT_DIAMETER_FOR_CLEAN_EXIT_UM, DRILL_BIT_SIZES_UM, False)

                if not nearest:
                    nearest = max(DRILL_BIT_SIZES_UM)

                self.rack.setdefault(nearest, [])
                self.rack[nearest].extend(coordinates)

                # Add a routed hole. The size is the final size and will need post-processing to rationalise the routers
                self.rack.setdefault(bit_dia_um*1j, [])
                self.rack[bit_dia_um*1j].extend(coordinates)
            else:
                self.rack.setdefault(dia, [])
                # Add all holes into the rack data
                self.rack[dia].extend(coordinates)

    def get_rack(self):
        return self.rack
    
    def gcode(self):
        # Start with the drills

        # Grab the tools from the rack - sort by smallest to the largest
        pass
