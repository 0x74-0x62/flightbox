import asyncio
import datetime
import logging
import re
import setproctitle
import sys
from threading import Lock

from data_hub.data_hub_item import DataHubItem
from input.input_module import InputModule

__author__ = "Thorsten Biermann"
__copyright__ = "Copyright 2015, Thorsten Biermann"
__email__ = "thorsten.biermann@gmail.com"


@asyncio.coroutine
def ogn_aprs_heartbeat(loop, clients, clients_lock, server_name, server_software):
    logger = logging.getLogger('InputNetworkOgnServer.Heartbeat')

    while True:
        heartbeat = '# {} {} {} {}'.format(server_software, datetime.datetime.utcnow().strftime('%d %b %Y %H:%M:%S GMT'), server_name, '127.0.0.1:14580')

        logger.debug('Sending heartbeat: {}'.format(heartbeat))

        with clients_lock:
            for client in clients:
                client.send_string_data(str(heartbeat + '\r\n'))

        yield from asyncio.sleep(20)


class OgnAprsServerClientProtocol(asyncio.Protocol):
    """
    APRS protocol implementation (server side).
    """

    def __init__(self, clients, clients_lock, data_hub, server_name, server_software):
        self._logger = logging.getLogger('OgnAprsServerClientProtocol.Server')
        self._logger.debug('Initializing')

        # store arguments in object variables
        self._clients = clients
        self._clients_lock = clients_lock
        self._data_hub = data_hub
        self._server_name = server_name
        self._server_software = server_software

        # initialize transport object
        self._transport = None

    def connection_made(self, transport):
        peername = transport.get_extra_info('peername')
        self._logger.info('New connection from {}'.format(peername))

        # keep transport object
        self._transport = transport

        # add this client to global client set
        with self._clients_lock:
            self._clients.add(self)

        # send initial message
        self.send_string_data('# {}\r\n'.format(self._server_software))

    def connection_lost(self, exc):
        self._logger.info('Connection closed to {}'.format(self._transport.get_extra_info('peername')))

        # remove this client from global client set
        with self._clients_lock:
            self._clients.remove(self)

    def data_received(self, data):
        data_string = data.decode().strip()

        self._logger.debug('Data received: {}'.format(data_string))

        # check for login request
        m = re.match(r"user (\w+) pass (\w+) vers (.+)", data_string)
        if m:
            user_name = m.group(1)
            password = m.group(2)

            # return authentication successful (credentials are not verified in current implementation)
            self.send_string_data('# logresp {} verified, server {}\r\n'.format(user_name, self._server_name))

            return

        # pre-process input
        data_string_lower = data_string.lower()

        # check for special commands
        if data_string_lower == 'exit':
            self._transport.close()

            return

        messages = data_string.splitlines()
        for message in messages:
            try:
                data_hub_item = DataHubItem('ogn', message)
                self._data_hub.put(data_hub_item)
            except:
                pass

    def send_string_data(self, data):
        self.send_data(str.encode(data))

    def send_data(self, data):
        self._transport.write(data)


class InputNetworkOgnServer(InputModule):
    """
    Input module that emulates an APRS server to which an Open Glider Network (OGN) decoder can connect. The OGN decoder
    is used to receive FLARM messages.
    """

    def __init__(self, data_hub):
        # call parent constructor
        super().__init__(data_hub=data_hub)

        # configure logging
        self._logger = logging.getLogger('InputNetworkOgnServer')
        self._logger.debug('Initializing')

        # initialize client set
        self.clients_lock = Lock()
        self.clients = set()

        # initialize object variables
        self._server_software = 'flightbox 1.0'
        self._server_name = 'FLIGHTBOX'

    def run(self):
        setproctitle.setproctitle("flightbox_input_network_ogn_server")

        self._logger.info('Running')

        # get asyncio loop
        loop = asyncio.get_event_loop()

        # create server coroutine
        ogn_aprs_server = loop.create_server(lambda: OgnAprsServerClientProtocol(clients=self.clients, clients_lock=self.clients_lock, data_hub=self._data_hub, server_name=self._server_name, server_software=self._server_software), host='', port=14580)

        # compile task list that will run in loop
        tasks = asyncio.gather(
            asyncio.async(ogn_aprs_heartbeat(loop=loop, clients=self.clients, clients_lock=self.clients_lock, server_name=self._server_name, server_software=self._server_software)),
            asyncio.async(ogn_aprs_server)
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
            ogn_aprs_server.close()
            loop.stop()

        # close data hub queue
        self._data_hub.close()

        self._logger.info('Terminating')
