from input.input_module import InputModule
from output.output_module import OutputModule

__author__ = "Thorsten Biermann"
__copyright__ = "Copyright 2015, Thorsten Biermann"
__email__ = "thorsten.biermann@gmail.com"


class TransformationModule(InputModule, OutputModule):
    """
    Generic transformation module class.
    """

    def __init__(self, data_hub):
        InputModule.__init__(self, data_hub=data_hub)
        OutputModule.__init__(self)
