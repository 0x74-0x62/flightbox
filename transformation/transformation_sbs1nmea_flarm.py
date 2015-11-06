import asyncio
from concurrent.futures import ThreadPoolExecutor
import logging
import pynmea2
from threading import Lock
import time

from data_hub.data_hub_item import DataHubItem
from transformation.transformation_module import TransformationModule

__author__ = "Thorsten Biermann"
__copyright__ = "Copyright 2015, Thorsten Biermann"
__email__ = "thorsten.biermann@gmail.com"


async def input_processor(loop, data_input_queue, aircraft, aircraft_lock, gnss_status, gnss_status_lock):
    logger = logging.getLogger('Sbs1NmeaToFlarmTransformation.InputProcessor')

    while True:
        # get executor that can run in the background (and is asyncio-enabled)
        executor = ThreadPoolExecutor()

        # get new item from data hub
        data_hub_item = await loop.run_in_executor(executor, data_input_queue.get)

        # check if item is a poison pill
        if data_hub_item is None:
            logger.debug('Received poison pill')

            # exit loop
            break

        if type(data_hub_item) is DataHubItem:
            logger.debug('Received ' + str(data_hub_item))

            if data_hub_item.get_content_type() == 'nmea':
                await handle_nmea_data(data_hub_item.get_content_data(), gnss_status, gnss_status_lock)

            if data_hub_item.get_content_type() == 'sbs1':
                await handle_sbs1_data(data_hub_item.get_content_data(), aircraft, aircraft_lock)

async def handle_sbs1_data(data, aircraft, aircraft_lock):
    logger = logging.getLogger('Sbs1NmeaToFlarmTransformation.Sbs1Handler')

    fields = data.split(',')

    msg_type = fields[1]

    # check if message is of interest
    if len(fields) > 16 and msg_type in ['1', '2', '3', '4']:
        icao_id = fields[4]
        callsign = fields[10].strip()
        altitude = fields[11]
        horizontal_speed = fields[12]
        heading = fields[13]
        latitude = fields[14]
        longitude = fields[15]
        vertical_speed = fields[16]

        with aircraft_lock:
            # initialize empty AircraftInfo object if required
            if icao_id not in aircraft.keys():
                aircraft[icao_id] = AircraftInfo()

            # save timestamp
            aircraft[icao_id].last_seen = time.time()

        # handle aircraft identification data
        if msg_type == '1':
            logger.debug("A/C identification: {} callsign={}".format(icao_id, callsign))

            with aircraft_lock:
                aircraft[icao_id].callsign = callsign

        # handle ground position data
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
            logger.debug('Vector: {} h_speed={} heading={} v_speed={}'.format(icao_id, horizontal_speed, heading, vertical_speed))

            with aircraft_lock:
                aircraft[icao_id].h_speed = float(horizontal_speed)
                aircraft[icao_id].v_speed = float(vertical_speed)
                aircraft[icao_id].heading = float(heading)


async def handle_nmea_data(data, gnss_status, gnss_status_lock):
    logger = logging.getLogger('Sbs1NmeaToFlarmTransformation.NmeaHandler')

    # check if message is of interest
    if data.startswith('$GPGGA'):
        message = pynmea2.parse(data)

        logger.info('GPGGA: lat={} {}, lon={} {}, alt={} {}, qual={:d}, n_sat={}, h_dop={}, geoidal_sep={} {}'.format(message.lat, message.lat_dir, message.lon, message.lon_dir, message.altitude, message.altitude_units, message.gps_qual, message.num_sats, message.horizontal_dil, message.geo_sep, message.geo_sep_units))
        # logger.info('GPGGA: lat={} {}, lon={} {}, alt={} {}, qual={:d}, n_sat={}, h_dop={}, geoidal_sep={} {}, dgps_id={}, dgps_age={}'.format(message.lat, message.lat_dir, message.lon, message.lon_dir, message.altitude, message.altitude_units, message.gps_qual, message.num_sats, message.horizontal_dil, message.geo_sep, message.geo_sep_units, message.ref_station_id, message.age_gps_data))
    elif data.startswith('$GPGLL'):
        message = pynmea2.parse(data)

        logger.info('GPGLL: lat={} {}, lon={} {}, status={}, pos_mode={}'.format(message.lat, message.lat_dir, message.lon, message.lon_dir, message.status, message.faa_mode))
    elif data.startswith('$GPVTG'):
        fields = (data.split('*')[0]).split(',')

        if len(fields) > 9:
            cog_t = fields[1]
            cog_m = fields[3]
            h_speed_kt = fields[5]
            h_speed_kph = fields[7]
            pos_mode = fields[9]

            logger.info('GPVTG: cog_t={}, cog_m={}, h_speed_kt={}, h_speed_kph={}, pos_mode={}'.format(cog_t, cog_m, h_speed_kt, h_speed_kph, pos_mode))

