__author__ = "Thorsten Biermann"
__copyright__ = "Copyright 2015, Thorsten Biermann"
__email__ = "thorsten.biermann@gmail.com"


class DataHubItem(object):
    """
    This class is the main data container for exchanging information between different modules.
    """

    def __init__(self, content_type, content_data):
        self.__content_type = content_type
        self.__content_data = content_data

    def __str__(self):
        return '(' + self.__content_type + ') "' + self.__content_data + '"'

    def get_content_type(self):
        return self.__content_type

    def get_content_data(self):
        return self.__content_data
