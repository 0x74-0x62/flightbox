import datetime
import logging
import time

from data_hub.data_hub_item import DataHubItem
from input.input_module import InputModule

__author__ = "Thorsten Biermann"
__copyright__ = "Copyright 2015, Thorsten Biermann"
__email__ = "thorsten.biermann@gmail.com"


class TestDataGenerator(InputModule):
    """
    Input module that generates test data.
    """

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
                # create new item for data hub
                data_hub_item = DataHubItem('test', 'test data ' + str(datetime.datetime.now()))

                self._logger.debug('Genereated dummy data ' + str(data_hub_item))

                # hand over data hub item to data hub
                self._data_hub.put(data_hub_item)

                time.sleep(5)

            except(KeyboardInterrupt, SystemExit):
                break

        # close data hub queue
        self._data_hub.close()

        self._logger.info('Terminating')
