""" Soar v0.11.0 ARCOS (Advanced Robot Control and Operations Software) Client

Classes and functions for communicating with an ARCOS server running on an Adept MobileRobot platform
(typically Pioneer 2 and 3).
"""
from threading import Thread, Lock, Event
from time import sleep

from serial import *
from serial.tools.list_ports import comports

from soar.errors import SoarError
from soar.client import printerr

# ARCOS Client command codes

SYNC0 = 0  # Synchronization packets, sent in sequence
SYNC1 = 1
SYNC2 = 2  # Robot specific information is sent back after SYNC2
PULSE = 0  # Reset server watchdog (typically sent every second so that the robot knows the client is alive_
OPEN = 1  # Start up ARCOS server
CLOSE = 2  # Close servers and client connection
POLLING = 3  # Change sonar polling sequence
ENABLE = 4  # if argument is 1, enables the motors, if 0, disables them
SETA = 5  # Set translation acceleration, if positive, or deceleration, if negative, in mm/sec^2
SETV = 6  # Set maximum translation velocity in mm/sec
SETO = 7  # Reset local position to 0,0,0 origin
MOVE = 8  # Translate forward (+) or backward (-) mm distance at SETV speed
ROTATE = 9  # Rotate counter- (+) or clockwise (-) degrees/sec at SETRV limited speed
SETRV = 10  # Sets maximum rotation velocity in degrees/sec
VEL = 11  # Translate at mm/sec forward (if positive) or backward (if negative), limited to velocity cap
HEAD = 12  # Turn at SETRV speed to absolute heading; +-degrees (+ is counterclockwise)
DHEAD = 13  # Turn at SETRV speed relative to current heading; (+) counter- or (-) clockwise degrees
SAY = 15  # Play up to 20 duration, tone sound pairs through User Control panel piezo speaker
JOYREQUEST = 17  # Request 1 or continuous stream (>1) or stop (0) joystick SIPS
CONFIG = 18  # Request a configuration SIP
ENCODER = 19  # Request one, a continuous stream (>1), or stop (0) encoder SIPS
RVEL = 21  # Rotate (degrees/sec) counterclockwise (positive) or clockwise (negative)
DCHEAD = 22  # Adjust heading relative to last setpoint; +- degrees (+ is counterclockwise)
SETRA = 23  # Change rotation (+) acceleration or (-) deceleration in degrees/sec^2
SONAR = 28  # 1=enable, 0=disable all the sonar; otherwise bits 1-3 specify an array from 1-4
STOP = 29  # Stops the robot without disabling the motors
DIGOUT = 30  # Set (1) or reset (0) User Output ports. Bits 8-15 is a byte mask that selects, if set the output ports
VEL2 = 32  # Set independent wheel velocities; bits 0-7 for right wheel, bits 8-15 for left wheel in 20mm/sec increments
IOREQUEST = 40  # Requires a single (1) or continuous stream (2), or stop (0) IO SIPS
SOUNDTOG = 92

command_types = {
    PULSE: None,
    OPEN: None,
    CLOSE: None,
    POLLING: str,
    ENABLE: int,
    SETA: int,
    SETV: int,
    SETO: int,
    MOVE: int,
    ROTATE: int,
    SETRV: int,
    VEL: int,
    HEAD: int,
    DHEAD: int,
    SAY: str,
    JOYREQUEST: int,
    CONFIG: None,
    ENCODER: int,
    RVEL: int,
    DCHEAD: int,
    SETRA: int,
    SONAR: int,
    STOP: None,
    DIGOUT: int,
    VEL2: int,
    IOREQUEST: int,
    SOUNDTOG: int,
}


class ARCOSError(SoarError):
    """ Umbrella class for ARCOS-related exceptions """


class Timeout(ARCOSError):
    """ Raised when no packet is read after a certain interval """


class InvalidPacket(ARCOSError):
    """ Raised when a packet's checksum is incorrect """


