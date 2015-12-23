import asyncio
import logging
import setproctitle

from data_hub.data_hub_item import DataHubItem
from input.input_module import InputModule

__author__ = "Thorsten Biermann"
__copyright__ = "Copyright 2015, Thorsten Biermann"
__email__ = "thorsten.biermann@gmail.com"


class NetworkSbs1ClientProtocol(asyncio.Protocol):
    """
    SBS1 protocol implementation (client side).
    """

    def __init__(self, loop, data_hub, message_types):
        self._logger = logging.getLogger('InputNetworkSbs1.Client')
        self._logger.debug('Initializing')

        # store arguments in object variables
        self._loop = loop
        self._data_hub = data_hub
        self._message_types = message_types

    def connection_made(self, transport):
        self._logger.info('Connection established to {}'.format(transport.get_extra_info('peername')))

    def data_received(self, data):
        data_string = data.decode().strip()

        self._logger.debug('Data received: {!r}'.format(data_string))

        messages = data_string.splitlines()
        for message in messages:
            try:
                message_type = message.split(',')[1]
                if message_type in self._message_types:
                    data_hub_item = DataHubItem('sbs1', message)
                    self._data_hub.put(data_hub_item)
            except:
                pass

    def connection_lost(self, exc):
        self._logger.debug('Connection terminated')
        self._loop.stop()


@asyncio.coroutine
def connect_loop(loop, data_hub, host_name, port, message_types):
    logger = logging.getLogger('InputNetworkSbs1.ConnectLoop')

    while True:
        try:
            logger.info("Creating new connection")
            yield from loop.create_connection(lambda: NetworkSbs1ClientProtocol(loop=loop, data_hub=data_hub, message_types=message_types), host_name, port)
        except OSError:
            logger.info("Server not up. Retrying to connect in 5 seconds.")
            yield from asyncio.sleep(5)
        else:
            break


class InputNetworkSbs1(InputModule):
    """
    Input module that connects to ADS-B receiver that has an SBS1 interface, like dump1090.
    """

    def __init__(self, data_hub, host_name, port, message_types = None):
        # call parent constructor
        super().__init__(data_hub=data_hub)

        # configure logging
        self._logger = logging.getLogger('InputNetworkSbs1')
        self._logger.info('Initializing')

        # store parameters in object variables
        self._host_name = host_name
        self._port = port
        self._message_types = message_types

    def run(self):
        setproctitle.setproctitle("flightbox_input_network_sbs1")

        self._logger.info('Running')

        # get asyncio loop
        loop = asyncio.get_event_loop()

        try:
            # start loop
            loop.run_until_complete(connect_loop(loop=loop, data_hub=self._data_hub, host_name=self._host_name, port=self._port, message_types=self._message_types))
            loop.run_forever()
        except(KeyboardInterrupt, SystemExit):
            pass
        finally:
            loop.stop()
            loop.close()

        # close data hub queue
        self._data_hub.close()

        self._logger.info('Terminating')
