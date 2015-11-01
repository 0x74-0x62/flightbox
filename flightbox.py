#!/usr/bin/env python

"""flightbox.py: Main FlightBox interface."""

__author__ = "Thorsten Biermann"
__copyright__ = "Copyright 2015, Thorsten Biermann"
__email__ = "thorsten.biermann@gmail.com"

import argparse
import daemon
import daemon.pidfile
import logging
import logging.handlers
from multiprocessing import Process, Queue
import os
import signal
import sys

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

    """ set up receiving side of logging framework """

    # create formatter
    logging_formatter = logging.Formatter(
        '%(asctime)s %(processName)-15s %(threadName)-15s %(name)-15s %(levelname)-8s %(message)s')

    # create file handler
    logging_file_handler = logging.FileHandler(args.log_file)
    logging_file_handler.setLevel(logging.DEBUG)
    logging_file_handler.setFormatter(logging_formatter)

    # create console handler
    logging_stream_handler = logging.StreamHandler()
    logging_stream_handler.setLevel(logging.DEBUG)
    logging_stream_handler.setFormatter(logging_formatter)

    # store logging streams (required for later protection when going into daemon mode)
    logging_file_handles = [logging_file_handler.stream.fileno(), logging_stream_handler.stream.fileno()]

    # start logging thread
    logging_thread = logging.handlers.QueueListener(logging_queue, logging_file_handler, logging_stream_handler)
    logging_thread.start()

    """ set up sending side of logging framework """

    # create queue handler
    logging_queue_handler = logging.handlers.QueueHandler(logging_queue)

    # configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(logging_queue_handler)

    """ set up logger for main FlightBox logging """

    # create flightbox logger
    flightbox_logger = logging.getLogger('FlightBox')

    flightbox_logger.info('Started logging framework')


# main function
def flightbox_main():
    global args
    global flightbox_logger
    global logging_queue

    flightbox_logger.info('Entering main procedure')

    try:
        # TODO add main processing
        pass

    except(KeyboardInterrupt, SystemExit):
        pass


# flightbox cleanup procedure
def flightbox_cleanup():
    global logging_queue
    global logging_thread
    global flightbox_logger

    flightbox_logger.info('Terminating logging thread')

    # terminate logging thread
    logging_thread.stop()


# call main flightbox function in case script is executed directly
if __name__ == "__main__":
    # initialize global variables
    logging_queue = None
    logging_thread = None
    flightbox_logger = None
    logging_file_handles = None

    # initialize framework
    flightbox_init()

    # check if daemon shall be terminated
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

    else:
        # check if background start is requested
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

    # clean up framework
    flightbox_cleanup()
