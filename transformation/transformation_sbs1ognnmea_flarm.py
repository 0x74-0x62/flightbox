import asyncio
from concurrent.futures import ThreadPoolExecutor
from geopy.distance import vincenty
import logging
import pynmea2
import re
import setproctitle
import sys
from threading import Lock
import time

from data_hub.data_hub_item import DataHubItem
from transformation.transformation_module import TransformationModule
import utils.conversion, utils.calculation

__author__ = "Thorsten Biermann"
__copyright__ = "Copyright 2015, Thorsten Biermann"
__email__ = "thorsten.biermann@gmail.com"


@asyncio.coroutine
def input_processor(loop, data_input_queue, aircraft, aircraft_lock, gnss_status, gnss_status_lock):
    logger = logging.getLogger('Sbs1OgnNmeaToFlarmTransformation.InputProcessor')

    while True:
        # get executor that can run in the background (and is asyncio-enabled)
        executor = ThreadPoolExecutor(max_workers=1)

        # get new item from data hub
        data_hub_item = yield from loop.run_in_executor(executor, data_input_queue.get)

        # check if item is a poison pill
        if data_hub_item is None:
            logger.debug('Received poison pill')

            # exit loop
            break

        if type(data_hub_item) is DataHubItem:
            logger.debug('Received ' + str(data_hub_item))

            if data_hub_item.get_content_type() == 'nmea':
                yield from handle_nmea_data(data_hub_item.get_content_data(), gnss_status, gnss_status_lock)

            if data_hub_item.get_content_type() == 'sbs1':
                yield from handle_sbs1_data(data_hub_item.get_content_data(), aircraft, aircraft_lock)

            if data_hub_item.get_content_type() == 'ogn':
                yield from handle_ogn_data(data_hub_item.get_content_data(), aircraft, aircraft_lock, gnss_status)


@asyncio.coroutine
def handle_sbs1_data(data, aircraft, aircraft_lock):
    logger = logging.getLogger('Sbs1OgnNmeaToFlarmTransformation.Sbs1Handler')

    try:
        fields = data.split(',')

        msg_type = fields[1]

        # check if message is of interest
        if len(fields) > 16 and msg_type in ['1', '2', '3', '4']:
            icao_id = fields[4]
            callsign = fields[10].strip()
            altitude = fields[11]
            horizontal_speed = fields[12]
            course = fields[13]
            latitude = fields[14]
            longitude = fields[15]
            vertical_speed = fields[16]

            with aircraft_lock:
                # initialize empty AircraftInfo object if required
                if icao_id not in aircraft.keys():
                    aircraft[icao_id] = AircraftInfo()
                    aircraft[icao_id].identifier = icao_id

                # save timestamp
                aircraft[icao_id].last_seen = time.time()

            # handle aircraft identification data
            if msg_type == '1':
                logger.debug("A/C identification: {} callsign={}".format(icao_id, callsign))

                with aircraft_lock:
                    aircraft[icao_id].callsign = callsign

            # handle ground and airborne position data
            elif msg_type == '2' or msg_type == '3':
                position_type = ''
                if msg_type == '2':
                    position_type = 'Ground'
                elif msg_type == '3':
                    position_type = 'Airborne'

                logger.debug('{} position: {} lat={} lon={} alt={}'.format(position_type, icao_id, latitude, longitude, altitude))

                with aircraft_lock:
                    aircraft[icao_id].latitude = float(latitude)
                    aircraft[icao_id].longitude = float(longitude)
                    aircraft[icao_id].altitude = float(altitude)

            # handle velocity data
            elif msg_type == '4':
                logger.debug('Vector: {} h_speed={} course={} v_speed={}'.format(icao_id, horizontal_speed, course, vertical_speed))

                with aircraft_lock:
                    aircraft[icao_id].h_speed = float(horizontal_speed)
                    aircraft[icao_id].v_speed = float(vertical_speed)
                    aircraft[icao_id].course = float(course)
    except ValueError:
        logger.warn('Problem during SBS1 data parsing')
    except:
        logger.exception(sys.exc_info()[0])


