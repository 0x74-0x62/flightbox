import logging
import time

from data_hub.data_hub_item import DataHubItem
from input.input_module import InputModule

__author__ = "Thorsten Biermann"
__copyright__ = "Copyright 2015, Thorsten Biermann"
__email__ = "thorsten.biermann@gmail.com"


class TestDataGenerator(InputModule):
    def __init__(self, data_hub):
        # call parent constructor
        super().__init__(data_hub=data_hub)

        # configure logging
        self._logger = logging.getLogger('TestDataInput')
        self._logger.info('Initializing')

    def run(self):
        self._logger.info('Running')

        while True:
            try:
                # get new item from data hub
                data_hub_item = DataHubItem('dummy', 'dummy data 12345')

                self._logger.debug('Genereated dummy data ' + str(data_hub_item))

                # hand over data hub item to data hub
                self._data_hub.put(data_hub_item)

                time.sleep(5)

            except(KeyboardInterrupt, SystemExit):
                self._logger.info('Terminating')
                break
