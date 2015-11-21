"""conversion: Description of what conversion does."""

__author__ = "Thorsten Biermann"
__copyright__ = "Copyright 2015, Thorsten Biermann"
__email__ = "thorsten.biermann@gmail.com"

METERS_PER_FEET = 0.3048
KNOTS_PER_MPS = 1.94384


def feet_to_meters(feet):
    return feet * METERS_PER_FEET


def meters_to_feet(meters):
    return meters / METERS_PER_FEET


def mps_to_knots(mps):
    return mps * KNOTS_PER_MPS


def knots_to_mps(knots):
    return knots / KNOTS_PER_MPS


def fpm_to_mps(feet_per_minute):
    return feet_to_meters(feet_per_minute) / 60.0


def mps_to_fpm(meters_per_second):
    return meters_to_feet(meters_per_second) * 60.0


def nmea_coord_to_degrees(coordinate):
    # extract degree part
    degrees = float(int(coordinate / 100.0))

    # extract minutes part
    minutes = coordinate - (degrees * 100.0)

    # add minutes to degrees
    degrees += minutes / 60.0

    return degrees


def ogn_coord_to_degrees(coordinate):
    # format is identical to NMEA
    return nmea_coord_to_degrees(coordinate)