def packet_checksum(data):
    """ Calculates and returns the ARCOS packet checksum of a packet which does not have one

    Args:
        data (list): A list of data bytes

    Returns:
        int: The packet checksum
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


def decode_packet(packet):  # TODO: Make this cleaner
    """ Decodes a packet into a field-indexable dictionary

    Returns:
        dict: A dictionary with field names as keys and values as corresponding numbers. The 'TYPE' key holds a value of
        'STANDARD', 'CONFIG', or 'ENCODER', corresponding to the packet type

    Raises:
        InvalidPacket: If a packet's fields could not be decoded
    """

    def b_2_i(l, i):  # Takes a list and an index and returns the two bytes combined into an int
        return l[i] | (l[i+1] << 8)

    def str_from_i(l, i):  # Takes a list and an index and returns a null terminated string with index after the null terminator
        s = ''
        while l[i] != 0:
            s += chr(l[i])
            i += 1
        i += 1
        return s, i

    def unpack_byte_fields(data, packet, i, *fields):
        for field in fields:
            data.update({field: packet[i]})
            i += 1
        return i

    def unpack_int_fields(data, packet, i, *fields):
        for field in fields:
            data.update({field: b_2_i(packet, i)})
            i += 2
        return i

    def unpack_str_fields(data, packet, i, *fields):
        for field in fields:
            s, i = str_from_i(packet, i)
            data.update({field: s})
        return i

    try:
        data = {'TYPE': packet[3]}
        if data['TYPE'] in [0x32, 0x33]:  # Standard sip
            data['TYPE'] = 'STANDARD'
            unpack_int_fields(data, packet, 4, 'XPOS', 'YPOS', 'THPOS', 'L VEL', 'R VEL')
            data.update({'BATTERY': packet[14]})
            unpack_int_fields(data, packet, 15, 'STALL AND BUMPERS', 'CONTROL', 'FLAGS')
            data.update({'COMPASS': packet[21], 'SONAR_COUNT': packet[22]})
            sonars = {}
            i = 23
            for sonar in range(data['SONAR_COUNT']):
                number = packet[i]
                dist = b_2_i(packet, i + 1)
                sonars.update({number: dist})
                i += 3
            data.update({'SONARS': sonars})
        elif data['TYPE'] == 0x20:  # CONFIGpac
            data['TYPE'] = 'CONFIG'
            i = unpack_str_fields(data, packet, 4, 'ROBOT_TYPE', 'SUBTYPE', 'SERNUM')
            data.update({'4MOTS': packet[i]})
            i = unpack_int_fields(data, packet, i+1, 'ROTVELTOP', 'TRANSVELTOP', 'ROTACCTOP', 'TRANSACCTOP', 'PWMMAX')
            s, i = str_from_i(packet, i)
            data.update({'NAME': s})
            i = unpack_byte_fields(data, packet, i, 'SIPCycle', 'HOSTBAUD', 'AUXBAUD')
            i = unpack_int_fields(data, packet, i, 'GRIPPER', 'FRONT_SONAR')
            data.update({'REAR_SONAR': packet[i]})
            i += 1
            data.update({'LOWBATTERY': b_2_i(packet, i)})
        elif data['TYPE'] == 0x90:  # ENCODERpac
            data['TYPE'] = 'ENCODER'
            data.update({'L_ENCODER': (b_2_i(packet, 6) << 16) | b_2_i(packet, 4),
                         'R_ENCODER': (b_2_i(packet, 10) << 16) | b_2_i(packet, 8)})
        elif data['TYPE'] == 0xF0:  # IOpac
            data['TYPE'] = 'IO'
            i = unpack_byte_fields(data, packet, 4, 'N DIGIN', 'DIGIN', 'FRONTBUMPS', 'REARBUMPS', 'IRS', 'N_DIGOUT', 'DIGOUT', 'N_AN')
            analogs = []
            for analog in range(data['N_AN']):
                analogs.append(b_2_i(packet, i))
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
        allowed_timeouts (int): The number of timeouts to tolerate before the update coroutine closes the port

    Attributes:
        standard (dict): The last standard Server Information Packet (SIP) received. If no packet of this type has been
                         received, this will be None.
        config (dict): The last CONFIGpac SIP received. If no packet of this type has been received, this will be None.
        encoder (dict): The last ENCODERpac SIP received. If no packet of this type has been received, this will be None.
        standard_event (:class:`threading.Event`): Set whenever a standard SIP is received.
        config_event (:class:`threading.Event`): Set whenever a CONFIGpac SIP is received.
        encoder_event (:class:`threading.Event`): Set whenever an ENCODERpac SIP is received.
        io_event (:class:`threading.Event`): Set whenever an IOpac is received.
        io (dict): The last IOpac SIP received. If no packet of this type has been received, this will be None.
        sonars (list): A list of the latest Sonar array values, updated whenever a standard SIP is received.
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
        """
        packet = [0xfa, 0xfb, len(data) + 2] + list(data)  # 0xfa, 0xfb are the packet header
        checksum = packet_checksum(packet)  # Calculate the checksum and append it
        packet.extend([checksum >> 8, checksum & 0xff])  # Big-endian two byte integer
        with self.serial_lock:
            self.ser.write(bytearray(packet))

    def receive_packet(self):
        """ Read an entire ARCOS Packet from an open port, including header and checksum bytes.

        Returns:
            list: The entire packet as a list of bytes, including header and checksum bytes.

        Raises:
            Timeout: If at any point a timeout occurs and fewer bytes than expected are read.
            InvalidPacket: If the packet header, checksum, or packet length are invalid.
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
            code: The command code. Must be in :data:`soar.robot.arcos.command_types`
            data (optional): The associated command argument, assumed to be of the correct type
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
            
    def connect(self):
        """ Attempt to connect and sync with an ARCOS server over a serial port.

        Returns if successful.

        Raises:
            ARCOSError: If unable to connect to any available ports
        """
        ports = [port_info.device for port_info in comports()]  # Try every available port until we find a robot
        for port in ports:
            def connect_with_baud(baud):
                return Serial(port=port, baudrate=baud, timeout=self.timeout, writeTimeout=self.write_timeout)
            for baud in [115200, 57600, 38400, 19200, 9600]:  # Connect with the highest baudrate possible
                # Attempt to open the port
                try:
                    # Kill the microcontroller servers in case they are already running
                    self.ser = connect_with_baud(baud)
                    self.send_packet(CLOSE)
                    self.ser.close()

                    # Connect for real, and flush the input and output buffers
                    self.ser = connect_with_baud(baud)
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
        # If we have tried every available port without success, except out
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

    def sync(self, tries=6):
        """ Try to sync with an ARCOS server connected over an open serial port.

         Returns if successful.

        Args:
            tries (int, optional): The number of failures to tolerate before timing out.

        Raises:
            Timeout: If the number of tries is exhausted and syncing was not completed
        """
        for sync in [SYNC0, SYNC1, SYNC2]:
            echo = None
            while sync != echo:
                self.send_packet(sync)
                try:
                    received = self.receive_packet()
                except Timeout:
                    tries -= 1
                except InvalidPacket:  # Try flushing the input/output buffers
                    self.ser.reset_input_buffer()
                    self.ser.reset_output_buffer()
                    tries -= 1
                else:
                    echo = received[3]
                if tries < 0:
                    raise Timeout('An error occurred while syncing')
        return
            

    def pulse(self):
        """ Continually send the PULSE command so that the robot knows the client is alive """
        self.pulse_running = True
        while self.pulse_running:
            self.send_packet(PULSE)
            sleep(1.0)  # Default Watchdog interval is 2 seconds, so PULSE every second just to be safe

    def update(self):
        """ Continually receive and decode packets, storing them as attributes and triggering events """
        self.update_running = True
        timeouts = 0
        invalids = 0
        while self.update_running:
            try:
                received = self.receive_packet()
                decoded = decode_packet(received)
            except Timeout:  # Count timeouts and close the port if too many occur, killing this routine
                print('Timeout')
                timeouts += 1
                if timeouts > self.allowed_timeouts:
                    self.disconnect()
                    break
            except InvalidPacket:  # As per the Pioneer handbook, ignore invalid SIPs and move on
                print('Invalid')
                invalids += 1
                if invalids > 10:  # If many packets are invalid, try flushing the input buffer
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
        self.wait_for(self.standard_event, 5.0, 'Failed to receive SIPs from the robot')
        for i in range(5):  # Try multiple times to enable the sonars
            if self.standard['FLAGS'] & 0x2 != 0x2:
                self.send_command(SONAR, 1)
                sleep(1.0)
            else:
                break
        if self.standard['FLAGS'] & 0x2 != 0x2:
            raise ARCOSError('Unable to enable the robot sonars.')

    def wait_for(self, event, timeout=1.0, message=''):
        """ Waits for an event to occur, with an optional timeout.

        Args:
            event (Event): The event to wait for. Expected to be one of the attribute events of this class.
            timeout (float, optional): How long to wait for the event before timing out.
            message (str): The message to pass if a timeout occurs.

        Raises:
            Timeout: If the event has not occurred by the specified time.
        """
        event_occurred = event.wait(timeout)
        event.clear()
        if not event_occurred:
            raise Timeout(message)

