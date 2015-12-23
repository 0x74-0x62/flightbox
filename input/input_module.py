from multiprocessing import Process

__author__ = "Thorsten Biermann"
__copyright__ = "Copyright 2015, Thorsten Biermann"
__email__ = "thorsten.biermann@gmail.com"


class InputModule(Process):
    """
    Generic input module class.
    """

    def __init__(self, data_hub):
        # call parent constructor
        super().__init__()

        # set data hub queue
        self._data_hub = data_hub
