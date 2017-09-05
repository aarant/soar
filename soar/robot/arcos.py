# Soar (Snakes on a Robot): A Python robotics framework.
# Copyright (C) 2017 Andrew Antonitis. Licensed under the LGPLv3.
#
# soar/robot/arcos.py
""" ARCOS (Advanced Robot Control and Operations Software) Client.

Classes and functions for communicating with an ARCOS server running on an Adept MobileRobot platform
(typically Pioneer 2 and 3).
"""
from threading import Thread, Lock, Event
from time import sleep

from serial import Serial, SerialTimeoutException, SerialException
from serial.tools.list_ports import comports

from soar.errors import SoarError
from soar.client import printerr

__version__ = '1.0'

# ARCOS Client command codes

SYNC0 = 0  #: The initial synchronization packet.
SYNC1 = 1  #: The second synchronization packet.
SYNC2 = 2  # The final synchronization packet. Robot specific information is sent back after this packet.
PULSE = 0  #: Reset server watchdog (typically sent every second so that the robot knows the client is alive).
OPEN = 1  #: Start the ARCOS servers.
CLOSE = 2  #: Close servers and client connection. Also stops the robot.
POLLING = 3  #: Change sonar polling sequence. Argument is a string consisting of sonar numbers 1-32 (as single bytes).
ENABLE = 4  #: Enable the motors, if argument is 1, or disable them if it is 0.
SETA = 5  #: Set translation acceleration, if positive, or deceleration, if negative, in mm/sec^2.
SETV = 6  #: Set maximum translational velocity in mm/sec. Note that the robot is still limited by the hardware cap.
SETO = 7  #: Reset local odometry position to the origin `(0, 0, 0)`.
MOVE = 8  #: Translate forward (+) or backward (-) mm absolute distance at `SETV` speed.
ROTATE = 9  #: Rotate counter- (+) or clockwise (-) degrees/sec at `SETRV` limited speed.
SETRV = 10  #: Set maximum rotation velocity in degrees/sec. Note that the robot is still limited by the hardware cap.
VEL = 11  #: Translate at mm/sec forward (+) or backward (-), capped by `SETV`.
HEAD = 12  #: Turn at `SETRV` speed to absolute heading; +-degrees (+ is counterclockwise).
DHEAD = 13  #: Turn at `SETRV` speed relative to current heading; (+) counterclockwise or (-) clockwise degrees.
SAY = 15
""" Play up to 20 duration, tone sound pairs through User Control panel piezo speaker.
The argument is a string consisting of duration, tone pair bytes. Duration is in 20 millisecond increments.
A value of 0 means silence. The values 1-127 are the corresponding MIDI notes. The remaining values are frequencies
computed as `tone - 127*32` equivalent frequencies from 1-4096, in 32Hz increments.
"""
CONFIG = 18  #: Request a configuration SIP.
ENCODER = 19  #: Request a single (1), a continuous stream (>1), or stop (0) encoder SIPS.
RVEL = 21  #: Rotate (degrees/sec) counterclockwise (+) or clockwise (-). Limited by `SETRV`.
DCHEAD = 22  #: Adjust heading relative to last setpoint; +- degrees (+ is counterclockwise).
SETRA = 23  #: Change rotation (+) acceleration or (-) deceleration in degrees/sec^2
SONAR = 28  #: 1=enable, 0=disable all the sonar; otherwise bits 1-3 specify an array from 1-4 to enable/disable.
STOP = 29  #: Stop the robot without disabling the motors.
DIGOUT = 30  #: Set (1) or reset (0) User Output ports. Bits 8-15 is a byte mask that selects, if set the output ports
""" Set (1) or reset (0) user output ports. High bits 8-15 is a byte mask that selects the ports to change;
low bits 0-7 set (1) or reset (0) the selected port(s).
"""
VEL2 = 32  #: Set independent wheel velocities; bits 0-7 for right wheel, bits 8-15 for left in 20mm/sec increments.
ADSEL = 35  #: Select the A/D port number for reporting ANPORT value in standard SIP.
IOREQUEST = 40  #: Request a single (1), a continuous stream (>1), or stop (0) IO SIPS.
BUMPSTALL = 44  #: Stall robot if no (0), only front (1), only rear (2), or either (3) bumpers make contact.
SONARCYCLE = 48  #: Change the sonar cycle time, in milliseconds.
E_STOP = 55  #: Emergency stop. Overrides acceleration, so is very abrupt.
SOUNDTOG = 92  #: Mute (0) or enable (1) the user control piezo speaker.

