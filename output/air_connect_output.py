import asyncio
from concurrent.futures import ThreadPoolExecutor
import logging

from data_hub.data_hub_item import DataHubItem
from output.output_module import OutputModule

__author__ = "Thorsten Biermann"
__copyright__ = "Copyright 2015, Thorsten Biermann"
__email__ = "thorsten.biermann@gmail.com"


async def input_processor(loop, data_input_queue):
    logger = logging.getLogger('AirConnectOutput.InputProcessor')

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


class AirConnectOutput(OutputModule):
    def __init__(self):
        # call parent constructor
        super().__init__()

        # configure logging
        self._logger = logging.getLogger('AirConnectOutput')
        self._logger.info('Initializing')

    def run(self):
        self._logger.info('Running')

        loop = asyncio.get_event_loop()
        tasks = [
            asyncio.ensure_future(input_processor(loop=loop, data_input_queue=self._data_input_queue))
        ]

        try:
            loop.run_until_complete(asyncio.wait(tasks))
        except(KeyboardInterrupt, SystemExit):
            pass
        finally:
            loop.stop()

        # close data input queue
        self._data_input_queue.close()

        self._logger.info('Terminating')

    def get_desired_content_types(self):
        return(['ANY'])
