import logging
import time

from data_hub.data_hub_item import DataHubItem
from output.output_module import OutputModule

__author__ = "Thorsten Biermann"
__copyright__ = "Copyright 2015, Thorsten Biermann"
__email__ = "thorsten.biermann@gmail.com"


class AirConnectOutput(OutputModule):
    def __init__(self):
        # call parent constructor
        super().__init__()

        # configure logging
        self._logger = logging.getLogger('AirConnectOutput')
        self._logger.info('Initializing')

    def run(self):
        self._logger.info('Running')

        while True:
            try:
                # get new item from data hub
                data_hub_item = self._data_input_queue.get()

                # check if item is a poison pill
                if data_hub_item is None:
                    self._logger.debug('Received poison pill')

                    # exit loop
                    break

                if type(data_hub_item) is DataHubItem:
                    self._logger.debug('Received ' + str(data_hub_item))

            except(KeyboardInterrupt, SystemExit):
                break

        # close data input queue
        self._data_input_queue.close()

        self._logger.info('Terminating')

    def get_desired_content_types(self):
        return(['ANY'])