@asyncio.coroutine
def handle_ogn_data(data, aircraft, aircraft_lock, gnss_status):
    logger = logging.getLogger('Sbs1OgnNmeaToFlarmTransformation.OgnHandler')

    logger.info('Processing OGN data: {}'.format(data))

    # check if own location is known (required for FLARM position calculation)
    if gnss_status.longitude and gnss_status.latitude:
        try:
            # ICA3D1B5A>APRS,qAR:/133959h0107.07N/00146.75W'259/067/A=003083 !W57! id053D1B5A -039fpm +0.1rot 8.2dB 1e +4.8kHz gps3x3 s6.01 h32 rDD04AF

            data_parts = data.split(' ')

            # get first part
            beacon_data = data_parts[0]

            # get remaining parts
            position_data = data_parts[1:len(data_parts)]

            m = re.match(r"^(.+?)>APRS,(.+?):/(\d{6})+h(\d{4}\.\d{2})(N|S)(.)(\d{5}\.\d{2})(E|W)(.)((\d{3})/(\d{3}))?/A=(\d{6})", beacon_data)
            if m:
                identifier = m.group(1)
                receiver_name = m.group(2)

                timestamp = m.group(3)

                latitude = utils.conversion.ogn_coord_to_degrees(float(m.group(4)))

                if m.group(5) == "S":
                    latitude = -1.0 * latitude

                symbol_table = m.group(6)

                longitude = utils.conversion.ogn_coord_to_degrees(float(m.group(7)))
                if m.group(8) == "W":
                    longitude = -1.0 * longitude

                symbol_code = m.group(9)

                track = 0
                h_speed = 0
                if m.group(10) is not None:
                    track = int(m.group(11))
                    h_speed = int(m.group(12))

                altitude = int(m.group(13))

                if not identifier == 'FlightBox':
                    logger.info('{}: lat={}, lon={}, alt={}, course={:d}, h_speed={:d}'.format(identifier, latitude, longitude, altitude, track, h_speed))

                    with aircraft_lock:
                        # initialize empty AircraftInfo object if required
                        if identifier not in aircraft.keys():
                            aircraft[identifier] = AircraftInfo()
                            aircraft[identifier].identifier = identifier

                        # save data
                        aircraft[identifier].last_seen = time.time()
                        aircraft[identifier].latitude = utils.calculation.lat_abs_from_rel_flarm_coordinate(gnss_status.latitude, latitude)
                        aircraft[identifier].longitude = utils.calculation.lat_abs_from_rel_flarm_coordinate(gnss_status.longitude, longitude)
                        aircraft[identifier].altitude = altitude
                        aircraft[identifier].h_speed = h_speed
                        aircraft[identifier].course = track
                else:
                    logger.debug('Discarding receiver beacon')

            else:
                logger.warn('Problem parsing OGN beacon data: {}'.format(beacon_data))

            # compile matching patterns
            address_pattern = re.compile(r"id(\S{2})(\S{6})")
            climb_rate_pattern = re.compile(r"([\+\-]\d+)fpm")
            turn_rate_pattern = re.compile(r"([\+\-]\d+\.\d+)rot")
            signal_strength_pattern = re.compile(r"(\d+\.\d+)dB")
            error_count_pattern = re.compile(r"(\d+)e")
            coordinates_extension_pattern = re.compile(r"\!W(.)(.)!")
            hear_ID_pattern = re.compile(r"hear(\w{4})")
            frequency_offset_pattern = re.compile(r"([\+\-]\d+\.\d+)kHz")
            gps_status_pattern = re.compile(r"gps(\d+x\d+)")
            software_version_pattern = re.compile(r"s(\d+\.\d+)")
            hardware_version_pattern = re.compile(r"h(\d+)")
            real_id_pattern = re.compile(r"r(\w{6})")
            flightlevel_pattern = re.compile(r"FL(\d{3}\.\d{2})")

            for position_data_part in position_data:
                address_match = address_pattern.match(position_data_part)
                climb_rate_match = climb_rate_pattern.match(position_data_part)
                turn_rate_match = turn_rate_pattern.match(position_data_part)
                signal_strength_match = signal_strength_pattern.match(position_data_part)
                error_count_match = error_count_pattern.match(position_data_part)
                coordinates_extension_match = coordinates_extension_pattern.match(position_data_part)
                hear_ID_match = hear_ID_pattern.match(position_data_part)
                frequency_offset_match = frequency_offset_pattern.match(position_data_part)
                gps_status_match = gps_status_pattern.match(position_data_part)
                software_version_match = software_version_pattern.match(position_data_part)
                hardware_version_match = hardware_version_pattern.match(position_data_part)
                real_id_match = real_id_pattern.match(position_data_part)
                flightlevel_match = flightlevel_pattern.match(position_data_part)

                if address_match is not None:
                    # Flarm ID type byte in APRS msg: PTTT TTII
                    # P => stealth mode
                    # TTTTT => aircraftType
                    # II => IdType: 0=Random, 1=ICAO, 2=FLARM, 3=OGN
                    # (see https://groups.google.com/forum/#!msg/openglidernetwork/lMzl5ZsaCVs/YirmlnkaJOYJ).
                    address_type = int(address_match.group(1), 16) & 0b00000011
                    aircraft_type = (int(address_match.group(1), 16) & 0b01111100) >> 2
                    stealth = ((int(address_match.group(1), 16) & 0b10000000) >> 7 == 1)
                    address = address_match.group(2)

                elif climb_rate_match is not None:
                    climb_rate = int(climb_rate_match.group(1))

                    # save data
                    aircraft[identifier].v_speed = climb_rate

                elif turn_rate_match is not None:
                    turn_rate = float(turn_rate_match.group(1))

                elif signal_strength_match is not None:
                    signal_strength = float(signal_strength_match.group(1))

                elif error_count_match is not None:
                    error_count = int(error_count_match.group(1))

                elif coordinates_extension_match is not None:
                    dlat = int(coordinates_extension_match.group(1)) / 1000
                    dlon = int(coordinates_extension_match.group(2)) / 1000

                    latitude += dlat
                    longitude += dlon

                    # save data
                    aircraft[identifier].latitude = utils.calculation.lat_abs_from_rel_flarm_coordinate(gnss_status.latitude, latitude)
                    aircraft[identifier].longitude = utils.calculation.lat_abs_from_rel_flarm_coordinate(gnss_status.longitude, longitude)

                elif hear_ID_match is not None:
                    pass
                    # heared_aircraft_IDs.append(hear_ID_match.group(1))

                elif frequency_offset_match is not None:
                    frequency_offset = float(frequency_offset_match.group(1))

                elif gps_status_match is not None:
                    gps_status = gps_status_match.group(1)

                elif software_version_match is not None:
                    software_version = float(software_version_match.group(1))

                elif hardware_version_match is not None:
                    hardware_version = int(hardware_version_match.group(1))

                elif real_id_match is not None:
                    real_id = real_id_match.group(1)

                elif flightlevel_match is not None:
                    flightlevel = float(flightlevel_match.group(1))

                else:
                    logger.warn('Problem parsing OGN position data ({}): {}'.format(position_data_part, position_data))

        except ValueError:
            logger.warn('Problem during OGN data parsing')
        except:
            logger.exception(sys.exc_info()[0])


