import asyncio
from concurrent.futures import ThreadPoolExecutor
import logging
import setproctitle
import sys
from threading import Lock

from data_hub.data_hub_item import DataHubItem
from output.output_module import OutputModule

__author__ = "Thorsten Biermann"
__copyright__ = "Copyright 2015, Thorsten Biermann"
__email__ = "thorsten.biermann@gmail.com"


@asyncio.coroutine
def input_processor(loop, data_input_queue, clients, clients_lock):
    logger = logging.getLogger('AirConnectOutput.InputProcessor')

    while True:
        # get executor that can run in the background (and is asyncio-enabled)
        executor = ThreadPoolExecutor(max_workers=1)

        # get new item from data hub
        data_hub_item = yield from loop.run_in_executor(executor, data_input_queue.get)

        # check if item is a poison pill
        if data_hub_item is None:
            logger.debug('Received poison pill')

            # exit loop
            break

        if type(data_hub_item) is DataHubItem:
            logger.debug('Received ' + str(data_hub_item))

            with clients_lock:
                for client in clients:
                    client.send_string_data(str(data_hub_item.get_content_data() + '\r\n'))


class AirConnectServerClientProtocol(asyncio.Protocol):
    """
    AirConnect protocol implementation (server side).
    """

    def __init__(self, clients, clients_lock, password = None):
        self._logger = logging.getLogger('AirConnectOutput.Server')
        self._logger.debug('Initializing')

        # store arguments in object variables
        self._clients = clients
        self._clients_lock = clients_lock
        self._password = password

        # set data forwarding flag
        self._send_data_enabled = True
        if self._password:
            self._send_data_enabled = False

        # initialize flag that indicates that we are waiting for a password input from the client
        self._awaiting_pass = False

    def connection_made(self, transport):
        peername = transport.get_extra_info('peername')
        self._logger.info('New connection from {}'.format(peername))

        # keep transport object
        self._transport = transport

        # add this client to global client set
        with self._clients_lock:
            self._clients.add(self)

        # request password
        if self._password:
            self._transport.write(str.encode('PASS?'))
            self._awaiting_pass = True

    def connection_lost(self, exc):
        self._logger.info('Connection closed to {}'.format(self._transport.get_extra_info('peername')))

        # remove this client from global client set
        with self._clients_lock:
            self._clients.remove(self)

    def data_received(self, data):
        message = data.decode()

        # check if we are waiting for password
        if self._awaiting_pass:
            if message.strip() == self._password:
                self._send_data_enabled = True
                return
            else:
                self._transport.close()

        # pre-process input
        message_strip_lower = message.strip().lower()

        # check for special commands
        if message_strip_lower == 'exit':
            self._transport.close()
        elif message_strip_lower == 'list_clients':
            self._transport.write(str.encode(str(self._clients) + '\r\n'))
        else:
            self._transport.write(data)

    def send_string_data(self, data):
        self.send_data(str.encode(data))

    def send_data(self, data):
        if self._send_data_enabled:
            self._transport.write(data)


class OutputNetworkAirConnect(OutputModule):
    """
    Output module that provides AirConnect network interface. This is used to provide services to navigation software,
    like SkyDemon.
    """

    def __init__(self):
        # call parent constructor
        super().__init__()

        # configure logging
        self._logger = logging.getLogger('AirConnectOutput')
        self._logger.info('Initializing')

        # initialize client set
        self.clients_lock = Lock()
        self.clients = set()

    def run(self):
        setproctitle.setproctitle("flightbox_output_network_airconnect")

        self._logger.info('Running')

        # get asyncio loop
        loop = asyncio.get_event_loop()

        # create server coroutine
        air_connect_server = loop.create_server(lambda: AirConnectServerClientProtocol(clients=self.clients, clients_lock=self.clients_lock, password=None), host='', port=2000)

        # compile task list that will run in loop
        tasks = asyncio.gather(
            asyncio.async(input_processor(loop=loop, data_input_queue=self._data_input_queue, clients=self.clients, clients_lock=self.clients_lock)),
            asyncio.async(air_connect_server)
        )

        try:
            # start loop
            loop.run_until_complete(tasks)
        except(KeyboardInterrupt, SystemExit):
            pass
        except:
            self._logger.exception(sys.exc_info()[0])
            tasks.cancel()
        finally:
            air_connect_server.close()
            loop.stop()

        # close data input queue
        self._data_input_queue.close()

        self._logger.info('Terminating')

    def get_desired_content_types(self):
        return(['nmea', 'flarm'])
