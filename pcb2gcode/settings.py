#
# Default cnstants used for the CNC
#
from utils import interpolate_lookup
from uniontool_mfg_data import DRILLBIT_DATA_LOOKUP, ROUTERBIT_DATA_LOOKUP


# Maximum allowed spindle speed RPM
MAX_SPINDLE_SPEED_RPM = 24000

# Minimum allowed spindle speed RPM
MIN_SPINDLE_SPEED = 10000

# Rack size in number of active slots (do not count the spare slot for bit exchange)
# If 0 - the change is manual - and no limit is set to the number of bit changes
RACK_SIZE = 0

# Define pre-filled drill racks, identified by a number 1..99. 0 is reserved for manual change.
# The value is a string of space separated "Tx:[R]d" where:
#       x ... The number of the tool from 1 to 999
#       R ... Optional, identifies a router bit
#       d ... The diameter of the drill/router bit in mm
STANDARD_RACKS_MM = {
    # Example 1 : "T1:.4 T2:.5" "T3:.6 T4:.8 T5:1.0 T6:1.2 T7:1.5 T8:R.6 T9:R0.8 T10:R1.5"
}

# Select the rack to use. If the rack size if 0, this has no effect.
# If the rack ID does not exists, create a new rack. Select 0 for manual tool change.
USE_RACK_ID = 0

# Standard drill sizes - Change to match own supplies
DRILLBIT_SIZES_MM = [ 0.5, 0.6, 0.7, 0.8, 1.0, 1.2, 1.4, 1.5, 2.0 ]

# Standard router bits - Change to match own supplier
ROUTERBIT_SIZES_MM = [.8, 1.0, 1.5]

# Max depth to drill into martyr board 
# This may limit the max bit diameter used since the conic shape 
#  may require to drill deeper than allow to have a fully drilled holes
MAX_DEPTH_INTO_BACKBOARD_MM = 1.5

# Drill speed (Union Tool extrapolated data)
MAX_DRILLBIT_RPM = lambda d : interpolate_lookup(DRILLBIT_DATA_LOOKUP, d)[0]

# Max feed rate (Union Tool extrapolated data) - based on optimum drill speed
MAX_DRILLBIT_Z_FEEDRATE = lambda dia_mm : 1000 * (1.5 * dia_mm ** -0.5)

# Max Z feedrate for the CNC
MAX_Z_FEEDRATE_MM_PER_MIN = 2000

# Min feedrate for the CNC
MIN_Z_FEEDRATE_MM_PER_MIN = 200

# Slot drilling pecking distance as ratio of the hole diameter
# So 1/4, means the pecking distance is 1/4 of the hole diameter
# A slot of 2 mm long, drill with a 1mm drill bit, will require 5 holes
SLOT_DRILL_PER_HOLE_WIDTH = 4

# Geometry angle of the drill bit in degree
DRILLBIT_POINT_ANGLE_DEGREE = 135

# Minimum straight shaft exit depth for all sizes (to add to the tip height)
MIN_EXIT_DEPTH_MM = 0.7

# Max oversize in % for a bit if no matching bit is found
# Example: 5 is 5% - so, the largest bit to drill a 1mm hole would be a 1.05mm bit and no more
MAX_OVERSIZING_PERCENT = 5

# Max downsizing for a bit
# Example: 5 is 5% - so, the smallest bit allowed to drill a 1mm hole would be a 0.95mm bit and no less
MAX_DOWNSIZING_PERCENT = 10

# Size of the router bit for routing the edges
EDGE_ROUTER_DIAMETER_MM = 1.5

# Return the recommended router RPM based on the diameter (mm)
ROUTERBIT_SPINDLE_SPEED_FROM_DIAMETER = lambda d: (
    interpolate_lookup(ROUTERBIT_DATA_LOOKUP, d)[0])

# Return the Z feedrate of the router bit based on the diameter (mm)
# Note : This feedrate assumes optimum RPM. If the RPM is less, slow the feed proportionally.
ROUTERBIT_Z_FEEDRATE_FROM_ROUTERBIT_DIAMETER = lambda d: (
    interpolate_lookup(ROUTERBIT_DATA_LOOKUP, d)[2]*1000) # *1000 to convert the m/min in mm/min

# Returns the table feedrate in mm/min of the router bit based on the diameter (mm)
# Note : This feedrate assumes optimum RPM. If the RPM is less, slow the feed proportionally.
ROUTERBIT_TABLE_FEEDRATE_FROM_ROUTERBIT_DIAMETER = lambda d: (
    interpolate_lookup(ROUTERBIT_DATA_LOOKUP, d)[1]*1000) # *1000 to convert the m/min in mm/min

# Return the depth (mm) into the backing board required for the given bit diameter (mm)
ROUTERBIT_BACKBOARD_DEPTH_REQUIRED_FROM_ROUTERBIT_DIAMETER = lambda d: (
    interpolate_lookup(ROUTERBIT_DATA_LOOKUP, d)[3])


# Now override the settings with custom values
import settings_overrides