@asyncio.coroutine
def handle_nmea_data(data, gnss_status, gnss_status_lock):
    logger = logging.getLogger('Sbs1OgnNmeaToFlarmTransformation.NmeaHandler')

    try:
        # check if message is of interest
        if data.startswith('$GPGGA'):
            message = pynmea2.parse(data)

            logger.debug('GPGGA: lat={} {}, lon={} {}, alt={} {}, qual={:d}, n_sat={}, h_dop={}, geoidal_sep={} {}'.format(message.lat, message.lat_dir, message.lon, message.lon_dir, message.altitude, message.altitude_units, message.gps_qual, message.num_sats, message.horizontal_dil, message.geo_sep, message.geo_sep_units))
            # logger.info('GPGGA: lat={} {}, lon={} {}, alt={} {}, qual={:d}, n_sat={}, h_dop={}, geoidal_sep={} {}, dgps_id={}, dgps_age={}'.format(message.lat, message.lat_dir, message.lon, message.lon_dir, message.altitude, message.altitude_units, message.gps_qual, message.num_sats, message.horizontal_dil, message.geo_sep, message.geo_sep_units, message.ref_station_id, message.age_gps_data))

            with gnss_status_lock:
                lat = utils.conversion.nmea_coord_to_degrees(float(message.lat))
                if message.lat_dir == 'N':
                    gnss_status.latitude = lat
                elif message.lat_dir == 'S':
                    gnss_status.latitude = -1.0 * lat

                lon = utils.conversion.nmea_coord_to_degrees(float(message.lon))
                if message.lon_dir == 'W':
                    gnss_status.longitude = -1.0 * lon
                elif message.lon_dir == 'E':
                    gnss_status.longitude = lon

                alt_m = float(message.altitude)
                if message.altitude_units == 'M':
                    gnss_status.altitude = utils.conversion.meters_to_feet(alt_m)

        elif data.startswith('$GPGLL'):
            message = pynmea2.parse(data)

            logger.debug('GPGLL: lat={} {}, lon={} {}, status={}, pos_mode={}'.format(message.lat, message.lat_dir, message.lon, message.lon_dir, message.status, message.faa_mode))

            with gnss_status_lock:
                lat = utils.conversion.nmea_coord_to_degrees(float(message.lat))
                if message.lat_dir == 'N':
                    gnss_status.latitude = lat
                elif message.lat_dir == 'S':
                    gnss_status.latitude = -1.0 * lat

                lon = utils.conversion.nmea_coord_to_degrees(float(message.lon))
                if message.lon_dir == 'W':
                    gnss_status.longitude = -1.0 * lon
                elif message.lon_dir == 'E':
                    gnss_status.longitude = lon

        elif data.startswith('$GPVTG'):
            fields = (data.split('*')[0]).split(',')

            if len(fields) > 9:
                cog_t = fields[1]
                cog_m = fields[3]
                h_speed_kt = fields[5]
                h_speed_kph = fields[7]
                pos_mode = fields[9]

                logger.debug('GPVTG: cog_t={}, cog_m={}, h_speed_kt={}, h_speed_kph={}, pos_mode={}'.format(cog_t, cog_m, h_speed_kt, h_speed_kph, pos_mode))

                with gnss_status_lock:
                    # check if values are available before converting
                    if h_speed_kt:
                        gnss_status.h_speed = float(h_speed_kt)
                    if cog_t:
                        gnss_status.course = float(cog_t)
    except ValueError:
        logger.warn('Problem during NMEA data parsing (no fix?)')
    except:
        logger.exception(sys.exc_info()[0])


