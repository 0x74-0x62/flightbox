"""conversion: Collection of functions for converting various formats and units."""

__author__ = "Thorsten Biermann"
__copyright__ = "Copyright 2015, Thorsten Biermann"
__email__ = "thorsten.biermann@gmail.com"

METERS_PER_FEET = 0.3048
KNOTS_PER_MPS = 1.94384


def feet_to_meters(feet):
    """
    :param feet: Distance in feet
    :return: Distance in meters
    """

    return feet * METERS_PER_FEET


def meters_to_feet(meters):
    """
    :param meters: Distance in meters
    :return: Distance in feet
    """

    return meters / METERS_PER_FEET


def mps_to_knots(mps):
    """
    :param mps: Speed in meters per second
    :return: Speed in knots
    """

    return mps * KNOTS_PER_MPS


def knots_to_mps(knots):
    """
    :param knots: Speed in knots
    :return: Speed in meters per second
    """

    return knots / KNOTS_PER_MPS


def fpm_to_mps(feet_per_minute):
    """
    :param feet_per_minute: Speed in feet per minute
    :return: Speed in meters per second
    """

    return feet_to_meters(feet_per_minute) / 60.0


def mps_to_fpm(meters_per_second):
    """
    :param meters_per_second: Speed in meters per second
    :return: Speed in feet per minute
    """

    return meters_to_feet(meters_per_second) * 60.0


def nmea_coord_to_degrees(coordinate):
    """
    :param coordinate: Coordinate in NMEA format (DDDMM.MMMM)
    :return: Decimal representation of coordinate in degrees
    """

    # extract degree part
    degrees = float(int(coordinate / 100.0))

    # extract minutes part
    minutes = coordinate - (degrees * 100.0)

    # add minutes to degrees
    degrees += minutes / 60.0

    return degrees


def ogn_coord_to_degrees(coordinate):
    """
    :param coordinate: Coordinate in OGN (APRS) format (DDDMM.MMMM)
    :return: Decimal representation of coordinate in degrees
    """

    # format is identical to NMEA
    return nmea_coord_to_degrees(coordinate)
