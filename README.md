# FlightBox

FlightBox is a modular, event-based processing framework for aviation-related data. It can be used, e.g., to receive GNSS/GPS, ADS-B and FLARM signals, process them, and provide a data stream to navigation systems, like SkyDemon.  These systems then can show surrounding aircraft positions in their moving map displays.

For receiving ADS-B and FLARM signals, two DVB-T USB dongles with a certain chip set, which are compatible to the rtl-sdr tools (<http://sdr.osmocom.org/trac/wiki/rtl-sdr>), can be used.

## Modules

FlightBox is implemented in a modular way to allow adding additional data sources (input modules), data processing steps (transformation modules), and output interfaces (output modules) in a simply way.  The following modules are currently implemented.

TODO: Data hub

### Input

#### GNSS (GPS) receiver

The system needs to know the current position to provide it to a connected navigation system and to calculate collision avoidance information.  To determine the current position, the `input_serial_gnss` module connects to a serial GNSS (GPS) receiver that is, e.g., connected via USB.  Each message received from the NMEA data stream is inserted into the data hub (type `nmea`).

#### Open Glider Network (OGN) FLARM receiver

To receive FLARM signals from other aircraft, the `input_setwork_ogn_server` module implements a very simple APRS-IS (<http://www.aprs-is.net>) server to which the receiver software of the Open Glider Network (OGN) Project (<http://wiki.glidernet.org/>) can connect.  For this, both `ogn_rf` and `ogn_decode` (available at <http://wiki.glidernet.org/wiki:manual-installation-guide>) need to be started after the FlightBox processes are running.  Every OGN/APRS message is inserted into the data hub (type `ogn`).

The OGN tools need a configuration file.  Below is an example configuration file that uses the second rtl-sdr device:

    RF:
    {
      Device   =   1;                          # [index]    0 = 1st USB stick, 1 = 2nd USB stick, etc.
      FreqCorr =  +0;                          # [ppm]      correction factors, measure it with gsm_scan or kalibrate
      PipeName = "opt/rtlsdr-ogn/ogn-rf.fifo"; # path to pipe that is used to exchange data between ogn_rf and ogn_decode
                                               # path is relative to location from which ogn_rf and ogn_decode are started
    } ;
    
    Position:
    { Latitude   =    +0.0000; # [deg] Antenna coordinates
      Longitude  =    +0.0000; # [deg]
      Altitude   =          0; # [m]   Altitude above sea leavel
      GeoidSepar =         48; # [m]   Geoid separation: FLARM transmits GPS altitude, APRS uses means Sea level altitude
    } ;
    
    APRS:
    { Call      = "FlightBox";          # APRS callsign (max. 9 characters)
                                        # Please refer to http://wiki.glidernet.org/receiver-naming-convention
      Server    = "localhost:14580";    # IP address and port at which an APRS-IS server is listening
    } ;

#### SBS1 (ADS-B) receiver

To receive ADS-B transponder signals from other aircraft, the `input_network_sbs1` module implements a client that connects to a server that delivers ADS-B data via the SBS1 protocol.  There are many implementations for decoding ADS-B data, like `dump1090`.  A popular fork of `dump1090` is available at <https://github.com/mutability/dump1090>, which provides everything to run the tool as a daemon.  After starting the daemon, the `input_network_sbs1` module can connect to dump1090's SBS1 server interface.  Every SBS1 message is inserted into the data hub (type `sbs1`).

### Output

#### AIR Connect server

AIR Connect (<http://www.air-avionics.com/air/index.php/en/products/apps-and-interface-systems/air-connect-interface-for-apps>) is a popular interface for providing serial data, like FLARM NMEA messages, via a network connection to a variety of navigation systems and apps.  The `output_network_airconnect` module implements a server that allows apps to connect and receive position and traffic information from the FlightBox system.  The module consumes NMEA and FLARM messages (types `nmea`and `flarm`) from the data hub and forwards them to the connected clients.

### Transformation

#### SBS1/OGN/NMEA to FLARM NMEA converter

To process all GNSS, OGN, and SBS1 data and generate a FLARM data stream (containing position and traffic information), the module `transformation_sbs1ognnmea` implements all required processing steps.  Therefore, the module consumes NMEA, OGN, and SBS1 messages (types `nmea`, `ogn`, `sbs1`) from the data hub and inserts FLARM messages (type `flarm`) back to the data hub after processing.

## Requirements

### Hardware

### Software

* dump1019

## Installation