command_types = {
    PULSE: None,
    OPEN: None,
    CLOSE: None,
    POLLING: str,
    ENABLE: int,
    SETA: int,
    SETV: int,
    SETO: None,
    MOVE: int,
    ROTATE: int,
    SETRV: int,
    VEL: int,
    HEAD: int,
    DHEAD: int,
    SAY: str,
    CONFIG: None,
    ENCODER: int,
    RVEL: int,
    DCHEAD: int,
    SETRA: int,
    SONAR: int,
    STOP: None,
    DIGOUT: int,
    VEL2: int,
    ADSEL: int,
    IOREQUEST: int,
    BUMPSTALL: int,
    SONARCYCLE: int,
    E_STOP: None,
    SOUNDTOG: int,
}
""" The argument type of every supported ARCOS command. """


class ARCOSError(SoarError):
    """ Umbrella class for ARCOS-related exceptions. """


class Timeout(ARCOSError):
    """ Raised when no packet is read after a certain interval. """


class InvalidPacket(ARCOSError):
    """ Raised when a packet's checksum is incorrect. """


def packet_checksum(data):
    """ Calculate and returns the ARCOS packet checksum of a packet which does not have one.

    Args:
        data (list): A list of data bytes.

    Returns:
        int: The packet checksum.
    """
    checksum = 0
    i = 3
    n = data[2]-2
    while n > 1:
        checksum += (data[i] << 8) | data[i+1]
        checksum &= 0xffff
        n -= 2
        i += 2
    if n > 0:
        checksum ^= data[i]
    return checksum


def __b_2_i(l, i):  # Takes a list and an index and returns the two bytes combined into an int
    return l[i] | (l[i + 1] << 8)


def __str_from_i(l, i):  # Takes a list and an index and returns a string and the index after the null terminator
    s = ''
    while l[i] != 0:
        s += chr(l[i])
        i += 1
    i += 1
    return s, i


def __unpack_byte_fields(data, packet, i, *fields):  # Unpack an arbitrary number of byte fields starting at index i
    for field in fields:
        data.update({field: packet[i]})
        i += 1
    return i


def __unpack_int_fields(data, packet, i, *fields):  # Unpack an arbitrary number of int fields starting at index i
    for field in fields:
        data.update({field: __b_2_i(packet, i)})
        i += 2
    return i


def __unpack_str_fields(data, packet, i, *fields):  # Unpack an arbitrary number of str fields starting at index i
    for field in fields:
        s, i = __str_from_i(packet, i)
        data.update({field: s})
    return i


