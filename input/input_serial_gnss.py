import logging
import serial
import setproctitle
import time

from data_hub.data_hub_item import DataHubItem
from input.input_module import InputModule

__author__ = "Thorsten Biermann"
__copyright__ = "Copyright 2015, Thorsten Biermann"
__email__ = "thorsten.biermann@gmail.com"


class InputSerialGnss(InputModule):
    """
    Input module that connects to serial GNSS device to get NMEA position data.
    """

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
        setproctitle.setproctitle("flightbox_input_serial_gnss")

        self._logger.info('Running')

        # initialize serial object
        s = None

        while True:
            try:
                # wait before attaching to serial port
                time.sleep(5)

                # create serial object
                s = serial.Serial(self._port, self._baud_rate)

                # read loop
                while True:
                    try:
                        # get line from serial device (blocking call)
                        line = s.readline().decode().strip()
                    except:
                        # in case read was unsuccessful, exit read loop
                        break

                    self._logger.debug('Data received: {!r}'.format(line))

                    # generate new data hub item and hand over to data hub
                    data_hub_item = DataHubItem('nmea', line)
                    self._data_hub.put(data_hub_item)
            except(KeyboardInterrupt, SystemExit):
                # exit re-connect loop in case of termination is requested
                break
            except:
                self._logger.warning('Could not attach to serial port {} with baud rate {:d}'.format(self._port, self._baud_rate))

                # continue in any other exception case
                pass
            finally:
                if s:
                    s.close()

        # close data input queue
        self._data_hub.close()

        self._logger.info('Terminating')