def generate_flarm_messages(gnss_status, aircraft):
    logger = logging.getLogger('Sbs1OgnNmeaToFlarmTransformation.FlarmGenerator')

    # define parameter limits (given by FLARM protocol)
    DISTANCE_M_MIN = -32768
    DISTANCE_M_MAX = 32767

    # initialize message list
    flarm_messages = []

    # check if positions are known
    if gnss_status.longitude and gnss_status.latitude and aircraft.longitude and aircraft.latitude:
        """ generate PFLAA message """
        # PFLAA,<AlarmLevel>,<RelativeNorth>,<RelativeEast>, <RelativeVertical>,<IDType>,<ID>,<Track>,<TurnRate>,<GroundSpeed>, <ClimbRate>,<AcftType>

        alarm_level = '0'

        # calculate distance and bearing
        gnss_coordinates = (gnss_status.latitude, gnss_status.longitude)
        aircraft_coordinates = (aircraft.latitude, aircraft.longitude)
        distance_m = vincenty(gnss_coordinates, aircraft_coordinates).meters
        initial_bearing = utils.calculation.initial_bearing(gnss_status.latitude, gnss_status.longitude, aircraft.latitude, aircraft.longitude)
        final_bearing = utils.calculation.final_bearing(gnss_status.latitude, gnss_status.longitude, aircraft.latitude, aircraft.longitude)

        # calculate relative distance (north, east)
        distance_north_m = utils.calculation.distance_north(initial_bearing, distance_m)
        distance_east_m = utils.calculation.distance_east(initial_bearing, distance_m)

        # skip aircraft if distance is out of limits
        if not (distance_north_m >= DISTANCE_M_MIN and distance_north_m <= DISTANCE_M_MAX):
            return None
        if not (distance_east_m >= DISTANCE_M_MIN and distance_east_m <= DISTANCE_M_MAX):
            return None

        # set relative distance
        relative_north = '{:.0f}'.format(min(max(distance_north_m, DISTANCE_M_MIN), DISTANCE_M_MAX))
        relative_east = '{:.0f}'.format(min(max(distance_east_m, DISTANCE_M_MIN), DISTANCE_M_MAX))

        logger.debug('{}: dist={:.0f} m, initial_bearing={:.0f} deg, final_bearing={:.0f} deg, dist_n={:.0f} m, dist_e={:.0f} m'.format(aircraft.identifier, distance_m, initial_bearing, final_bearing, distance_north_m, distance_east_m))

        relative_vertical = ''
        if gnss_status.altitude and aircraft.altitude:
            relative_vertical = '{:.0f}'.format(min(max(utils.conversion.feet_to_meters(aircraft.altitude - gnss_status.altitude), DISTANCE_M_MIN), DISTANCE_M_MAX))

        # indicate ICAO identifier
        identifier_type = '1'
        identifier = aircraft.identifier

        if aircraft.callsign:
            identifier_type = '2'
            identifier = aircraft.callsign

        track = ''
        if aircraft.course is not None:
            track = '{:.0f}'.format(min(max(aircraft.course, 0), 359))

        turn_rate = ''

        ground_speed = ''
        if aircraft.h_speed is not None:
            # convert knots to m/s and limit to target range
            ground_speed = '{:.0f}'.format(min(max(utils.conversion.knots_to_mps(aircraft.h_speed), 0), 32767))

        climb_rate = ''
        if aircraft.v_speed is not None:
            # convert ft/min to m/s, limit to target range, and limit to one digit after dot
            climb_rate = '{:.1f}'.format(min(max(utils.conversion.feet_to_meters(aircraft.v_speed * 0.3048) / 60.0, -32.7), 32.7))

        # set type to unknown
        acft_type = '0'

        flarm_message_laa = pynmea2.ProprietarySentence('F', ['LAA', alarm_level, relative_north, relative_east, relative_vertical, identifier_type, identifier, track, turn_rate, ground_speed, climb_rate, acft_type])
        flarm_messages.append(str(flarm_message_laa))
        logger.debug('FLARM message: {}'.format(str(flarm_message_laa)))

        if gnss_status.course:
            """ generate PFLAU message """
            # PFLAU,<RX>,<TX>,<GPS>,<Power>,<AlarmLevel>,<RelativeBearing>,<AlarmType>,<RelativeVertical>,<RelativeDistance>,<ID>

            # indicate number of received devices
            rx = '0'

            # indicate no transmission
            tx = '0'

            # indicate airborne 3D fix
            gps = '2'

            # indicate power OK
            power = '1'

            # indicate no collision within next 18 seconds
            alarm_level = '0'

            # set relative bearing to target
            relative_bearing = ''
            if initial_bearing and gnss_status.course:
                relative_bearing = '{:.0f}'.format(min(max(utils.calculation.relative_bearing(initial_bearing, gnss_status.course), -180), 180))

            # set aircraft alarm
            alarm_type = '2'

            # has already been calculated for LAA message
            # relative_vertical = ''

            # set relative distance to target
            relative_distance = '{:.0f}'.format(min(max(distance_m, 0), 2147483647))

            # has already been defined for LAA message
            # identifier = ''

            flarm_message_laa = pynmea2.ProprietarySentence('F', ['LAU', rx, tx, gps, power, alarm_level, relative_bearing, alarm_type, relative_vertical, relative_distance, identifier])
            flarm_messages.append(str(flarm_message_laa))
            logger.debug('FLARM message: {}'.format(str(flarm_message_laa)))

    if len(flarm_messages) > 0:
        return flarm_messages

    return None