async def data_processor(loop, aircraft, aircraft_lock, gnss_status, gnss_status_lock):
    logger = logging.getLogger('Sbs1NmeaToFlarmTransformation.DataProcessor')

    while True:
        logger.debug('Processing data')

        with aircraft_lock:
            for icao_id in sorted(aircraft.keys()):
                current_aircraft = aircraft[icao_id]

                age_in_seconds = time.time() - current_aircraft.last_seen

                logger.debug('{}: cs={}, lat={}, lon={}, alt={}, h_s={}, v_s={}, h={}, a={:.0f}'.format(icao_id, current_aircraft.callsign, current_aircraft.latitude, current_aircraft.longitude, current_aircraft.altitude, current_aircraft.h_speed, current_aircraft.v_speed, current_aircraft.heading, age_in_seconds))

                # delete entries of aircraft that have not been seen for a while
                if age_in_seconds > 30.0:
                    del aircraft[icao_id]

        await asyncio.sleep(1)


class AircraftInfo(object):
    def __init__(self):
        self.callsign = None
        self.latitude = None
        self.longitude = None
        self.altitude = None
        self.h_speed = None
        self.v_speed = None
        self.heading = None
        self.last_seen = None


class GnssStatus(object):
    def __init__(self):
        self.latitude = None
        self.longitude = None
        self.altitude = None
        self.h_speed = None
        self.heading = None
        self.last_update = None


class Sbs1NmeaToFlarmTransformation(TransformationModule):
    def __init__(self, data_hub):
        # call parent constructor
        super().__init__(data_hub=data_hub)

        # configure logging
        self._logger = logging.getLogger('Sbs1NmeaToFlarmTransformation')
        self._logger.info('Initializing')

        # initialize aircraft data structure
        self._aircraft = {}
        self._aircraft_lock = Lock()

        # initialize gnss data structure
        self._gnss_status = GnssStatus()
        self._gnss_status_lock = Lock()

    def run(self):
        self._logger.info('Running')

        # get asyncio loop
        loop = asyncio.get_event_loop()

        # compile task list that will run in loop
        # TODO add data processing task
        # TODO add data cleanup task
        tasks = [
            asyncio.ensure_future(input_processor(loop=loop, data_input_queue=self._data_input_queue, aircraft=self._aircraft, aircraft_lock=self._aircraft_lock, gnss_status=self._gnss_status, gnss_status_lock=self._gnss_status_lock)),
            asyncio.ensure_future(data_processor(loop=loop, aircraft=self._aircraft, aircraft_lock=self._aircraft_lock, gnss_status=self._gnss_status, gnss_status_lock=self._gnss_status_lock))
        ]

        try:
            # start loop
            loop.run_until_complete(asyncio.wait(tasks))
        except(KeyboardInterrupt, SystemExit):
            pass
        finally:
            loop.stop()

        # close data input queue
        self._data_input_queue.close()

        self._logger.info('Terminating')

    def get_desired_content_types(self):
        return(['sbs1', 'nmea'])
