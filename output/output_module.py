from multiprocessing import Process

__author__ = "Thorsten Biermann"
__copyright__ = "Copyright 2015, Thorsten Biermann"
__email__ = "thorsten.biermann@gmail.com"


class OutputModule(Process):
    """
    Generic output module class.
    """

    def __init__(self):
        # call parent constructor
        super().__init__()

        # initialize data input queue
        self._data_input_queue = None

    def set_data_input_queue(self, data_input_queue):
        self._data_input_queue = data_input_queue

        self._logger.debug('Received data input queue')

    def get_desired_content_types(self):
        return(['ANY'])