@asyncio.coroutine
def data_processor(loop, data_hub, aircraft, aircraft_lock, gnss_status, gnss_status_lock):
    logger = logging.getLogger('Sbs1OgnNmeaToFlarmTransformation.DataProcessor')

    while True:
        logger.debug('Processing data:')

        with gnss_status_lock:
            logger.debug('GNSS: lat={}, lon={}, alt={}, h_s={}, h={}'.format(gnss_status.latitude, gnss_status.longitude, gnss_status.altitude, gnss_status.h_speed, gnss_status.course))

        with aircraft_lock:
            for icao_id in sorted(aircraft.keys()):
                current_aircraft = aircraft[icao_id]

                age_in_seconds = time.time() - current_aircraft.last_seen

                logger.debug('{}: cs={}, lat={}, lon={}, alt={}, h_s={}, v_s={}, h={}, a={:.0f}'.format(icao_id, current_aircraft.callsign, current_aircraft.latitude, current_aircraft.longitude, current_aircraft.altitude, current_aircraft.h_speed, current_aircraft.v_speed, current_aircraft.course, age_in_seconds))

                # generate FLARM messages
                flarm_messages = generate_flarm_messages(gnss_status=gnss_status, aircraft=current_aircraft)
                if flarm_messages:
                    for flarm_message in flarm_messages:
                        data_hub_item = DataHubItem('flarm', flarm_message)
                        data_hub.put(data_hub_item)

                # delete entries of aircraft that have not been seen for a while
                if age_in_seconds > 30.0:
                    del aircraft[icao_id]

        yield from asyncio.sleep(1)


