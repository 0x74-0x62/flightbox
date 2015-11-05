import logging
import serial

from data_hub.data_hub_item import DataHubItem
from input.input_module import InputModule

__author__ = "Thorsten Biermann"
__copyright__ = "Copyright 2015, Thorsten Biermann"
__email__ = "thorsten.biermann@gmail.com"


class InputSerialGnss(InputModule):
    def __init__(self, data_hub, port, baud_rate):
        # call parent constructor
        super().__init__(data_hub=data_hub)

        # configure logging
        self._logger = logging.getLogger('InputSerialGnss')
        self._logger.info('Initializing')

        # store parameters in object variables
        self._port = port
        self._baud_rate = baud_rate

    def run(self):
        self._logger.info('Running')

        # create serial object
        s = serial.Serial(self._port, self._baud_rate)

        try:
            while True:
                # get line from serial device (blocking call)
                line = s.readline().decode().strip()

                self._logger.debug('Data received: {!r}'.format(line))

                # generate new data hub item and hand over to data hub
                data_hub_item = DataHubItem('nmea', line)
                self._data_hub.put(data_hub_item)
        except(KeyboardInterrupt, SystemExit):
            pass
        finally:
            s.close()

        # close data input queue
        self._data_hub.close()

        self._logger.info('Terminating')
