import bisect


def interpolate_lookup(table, value):
    """
    Given a value, lookup the nearest values from the given table and
    extrapolate a value based on a linear extrapolation
    This function creates a virtual entry in the lookup table and return the virtual row.
    If the value exists in the table, the table entry is returned.
    """
    diameters = sorted(table.keys())
    index = bisect.bisect_left(diameters, value)
    
    # Handle edge cases
    if index == 0:
        return table[diameters[0]]
    if index == len(diameters):
        return table[diameters[-1]]
    
    # Interpolate values
    lower_diameter = diameters[index - 1]
    upper_diameter = diameters[index]
    lower_values = table[lower_diameter]
    upper_values = table[upper_diameter]
    
    lower_percentage = (upper_diameter - value) / (upper_diameter - lower_diameter)
    upper_percentage = 1 - lower_percentage
    
    interpolated_values = tuple(int(l * lower_percentage + u * upper_percentage) 
                                for l, u in zip(lower_values, upper_values))
    
    return interpolated_values
