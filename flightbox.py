#!/usr/bin/env python

"""flightbox.py: Main FlightBox interface."""

import argparse
import logging
import logging.handlers
from multiprocessing import Queue
import multiprocessing.util
import time

from data_hub.data_hub_worker import DataHubWorker
from input.test_data_generator import TestDataGenerator
from output.air_connect_output import AirConnectOutput

__author__ = "Thorsten Biermann"
__copyright__ = "Copyright 2015, Thorsten Biermann"
__email__ = "thorsten.biermann@gmail.com"

arg_parser = argparse.ArgumentParser(description='FlightBox collects input from various devices, like GNSS, ADS-B, and combines them in one NMEA stream.')
arg_parser.add_argument('--log-file', dest='log_file', help='path to log file')
arg_parser.set_defaults(log_file='/tmp/flightbox.log')
args = arg_parser.parse_args()


# watchdog initialization procedure
def flightbox_init():
    global args
    global logging_queue
    global logging_thread
    global flightbox_logger

    # enable debug logging for multiprocessing
    # multiprocessing.util.log_to_stderr(level=logging.DEBUG)

    # instantiate logging queue (used for inter-process communication)
    logging_queue = Queue()

    """ set up receiving side of logging framework """

    # create formatter
    logging_formatter = logging.Formatter(
        '%(asctime)s %(processName)-25s %(threadName)-10s %(name)-35s %(levelname)-8s %(message)s')

    # create file handler
    logging_file_handler = logging.FileHandler(args.log_file)
    logging_file_handler.setLevel(logging.DEBUG)
    logging_file_handler.setFormatter(logging_formatter)

    # create console handler
    logging_stream_handler = logging.StreamHandler()
    logging_stream_handler.setLevel(logging.DEBUG)
    logging_stream_handler.setFormatter(logging_formatter)

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
    global data_hub
    global data_hub_worker

    flightbox_logger.info('Entering main procedure')

    try:
        # TODO add main processing
        data_hub = Queue()

        processes = []

        data_hub_worker = DataHubWorker(data_hub)
        processes.append(data_hub_worker)

        test_data_generator = TestDataGenerator(data_hub)
        processes.append(test_data_generator)

        air_connect_output = AirConnectOutput()
        data_hub_worker.add_output_module(air_connect_output)
        processes.append(air_connect_output)

        # processes need to be started after configuration, as they are executed in separate processes
        data_hub_worker.start()
        time.sleep(1)
        test_data_generator.start()
        time.sleep(1)
        air_connect_output.start()
        time.sleep(1)

        # wait for data_hub_worker to finish
        data_hub_worker.join()

    except(KeyboardInterrupt, SystemExit):
        # wait for all processes to finish
        for process in processes:
            flightbox_logger.debug('Waiting for process ' + process.name + ' to terminate')
            process.join()


# flightbox cleanup procedure
def flightbox_cleanup():
    global logging_queue
    global logging_thread
    global flightbox_logger
    global data_hub
    global data_hub_worker

    # terminate logging thread
    flightbox_logger.info('Terminating logging thread')
    logging_thread.stop()

    # close all queues
    data_hub.close()
    logging_queue.close()


# call main flightbox function in case script is executed directly
if __name__ == "__main__":
    # initialize global variables
    logging_queue = None
    logging_thread = None
    flightbox_logger = None
    data_hub = None
    data_hub_worker = None

    # initialize framework
    flightbox_init()

    # start normally in foreground
    flightbox_main()

    # clean up framework
    flightbox_cleanup()
