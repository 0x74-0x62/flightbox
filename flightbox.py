#!/usr/bin/env python

"""flightbox.py: Main FlightBox interface."""

__author__ = "Thorsten Biermann"
__copyright__ = "Copyright 2015, Thorsten Biermann"
__email__ = "thorsten.biermann@gmail.com"

import argparse
import daemon
import logging
import logging.config
import logging.handlers
from multiprocessing import Process, Queue
import os
import signal
import sys
import threading

arg_parser = argparse.ArgumentParser(description='FlightBox collects input from various devices, like GNSS, ADS-B, and combines them in one NMEA stream.')
arg_parser.add_argument('--daemon', dest='daemon', action='store_true', help='start in daemonized mode (background)')
arg_parser.set_defaults(daemon=False)
arg_parser.add_argument('--kill-daemon', dest='kill_daemon', action='store_true', help='kill running daemon')
arg_parser.set_defaults(kill_daemon=False)
arg_parser.add_argument('--pid-file', dest='pid_file', help='path to PID file')
arg_parser.set_defaults(pid_file='/tmp/flightbox.pid')
arg_parser.add_argument('--log-file', dest='log_file', help='path to log file')
arg_parser.set_defaults(log_file='/tmp/flightbox.log')
args = arg_parser.parse_args()


# watchdog initialization procedure
def flightbox_init():
    global args
    global logging_queue
    global logging_thread
    global flightbox_logger
    global logging_file_handles

    # instantiate logging queue (used for inter-process communication)
    logging_queue = Queue()

    # create configuration dict for logging
    logging_config = {
        'version': 1,
        'formatters': {
            'detailed': {
                'class': 'logging.Formatter',
                'format': '%(asctime)s %(processName)-15s %(name)-15s %(levelname)-8s %(message)s'
            }
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'level': 'DEBUG',
                'formatter': 'detailed',
            },
            'file': {
                'class': 'logging.FileHandler',
                'filename': args.log_file,
                'mode': 'w',
                'level': 'DEBUG',
                'formatter': 'detailed',
            },
        },
        'root': {
            'level': 'DEBUG',
            'handlers': ['console', 'file']
        },
    }

    # apply logging configuration
    logging.config.dictConfig(logging_config)

    logging_thread = threading.Thread(target=flightbox_logging_thread, args=(logging_queue,))
    logging_thread.start()

    # set up main flightbox logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    flightbox_logger = logging.getLogger('FlightBox')

    # store logging streams (required for later protection when going into daemon mode)
    logging_file_handles = []
    for handler in root_logger.handlers:
        if type(handler) is logging.StreamHandler or type(handler) is logging.FileHandler:
            logging_file_handles.append(handler.stream.fileno())


# main function
def flightbox_main():
    global args
    global flightbox_logger

    flightbox_logger.info('Entering main procedure')

    try:
        # TODO add main processing
        pass

    except(KeyboardInterrupt, SystemExit):
        pass

    flightbox_cleanup()


# flightbox cleanup procedure
def flightbox_cleanup():
    global logging_queue
    global logging_thread
    global flightbox_logger

    flightbox_logger.info('Stopping logging thread')

    # hand over poison pill to logging thread
    logging_queue.put(None)
    # wait for logging thread to terminate
    logging_thread.join()


# thread function that handles log messages from all processes
def flightbox_logging_thread(logging_queue):
    while True:
        # get log record from queue
        logging_record = logging_queue.get()

        print('Processing queue record')

        # terminate when poison pill None is found in queue
        if logging_record is None:
            break

        # handle log record
        logger = logging.getLogger(logging_record.name)
        logger.handle(logging_record)


# call main flightbox function in case script is executed directly
if __name__ == "__main__":
    flightbox_init()

    if args.kill_daemon:
        flightbox_logger.info('Trying to terminate existing daemon process')
        try:
            # get PID
            with open(args.pid_file, "r") as pid_file:
                pid = int(pid_file.read().replace('\n', ''))

                flightbox_logger.info('Sending SIGTERM to PID ' + str(pid))
                os.kill(pid, signal.SIGTERM)
        except IOError as e:
            flightbox_logger.error('Unable to read PID from ' + args.pid_file)
            flightbox_logger.exception(sys.exc_info()[0])

        sys.exit(0)

    if args.daemon:
        flightbox_logger.info('Starting in daemon mode')

        context = daemon.DaemonContext(
            working_directory='/tmp',
            umask=0o022,
            pidfile=daemon.pidfile.PIDLockFile(args.pid_file),
            )

        # keep log file open during daemon start
        context.files_preserve = logging_file_handles

        context.signal_map = {
            signal.SIGTERM: flightbox_cleanup,
            signal.SIGHUP: flightbox_cleanup,
            }

        # start daemonized in background
        with context:
            flightbox_main()

    else:
        # start normally in foreground
        flightbox_main()
