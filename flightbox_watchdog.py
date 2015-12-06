#!/usr/bin/env python3

"""flightbox_watchdog.py: Description of what flightbox_watchdog.py does."""

import psutil
from screenutils import Screen
import time

__author__ = "Thorsten Biermann"
__copyright__ = "Copyright 2015, Thorsten Biermann"
__email__ = "thorsten.biermann@gmail.com"


# define flightbox processes that must be running
required_flightbox_processes = {}
required_flightbox_processes['flightbox'] = {'status': None}
required_flightbox_processes['flightbox_datahubworker'] = {'status': None}
required_flightbox_processes['flightbox_output_network_airconnect'] = {'status': None}
required_flightbox_processes['flightbox_transformation_sbs1ognnmea_flarm'] = {'status': None}
required_flightbox_processes['flightbox_input_network_sbs1'] = {'status': None}
required_flightbox_processes['flightbox_input_network_ogn_server'] = {'status': None}
required_flightbox_processes['flightbox_input_serial_gnss'] = {'status': None}

# define command for starting flightbox
flightbox_command = '/home/pi/opt/flightbox/flightbox.py'


def kill_all_flightbox_processes():
    for p in psutil.process_iter():
        if p.name().startswith('flightbox'):
            print("Killing process {}".format(p.name()))
            p.kill()


def start_flightbox():
    global flightbox_command

    print("Starting flightbox inside screen")
    s = Screen('flightbox', initialize=True)
    s.send_commands(flightbox_command)
    s.detach()


def restart_flightbox():
    kill_all_flightbox_processes()
    time.sleep(1.0)
    start_flightbox()


def check_flightbox_processes():
    global required_flightbox_processes

    for p in psutil.process_iter():
        if p.name() in required_flightbox_processes.keys():
            required_flightbox_processes[p.name()]['status'] = p.status()


# check if script is executed directly
if __name__ == "__main__":
    check_flightbox_processes()

    is_flightbox_restart_required = False

    for p in required_flightbox_processes.keys():
        if required_flightbox_processes[p]['status'] not in ['running', 'sleeping']:
            print("{} not running".format(p))
            is_flightbox_restart_required = True

    if is_flightbox_restart_required:
        restart_flightbox()
