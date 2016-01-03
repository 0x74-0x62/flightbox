"""calculation: Collection of helper functions for calculating certain parameters."""

import math

__author__ = "Thorsten Biermann"
__copyright__ = "Copyright 2015, Thorsten Biermann"
__email__ = "thorsten.biermann@gmail.com"


def initial_bearing(lat1_deg, lon1_deg, lat2_deg, lon2_deg):
    """
    :param lat1_deg: Latitude of first location in degrees
    :param lon1_deg: Longitude of first location in degrees
    :param lat2_deg: Latitude of second location in degrees
    :param lon2_deg: Longitude of second location in degrees
    :return: Initial bearing in degrees from first to second location
    """

    lat1_rad = math.radians(lat1_deg)
    lat2_rad = math.radians(lat2_deg)
    lon1_rad = math.radians(lon1_deg)
    lon2_rad = math.radians(lon2_deg)

    diff_lon_rad = lon2_rad - lon1_rad

    bearing_rad = math.atan2(math.sin(diff_lon_rad) * math.cos(lat2_rad), math.cos(lat1_rad) * math.sin(lat2_rad) - math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(diff_lon_rad))
    bearing_deg_360 = (math.degrees(bearing_rad) + 360.0) % 360.0

    return bearing_deg_360


def final_bearing(lat1_deg, lon1_deg, lat2_deg, lon2_deg):
    """
    :param lat1_deg: Latitude of first location in degrees
    :param lon1_deg: Longitude of first location in degrees
    :param lat2_deg: Latitude of second location in degrees
    :param lon2_deg: Longitude of second location in degrees
    :return: Final bearing in degrees from first to second location (equals inverse initial bearing from second to first location)
    """

    # calculate initial bearing from end point to start point
    reverse_initial_bearing = initial_bearing(lat2_deg, lon2_deg, lat1_deg, lon1_deg)

    # invert bearing to get final bearing from start point to end point
    final_bearing_deg_360 = (reverse_initial_bearing + 180.0) % 360.0

    return final_bearing_deg_360


def distance_north(bearing_deg, distance):
    """
    :param bearing_deg: Bearing in degrees from first to second location
    :param distance: Distance from first to second location
    :return: Northern (Y) component of overall distance
    """
    return math.sin(math.radians(90.0 - bearing_deg)) * distance


def distance_east(bearing_deg, distance):
    """
    :param bearing_deg: Bearing in degrees from first to second location
    :param distance: Distance from first to second location
    :return: Eastern (X) component of overall distance
    """
    return math.cos(math.radians(90.0 - bearing_deg)) * distance


def relative_bearing(absolute_bearing, course):
    """
    :param absolute_bearing: Bearing in degrees between first and second location
    :param course: Course at first location
    :return: Relative bearing in degrees from first to second location, taking into account course at first location
    """

    # calculate angle between course and bearing
    relative_bearing_360 = absolute_bearing - course

    # initialize result
    result = relative_bearing_360

    if relative_bearing_360 > 180.0:
        result = relative_bearing_360 - 360.0
    elif relative_bearing_360 < -180.0:
        result = relative_bearing_360 + 360.0

    return result


def lat_abs_from_rel_flarm_coordinate(abs_location_coordinate, rel_flarm_coordinate):
    """
    :param abs_location_coordinate: See function abs_from_rel_flarm_coordinate
    :param rel_flarm_coordinate: See function abs_from_rel_flarm_coordinate
    :return: See function abs_from_rel_flarm_coordinate
    """
    return abs_from_rel_flarm_coordinate(abs_location_coordinate, rel_flarm_coordinate, 19)


def lon_abs_from_rel_flarm_coordinate(abs_location_coordinate, rel_flarm_coordinate):
    """
    :param abs_location_coordinate: See function abs_from_rel_flarm_coordinate
    :param rel_flarm_coordinate: See function abs_from_rel_flarm_coordinate
    :return: See function abs_from_rel_flarm_coordinate
    """
    return abs_from_rel_flarm_coordinate(abs_location_coordinate, rel_flarm_coordinate, 20)


def abs_from_rel_flarm_coordinate(abs_location_coordinate, rel_flarm_coordinate, data_bit_width):
    """
    :param abs_location_coordinate: Absolute coordinate of FLARM receivers's location in degrees
    :param rel_flarm_coordinate: Relative coordinate as returned by ogn-decode in degrees (assuming receiver location has been configured to 0)
    :param data_bit_width: Bit width of FLARM position data (should be 19 for latitude and 20 for longitude)
    :return: Absolute FLARM coordinate in degrees
    """

    # set FLARM constants
    INT_CONVERSION_FACTOR = 1e7
    LSB_TRUNCATION_BIT_WIDTH = 7

    # convert degrees to integer representation: limit decimal places according to INT_CONVERSION_FACTOR
    abs_location_coordinate_int = int(abs_location_coordinate * INT_CONVERSION_FACTOR)
    rel_flarm_coordinate_int = int(rel_flarm_coordinate * INT_CONVERSION_FACTOR)

    # check if two's complement representation has to be calculated
    if rel_flarm_coordinate_int < 0:
        # remove truncated LSBs of relative FLARM position (shift right by LSB_TRUNCATION_BIT_WIDTH bits)
        rel_flarm_coordinate_int = int(rel_flarm_coordinate_int / (2 ** LSB_TRUNCATION_BIT_WIDTH))

        # calculate two's complement representation
        rel_flarm_coordinate_int = (2 ** data_bit_width) - abs(rel_flarm_coordinate_int)

        # add truncated LSBs again to relative FLARM position (shift left by LSB_TRUNCATION_BIT_WIDTH bits)
        rel_flarm_coordinate_int = int(rel_flarm_coordinate_int * (2 ** LSB_TRUNCATION_BIT_WIDTH))

    # truncate both coordinates
    abs_location_coordinate_int_truncated = int(abs_location_coordinate_int / (2 ** LSB_TRUNCATION_BIT_WIDTH))
    rel_flarm_coordinate_int_truncated = int(rel_flarm_coordinate_int / (2 ** LSB_TRUNCATION_BIT_WIDTH))

    # calculate difference of relative parts of both coordinates (difference of relative part only ensured by bit-wise AND operation)
    delta_rel_flarm_to_location_truncated = (rel_flarm_coordinate_int_truncated - abs_location_coordinate_int_truncated) & ((2 ** data_bit_width) - 1)

    # check if delta is larger than center of current "FLARM sector" and hence needs to be wrapped
    if delta_rel_flarm_to_location_truncated >= (2 ** (data_bit_width - 1)):
        delta_rel_flarm_to_location_truncated -= (2 ** data_bit_width)

    # calculate absolute FLARM position
    abs_flarm_coordinate_int = (abs_location_coordinate_int_truncated + delta_rel_flarm_to_location_truncated) * (2 ** LSB_TRUNCATION_BIT_WIDTH)

    # convert back to degrees
    abs_flarm_coordinate = abs_flarm_coordinate_int / INT_CONVERSION_FACTOR

    return abs_flarm_coordinate