class AircraftInfo(object):
    def __init__(self):
        self.identifier = None
        self.callsign = None
        self.latitude = None
        self.longitude = None
        self.altitude = None
        self.h_speed = None
        self.v_speed = None
        self.course = None
        self.last_seen = None


class GnssStatus(object):
    def __init__(self):
        self.latitude = None
        self.longitude = None
        self.altitude = None
        self.h_speed = None
        self.course = None
        self.last_update = None


class Sbs1OgnNmeaToFlarmTransformation(TransformationModule):
    def __init__(self, data_hub):
        # call parent constructor
        super().__init__(data_hub=data_hub)

        # configure logging
        self._logger = logging.getLogger('Sbs1OgnNmeaToFlarmTransformation')
        self._logger.info('Initializing')

        # initialize aircraft data structure
        self._aircraft = {}
        self._aircraft_lock = Lock()

        # initialize gnss data structure
        self._gnss_status = GnssStatus()
        self._gnss_status_lock = Lock()

    def run(self):
        setproctitle.setproctitle("flightbox_transformation_sbs1ognnmea_flarm")

        self._logger.info('Running')

        # get asyncio loop
        loop = asyncio.get_event_loop()

        # compile task list that will run in loop
        tasks = asyncio.gather(
            asyncio.async(input_processor(loop=loop, data_input_queue=self._data_input_queue, aircraft=self._aircraft, aircraft_lock=self._aircraft_lock, gnss_status=self._gnss_status, gnss_status_lock=self._gnss_status_lock)),
            asyncio.async(data_processor(loop=loop, data_hub=self._data_hub, aircraft=self._aircraft, aircraft_lock=self._aircraft_lock, gnss_status=self._gnss_status, gnss_status_lock=self._gnss_status_lock))
        )

        try:
            # start loop
            loop.run_until_complete(tasks)
        except(KeyboardInterrupt, SystemExit):
            pass
        except:
            self._logger.exception(sys.exc_info()[0])
            tasks.cancel()
        finally:
            loop.stop()

        # close data input queue
        self._data_input_queue.close()

        self._logger.info('Terminating')

    def get_desired_content_types(self):
        return(['sbs1', 'ogn', 'nmea'])
