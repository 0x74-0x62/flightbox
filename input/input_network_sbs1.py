import asyncio
import logging

from data_hub.data_hub_item import DataHubItem
from input.input_module import InputModule

__author__ = "Thorsten Biermann"
__copyright__ = "Copyright 2015, Thorsten Biermann"
__email__ = "thorsten.biermann@gmail.com"


class NetworkSbs1ClientProtocol(asyncio.Protocol):
    def __init__(self, loop, data_hub):
        self._logger = logging.getLogger('InputNetworkSbs1.Client')
        self._logger.debug('Initializing')

        # store arguments in object variables
        self._loop = loop
        self._data_hub = data_hub

    def connection_made(self, transport):
        self._logger.debug('Connection established')

    def data_received(self, data):
        data_string = data.decode().strip()

        self._logger.debug('Data received: {!r}'.format(data_string))

        messages = str.split(data_string)
        for message in messages:
            data_hub_item = DataHubItem('sbs1', message)
            self._data_hub.put(data_hub_item)

    def connection_lost(self, exc):
        self._logger.debug('Connection terminated')
        self._loop.stop()


class InputNetworkSbs1(InputModule):
    def __init__(self, data_hub, host_name, port):
        # call parent constructor
        super().__init__(data_hub=data_hub)

        # configure logging
        self._logger = logging.getLogger('InputNetworkSbs1')
        self._logger.info('Initializing')

        # store parameters in object variables
        self._host_name = host_name
        self._port = port

    def run(self):
        self._logger.info('Running')

        # get asyncio loop
        loop = asyncio.get_event_loop()

        network_client = loop.create_connection(lambda: NetworkSbs1ClientProtocol(loop=loop, data_hub=self._data_hub), self._host_name, self._port)

        try:
            # start loop
            loop.run_until_complete(network_client)
            loop.run_forever()
        except(KeyboardInterrupt, SystemExit):
            pass
        finally:
            loop.stop()
            loop.close()

        # close data hub queue
        self._data_hub.close()

        self._logger.info('Terminating')
