import logging
from multiprocessing import Process

from data_hub.data_hub_item import DataHubItem

__author__ = "Thorsten Biermann"
__copyright__ = "Copyright 2015, Thorsten Biermann"
__email__ = "thorsten.biermann@gmail.com"


class DataHubWorker(Process):
    def __init__(self, data_hub):
        # call parent constructor
        super().__init__()

        # configure logging
        self._logger = logging.getLogger('DataHubWorker')
        self._logger.info('Initializing')

        # set data hub queue
        self._data_hub = data_hub

    def run(self):
        self._logger.info('Running')

        while True:
            try:
                # get new item from data hub
                data_hub_item = self._data_hub.get()

                # check if item is a poison pill
                if data_hub_item is None:
                    # exit loop
                    break

                if type(data_hub_item) is DataHubItem:
                    self._logger.debug('Received ' + str(data_hub_item))
                else:
                    self._logger.warning('Dropping data (wrong data type)')

            except(KeyboardInterrupt, SystemExit):
                self._logger.info('Terminating')
                break