def decode_packet(packet):
    """ Decode a SIP (Server Information Packet) into a field-indexable dictionary.

    Returns:
        dict: A dictionary with field names as keys and values as corresponding numbers. The `'TYPE'` key holds a value
        of `'STANDARD'`, `'CONFIG'`, `'ENCODER'`, or `'IO'`, corresponding to the packet type.

    Raises:
        `InvalidPacket`: If a packet's fields could not be decoded.
    """
    try:
        data = {'TYPE': packet[3], 'CHECKSUM': (packet[-1] & 0xff) | (packet[-2] << 8)}
        if data['TYPE'] in [0x32, 0x33]:  # Standard sip
            data['TYPE'] = 'STANDARD'
            __unpack_int_fields(data, packet, 4, 'XPOS', 'YPOS', 'THPOS', 'L VEL', 'R VEL')
            data['BATTERY'] = packet[14]
            __unpack_int_fields(data, packet, 15, 'STALL AND BUMPERS', 'CONTROL', 'FLAGS')
            data.update({'COMPASS': packet[21], 'SONAR_COUNT': packet[22]})
            sonars = {}
            i = 23
            for sonar in range(data['SONAR_COUNT']):
                number = packet[i]
                dist = __b_2_i(packet, i + 1)
                sonars.update({number: dist})
                i += 3
            data.update({'SONARS': sonars})
            i = __unpack_byte_fields(data, packet, i, 'GRIP_STATE', 'ANPORT', 'ANALOG', 'DIGIN', 'DIGOUT')
            data.update({'BATTERYX10': __b_2_i(packet, i)})
            i += 2
            data['CHARGE_STATE'] = packet[i]
            i += 1
            data['ROTVEL'] = __b_2_i(packet, i)
        elif data['TYPE'] == 0x20:  # CONFIGpac
            data['TYPE'] = 'CONFIG'
            i = __unpack_str_fields(data, packet, 4, 'ROBOT_TYPE', 'SUBTYPE', 'SERNUM')
            data.update({'4MOTS': packet[i]})
            i = __unpack_int_fields(data, packet, i+1, 'ROTVELTOP', 'TRANSVELTOP', 'ROTACCTOP', 'TRANSACCTOP', 'PWMMAX')
            s, i = __str_from_i(packet, i)
            data.update({'NAME': s})
            i = __unpack_byte_fields(data, packet, i, 'SIPCycle', 'HOSTBAUD', 'AUXBAUD')
            i = __unpack_int_fields(data, packet, i, 'GRIPPER', 'FRONT_SONAR')
            data.update({'REAR_SONAR': packet[i]})
            i = __unpack_int_fields(data, packet, i+1, 'LOWBATTERY', 'REVCOUNT', 'WATCHDOG')
            data.update({'P2MPACS': packet[i]})
            i = __unpack_int_fields(data, packet, i+1, 'STALLVAL', 'STALLCOUNT', 'JOYVEL', 'JORVEL', 'ROTVELMAX',
                                    'TRANSVELMAX')
        elif data['TYPE'] == 0x90:  # ENCODERpac
            data['TYPE'] = 'ENCODER'
            data.update({'L_ENCODER': (__b_2_i(packet, 6) << 16) | __b_2_i(packet, 4),
                         'R_ENCODER': (__b_2_i(packet, 10) << 16) | __b_2_i(packet, 8)})
        elif data['TYPE'] == 0xF0:  # IOpac
            data['TYPE'] = 'IO'
            i = __unpack_byte_fields(data, packet, 4, 'N DIGIN', 'DIGIN', 'FRONTBUMPS', 'REARBUMPS', 'IRS', 'N_DIGOUT',
                                     'DIGOUT', 'N_AN')
            analogs = []
            for analog in range(data['N_AN']):
                analogs.append(__b_2_i(packet, i))
                i += 2
            data.update({'ANALOGS': analogs})
    except IndexError:
        raise InvalidPacket('ARCOS SIP fields invalid')
    return data


