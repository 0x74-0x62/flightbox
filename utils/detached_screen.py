#!/usr/bin/env python3

"""detached_screen.py: Derived screenutils.Screen class that starts screen sessions in detached mode right from the
beginning."""

from os import system
from screenutils import Screen

__author__ = "Thorsten Biermann"
__copyright__ = "Copyright 2015, Thorsten Biermann"
__email__ = "thorsten.biermann@gmail.com"


class DetachedScreen(Screen):
    def __init__(self, name, command, initialize=False):
        super().__init__(name, initialize=False)

        if initialize:
            self.initialize(command=command)

    def initialize(self, command):
        """initialize a screen, if does not exists yet"""
        if not self.exists:
            self._id=None
            system('screen -d -m -S ' + self.name + ' ' + command)
