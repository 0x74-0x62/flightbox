import logging
import setproctitle
from multiprocessing import Process, Queue

from data_hub.data_hub_item import DataHubItem

__author__ = "Thorsten Biermann"
__copyright__ = "Copyright 2015, Thorsten Biermann"
__email__ = "thorsten.biermann@gmail.com"


class DataHubWorker(Process):
    """
    The DataHubWorker is the central data handling entity that receives DataHubItems from input and transformation
    modules and forwards them as requested by output and transformation modules.
    """

    def __init__(self, data_hub):
        # call parent constructor
        super().__init__()

        # configure logging
        self._logger = logging.getLogger('DataHubWorker')
        self._logger.info('Initializing')

        # set data hub queue
        self._data_hub = data_hub

        # initialize output modules
        self._output_modules = []

    def run(self):
        setproctitle.setproctitle("flightbox_datahubworker")

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

                    # iterate over all known output modules
                    for output_module in self._output_modules:
                        # check if received data type is in output module's requested data types
                        if data_hub_item.get_content_type() in output_module['content_types'] \
                                or 'ANY' in output_module['content_types']:
                            self._logger.debug('Passing data to ' + str(output_module['output_module']))
                            # forward data via queue
                            output_module['queue'].put(data_hub_item)
                else:
                    self._logger.warning('Dropping data (wrong data type)')

            except(KeyboardInterrupt, SystemExit):
                break

        # close data hub queue
        self._data_hub.close()

        # terminate output modules and close queues
        for output_module in self._output_modules:
            # send poison pill to output module
            output_module['queue'].put(None)

            # close queue
            output_module['queue'].close()

        self._logger.info('Terminating')

    def add_output_module(self, output_module):
        # generate new queue for inter-process communication
        queue = Queue()

        # tell output module about queue
        output_module.set_data_input_queue(queue)

        # add module to internal list
        self._output_modules.append({'output_module': output_module, 'queue': queue, 'content_types': output_module.get_desired_content_types()})

        self._logger.debug('Output module added: ' + str(self._output_modules[-1]))