class ARCOSClient:
    """ An ARCOS Client communicating over a serial port with an ARCOS server.

    Args:
        timeout (float): The time to wait while receiving data before a timeout occurs, in seconds.
        write_timeout (float): The time to wait while sending data before a timeout occurs, in seconds.
        allowed_timeouts (int): The number of timeouts to tolerate before the update coroutine closes the port.

    Attributes:
        standard (dict): The last standard Server Information Packet (SIP) received, or `None`, if one hasn't been
            received yet.
        config (dict): The last CONFIGpac SIP received, or `None`, if one hasn't been received yet.
        encoder (dict): The last ENCODERpac SIP received, or `None`, if one hasn't been received yet.
        io (dict): The last IOpac SIP received, or `None`, if one hasn't been received yet.
        standard_event (:class:`threading.Event`): Set whenever a standard SIP is received.
        config_event (:class:`threading.Event`): Set whenever a CONFIGpac SIP is received.
        encoder_event (:class:`threading.Event`): Set whenever an ENCODERpac SIP is received.
        io_event (:class:`threading.Event`): Set whenever an IOpac is received.
        sonars (list): A list of the latest sonar array values, updated whenever a standard SIP is received.
    """
    def __init__(self, timeout=1.0, write_timeout=1.0, allowed_timeouts=2):
        self.timeout = timeout  # Timeout values, in seconds
        self.write_timeout = write_timeout
        # If more than this number of consecutive timeouts occur, close the port, as it is unlikely it is still usable
        self.allowed_timeouts = allowed_timeouts
        self.ser = None  # The serial port, initially nonexistent
        self.serial_lock = Lock()  # A lock is needed so that packets sent by separate threads do not interfere
        self.pulse_running = False
        self.update_running = False
        # Store the last packets received of each type, and make them trigger events
        self.standard = None
        self.standard_event = Event()
        self.config = None
        self.config_event = Event()
        self.encoder = None
        self.encoder_event = Event()
        self.io = None
        self.io_event = Event()
        self.sonars = [5000]*32  # Initialize all possible sonars to 5000 mm

    def send_packet(self, *data):
        """ Send arbitrary data to the ARCOS server.

        Adds the packet header and checksum. Thread-safe.

        Args:
            *data: A tuple or iterable of bytes, whose values are assumed to be between 0 and 255, inclusive.

        Raises:
            `Timeout`: If the write timeout of the serial port was exceeded.
        """
        packet = [0xfa, 0xfb, len(data) + 2] + list(data)  # 0xfa, 0xfb are the packet header
        checksum = packet_checksum(packet)  # Calculate the checksum and append it
        packet.extend([checksum >> 8, checksum & 0xff])  # Big-endian two byte integer
        with self.serial_lock:
            try:
                self.ser.write(bytearray(packet))
            except SerialTimeoutException as e:  # Recast serial timeout as an ARCOS timeout
                raise Timeout(str(e)) from e

    def receive_packet(self):
        """ Read an entire ARCOS Packet from an open port, including header and checksum bytes.

        Returns:
            list: The entire packet as a list of bytes, including header and checksum bytes.

        Raises:
            `Timeout`: If at any point a timeout occurs and fewer bytes than expected are read.
            `InvalidPacket`: If the packet header, checksum, or packet length are invalid.
        """
        def read():
            try:
                b = ord(self.ser.read())
            except TypeError:  # A timeout has occurred, as 0 bytes were read
                raise Timeout
            else:
                return b
        with self.serial_lock:
            # Grab the packet header and ensure it is valid
            h1 = read()
            h2 = read()
            if h1 != 0xfa or h2 != 0xfb:
                raise InvalidPacket('ARCOS header invalid')
            data = [0xfa, 0xfb]
            length = read()
            if length > 249:
              raise InvalidPacket('Invalid packet length')
            data.append(length)
            for i in range(length):
                data.append(read())

        received_crc = (data[-1] & 0xFF) | (data[-2] << 8)
        crc = packet_checksum(data)
        if crc != received_crc:  # Checksum match failure
            raise InvalidPacket('Received checksum ' + str(received_crc) + ', expected checksum ' + str(crc))
        return data

    def send_command(self, code, data=None):
        """ Send a command and data to the ARCOS server.

        Args:
            code: The command code. Must be in :data:`soar.robot.arcos.command_types`.
            data (optional): The associated command argument, assumed to be of the correct type.

        Raises:
            `Timeout`: If the write timeout of the port was exceeded.
        """
        if command_types[code] is None:  # No argument
            self.send_packet(code)
        elif command_types[code] == int:
            if data >= 0:
                arg_type = 0x3b  # Positive integer
            else:
                arg_type = 0x1b  # Negative integer
            data = abs(data)
            b = [data & 0xff, (data >> 8) & 0xff]
            self.send_packet(code, arg_type, *b)
        else:  # command_types[code] == str
            b = [ord(c) for c in data]  # Convert the string to bytes and add a null terminator
            b.append(0)
            arg_type = 0x2b
            self.send_packet(code, arg_type, *b)
            
    def connect(self, forced_ports=None):
        """ Attempt to connect and sync with an ARCOS server over a serial port.

        Returns if successful.

        Args:
            forced_ports (list, optional): If provided, a list of serial ports to try connecting to. Otherwise, the
                client will try all available ports.

        Raises:
            `ARCOSError`: If unable to connect to any available ports.
        """
        if forced_ports is not None:
            ports = forced_ports
        else:
            ports = [port_info.device for port_info in comports()]  # Try every available port until we find a robot
        for port in ports:
            def connect_with_baudrate(baudrate):
                return Serial(port=port, baudrate=baudrate, timeout=self.timeout, writeTimeout=self.write_timeout)
            for baudrate in [115200, 57600, 38400, 19200, 9600]:  # Connect with the highest baudrate possible
                # Attempt to open the port
                try:
                    # Kill the microcontroller servers in case they are already running
                    self.ser = connect_with_baudrate(baudrate)
                    self.send_packet(CLOSE)
                    self.ser.close()

                    # Connect for real, and flush the input and output buffers
                    self.ser = connect_with_baudrate(baudrate)
                    self.ser.reset_input_buffer()
                    self.ser.reset_output_buffer()
                except SerialException as e:  # Any error opening the port (permissions, etc) will cause us to move on
                    printerr('SerialException:', str(e))
                    break
                # Try to sync; if there is a timeout, the port is probably not connected to a robot, so move on
                try:
                    self.sync()
                except Timeout:
                    continue
                else:
                    self.start()
                    return
        # If we have tried every available port without success, raise an exception
        raise ARCOSError('Unable to sync with an ARCOS server--is the robot connected and its port accessible?')

    def disconnect(self):
        """ Stop the ARCOS server and close the connection if running. """
        self.pulse_running = False  # Kill the pulse timer
        self.update_running = False
        if self.ser:  # Only attempt this if the serial port exists
            try:
                self.send_packet(STOP)  # Stop the robot
                self.send_packet(CLOSE)
                self.ser.close()
            except SerialException:  # Ignore errors that occur and assume the port is closed
                pass

    def sync(self, tries=4):
        """ Try to sync with an ARCOS server connected over an open serial port.

        Returns the raw robot identifying information packet sent after `SYNC2` if successful.

        Args:
            tries (int, optional): The number of failures to tolerate before timing out.

        Raises:
            `Timeout`: If the number of tries is exhausted and syncing was not completed.
        """
        for sync in [SYNC0, SYNC1, SYNC2]:
            while True:
                try:
                    self.send_packet(sync)
                    echo = self.receive_packet()
                except Timeout:  # Timeouts just decrement the tries count
                    tries -= 1
                except InvalidPacket:  # Try flushing the input/output buffers
                    self.ser.reset_input_buffer()
                    self.ser.reset_output_buffer()
                    tries -= 1
                else:
                    if sync == echo[3]:
                        break
                    else:
                        tries -= 1
                if tries < 0:
                    raise Timeout('An error occurred while syncing')
        return echo

    def pulse(self):
        """ Continually send the PULSE command so that the robot knows the client is alive. """
        self.pulse_running = True
        while self.pulse_running:
            try:
                self.send_packet(PULSE)
            except Timeout:  # Ignore pulse timeouts, the update coroutine will handle closing the port
                pass
            finally:
                sleep(1.0)  # Default Watchdog interval is 2 seconds, so PULSE every second just to be safe

    def update(self):
        """ Continually receive and decode packets, storing them as attributes and triggering events. """
        self.update_running = True
        timeouts = 0
        invalids = 0
        while self.update_running:
            try:
                received = self.receive_packet()
                decoded = decode_packet(received)
            except Timeout:  # Count timeouts and close the port if too many occur, killing this routine
                timeouts += 1
                if timeouts > self.allowed_timeouts:
                    self.disconnect()
                    break
            except InvalidPacket:  # As per the Pioneer handbook, ignore invalid SIPs and move on
                invalids += 1
                if invalids > 10:  # If many consecutive packets are invalid, try flushing the input buffer
                    self.ser.reset_input_buffer()
                continue
            else:
                invalids = 0
                if decoded['TYPE'] == 'STANDARD':  # Trigger the standard SIP event, and update the latest sonar reading
                    self.standard = decoded
                    for sonar, dist in self.standard['SONARS'].items():
                        self.sonars[sonar] = dist
                    self.standard_event.set()
                elif decoded['TYPE'] == 'CONFIG':
                    self.config = decoded
                    self.config_event.set()
                elif decoded['TYPE'] == 'ENCODER':
                    self.encoder = decoded
                    self.encoder_event.set()
                elif decoded['TYPE'] == 'IO':
                    self.io = decoded
                    self.io_event.set()

    def start(self):
        """ Open the ARCOS servers, enable the sonars, and start the pulse & update coroutines. """
        self.send_packet(OPEN)
        pulse = Thread(target=self.pulse, daemon=True)
        pulse.start()
        update = Thread(target=self.update, daemon=True)
        update.start()
        self.wait_or_timeout(self.standard_event, 5.0, 'Failed to receive SIPs from the robot')
        for i in range(5):  # Try multiple times to enable the sonars
            if self.standard['FLAGS'] & 0x2 != 0x2:
                self.send_command(SONAR, 1)
                sleep(1.0)
            else:
                return
        if self.standard['FLAGS'] & 0x2 != 0x2:  # If they still aren't enabled, raise an exception
            raise ARCOSError('Unable to enable the robot sonars.')

    @staticmethod
    def wait_or_timeout(event, timeout=1.0, timeout_msg=''):
        """ Wait for an event to occur, with an optional timeout and message.

        Args:
            event (Event): The event to wait for. Expected to be one of the attribute events of this class.
            timeout (float, optional): How long to wait for the event before timing out.
            timeout_msg (str): The message to pass if a timeout occurs.

        Raises:
            `Timeout`: If the event has not occurred by the specified time.
        """
        event_occurred = event.wait(timeout)
        event.clear()
        if not event_occurred:
            raise Timeout(timeout_msg)

