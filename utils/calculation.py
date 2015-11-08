"""calculation: Description of what calculation does."""

import math

__author__ = "Thorsten Biermann"
__copyright__ = "Copyright 2015, Thorsten Biermann"
__email__ = "thorsten.biermann@gmail.com"


def initial_bearing(lat1_deg, lon1_deg, lat2_deg, lon2_deg):
    lat1_rad = math.radians(lat1_deg)
    lat2_rad = math.radians(lat2_deg)
    lon1_rad = math.radians(lon1_deg)
    lon2_rad = math.radians(lon2_deg)

    diff_lon_rad = lon2_rad - lon1_rad

    bearing_rad = math.atan2(math.sin(diff_lon_rad) * math.cos(lat2_rad), math.cos(lat1_rad) * math.sin(lat2_rad) - math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(diff_lon_rad))
    bearing_deg_360 = (math.degrees(bearing_rad) + 360.0) % 360.0

    # bearing_deg = math.degrees(math.atan2(math.cos(lat1_rad) * math.sin(lat2_rad) - math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(lon2_rad - lon1_rad), math.sin(lon2_rad - lon1_rad) * math.cos(lat2_rad)))
    # bearing_deg_360 = (bearing_deg + 360.0) % 360.0

    return bearing_deg_360


def final_bearing(lat1_deg, lon1_deg, lat2_deg, lon2_deg):
    # calculate initial bearing from end point to start point
    reverse_initial_bearing = initial_bearing(lat2_deg, lon2_deg, lat1_deg, lon1_deg)

    # invert bearing to get final bearing from start point to end point
    final_bearing = (reverse_initial_bearing + 180.0) % 360.0

    return final_bearing


def distance_north(bearing_deg, distance):
    return math.sin(math.radians(90.0 - bearing_deg)) * distance


def distance_east(bearing_deg, distance):
    return math.cos(math.radians(90.0 - bearing_deg)) * distance


def relative_bearing(absolute_bearing, course):
    # calculate angle between course and bearing
    relative_bearing_360 = absolute_bearing - course

    # initialize result
    result = relative_bearing_360

    if relative_bearing_360 > 180.0:
        result = relative_bearing_360 - 360.0
    elif relative_bearing_360 < -180.0:
        result = relative_bearing_360 + 360.0

    return result
