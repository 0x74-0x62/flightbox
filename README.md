# FlightBox

FlightBox is a modular, event-based processing framework for aviation-related data, writen in Python. It can be used, e.g., to receive GNSS/GPS, ADS-B and FLARM signals, process them, and provide a data stream to navigation systems, like SkyDemon.  These systems then can show surrounding aircraft positions in their moving map displays.

For receiving ADS-B and FLARM signals, two DVB-T USB dongles with a certain chip set, which are compatible to the rtl-sdr tools (<http://sdr.osmocom.org/trac/wiki/rtl-sdr>), are required.

Currently, the default configuration assumes that the FlightBox files are located at `/home/pi/opt/flightbox`, and OGN receiver tools in `/home/pi/opt/rtlsdr-ogn`.  There is a watchdog script called `flightbox_watchdog.py`, which starts and monitors all required processes except the `dump1090` daemon (required for receiving ADS-B data).  This watchdog can, e.g., be executed by a cronjob to automatically start the framework after boot and make sure it keeps running.

## Requirements

Below are requirements from the hardware and software perspective.  Note that a system with reduced features, like only receiving ADS-B, works, too.

### Hardware

* Computing device, like Raspberry Pi 1 or 2
* Wifi USB dongle that supports AP mode (for providing Wifi access point), like those with RT5370 chipset
* DVB-T USB dongle that is supported by rtl-sdr (one required for ADS-B reception and another one for receiving FLARM)
* GNSS (GPS/GLONASS) USB dongle
  * E.g., with u-blox 7 chipset
* Powered USB hub (to sufficiently power all USB devices)
  * Wifi, GNSS, and one DVB-T dongle probably works without an additional hub

### Software

* ADS-B decoder that provides SBS1 data stream, like dump1090
* OGN FLARM decoder
* Everything required to set up a Wifi access point, like DHCP daemon, HostAP daemon
  * See <http://elinux.org/RPI-Wireless-Hotspot> for instructions (NAT is not required)
  * The network should be configured to such that the access point has the address 192.168.1.1
* Screen (in case the watchdog script is used)
* Python 3
* Python packages (can be installed, e.g., via `sudo pip3 install <PACKAGENAME>`)
  * pyserial
  * pynmea2
  * geopy
  * setproctitle
  * psutil
  * screenutils

## Modules

FlightBox is implemented in a modular way to allow adding additional data sources (input modules), data processing steps (transformation modules), and output interfaces (output modules) in a simply way.  The modules that are currently implemented are described in the following subsections.

The data flows through a central data structure called `data_hub`.  Input and transformation modules can inject data into the system by creating a `data_hub_item` and handing it over to the data hub.  Output and transformation modules can subscribe to certain `data_hub_item` types, like `nmea` or `sbs1`.  A `data_hub_worker` processes all incoming data hub items and forwards them to the registered output and transformation modules as desired.

### Input

#### GNSS (GPS) receiver

The system needs to know the current position to provide it to a connected navigation system and to calculate collision avoidance information.  To determine the current position, the `input_serial_gnss` module connects to a serial GNSS (GPS) receiver that is, e.g., connected via USB.  Each message received from the NMEA data stream is inserted into the data hub (type `nmea`).

#### Open Glider Network (OGN) FLARM receiver

To receive FLARM signals from other aircraft, the `input_setwork_ogn_server` module implements a very simple APRS-IS (<http://www.aprs-is.net>) server to which the receiver software of the Open Glider Network (OGN) Project (<http://wiki.glidernet.org/>) can connect.  For this, both `ogn_rf` and `ogn_decode` (available at <http://wiki.glidernet.org/wiki:manual-installation-guide>) need to be started after the FlightBox processes are running.  Every OGN/APRS message is inserted into the data hub (type `ogn`).

The OGN tools need a configuration file.  Please note that in this configuration file the own position, which is needed to calculate the absolute positions of FLARM targets, has to be set to 0.  The current location from the GNSS input module will be used by FlightBox for calculation.  Below is an example configuration file that uses the second rtl-sdr device:

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

To receive ADS-B transponder signals from other aircraft, the `input_network_sbs1` module implements a client that connects to a server that delivers ADS-B data via the SBS1 protocol (usually available on port 30003).  There are many implementations for decoding ADS-B data, like `dump1090`.  A popular fork of `dump1090` is available at <https://github.com/mutability/dump1090>, which provides everything to run the tool as a daemon.  After starting the daemon, the `input_network_sbs1` module can connect to dump1090's SBS1 server interface.  Every SBS1 message is inserted into the data hub (type `sbs1`).

### Output

#### AIR Connect server

AIR Connect (<http://www.air-avionics.com/air/index.php/en/products/apps-and-interface-systems/air-connect-interface-for-apps>) is a popular interface for providing serial data, like FLARM NMEA messages, via a network connection to a variety of navigation systems and apps.  The `output_network_airconnect` module implements a server that allows apps to connect and receive position and traffic information from the FlightBox system.  The module consumes NMEA and FLARM messages (types `nmea` and `flarm`) from the data hub and forwards them to the connected clients.

### Transformation

#### SBS1/OGN/NMEA to FLARM NMEA converter

To process all GNSS, OGN, and SBS1 data and generate a FLARM data stream (containing position and traffic information), the module `transformation_sbs1ognnmea` implements all required processing steps.  Therefore, the module consumes NMEA, OGN, and SBS1 messages (types `nmea`, `ogn`, `sbs1`) from the data hub and inserts FLARM messages (type `flarm`) back to the data hub after processing.

## Installation procedure

TODO

## Contact

In case you have any problems, questions, ideas for improvement, would like to contribute to this project, or just find this piece of software useful, please do not hesitate to get in touch with the author. :-)
