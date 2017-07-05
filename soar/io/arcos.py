""" ARCOS (Advanced Robot Control and Operations Software) Client

Classes and functions for communicating with an ARCOS server running on an Adept MobileRobot platform
(typically Pioneer 2 and 3)
"""


from threading import Thread, Lock, Event
from time import sleep
from serial import *
from serial.tools.list_ports import comports

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
DIGOUT = 30
VEL2 = 32  # Set independent wheel velocities; bits 0-7 for right wheel, bits 8-15 for left wheel in 20mm/sec increments
GRIPPER = 33
ADSEL = 35
GRIPPERVAL = 36
GRIPREQUEST = 37

SOUNDTOG = 92
# TODO

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
    SOUNDTOG: int,
    }


class ARCOSError(Exception):
    """ Umbrella class for ARCOS-related exceptions """


class Timeout(ARCOSError):
    """ Raised when no packet is read after a certain interval """


class InvalidPacket(ARCOSError):
    """ Raised when a packet's checksum is incorrect """


def packet_checksum(data):
    """ Calculates and returns the ARCOS packet checksum of a packet which does not yet have one

    Args:
        data (list): A list of data bytes

    Returns: # TODO
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


def decode_packet(packet):
    """ Decodes a packet into a field-indexable dictionary

    Returns:
        dict: A dictionary with field names as keys and values as corresponding numbers. The 'TYPE' key holds a value of
        'STANDARD', 'CONFIG', or 'ENCODER'
    """

    def b_2_i(l, i):  # Takes a list and an index and returns the two bytes combined into an int
        return l[i] | (l[i+1] << 8)

    def str_from_i(l, i):  # Takes a list and an index and returns the null terminated string with index after the null terminator
        s = ''
        while l[i] != 0:
            s += chr(l[i])
            i += 1
        i += 1
        return s, i

    data = {'TYPE': packet[3]}
    if data['TYPE'] in [0x32, 0x33]:  # Standard sip
        data['TYPE'] = 'STANDARD'
        i = 4
        for field in ['XPOS', 'YPOS', 'THPOS', 'L VEL', 'R VEL']:
            num = b_2_i(packet, i)
            data.update({field: num})
            i += 2
        data.update({'BATTERY': packet[14]})
        i = 15
        for field in ['STALL AND BUMPERS', 'CONTROL', 'FLAGS']:
            num = b_2_i(packet, i)
            data.update({field: num})
            i += 2
        data.update({'COMPASS': packet[21], 'SONAR_COUNT': packet[22]})
        sonars = {}
        i = 23
        for sonar in range(data['SONAR_COUNT']):
            number = packet[i]
            dist = b_2_i(packet, i + 1)
            sonars.update({number: dist})
            i += 3
        data.update({'SONARS': sonars})
    elif data['TYPE'] == 0x20:
        data['TYPE'] = 'CONFIG'
        i = 4
        for field in ['ROBOT_TYPE', 'SUBTYPE', 'SERNUM']:
            s, i = str_from_i(packet, i)
            data.update({field: s})
        data.update({'4MOTS': packet[i]})
        i += 1
        for field in ['ROTVELTOP', 'TRANSVELTOP', 'ROTACCTOP', 'TRANSACCTOP', 'PWMMAX']:
            data.update({field: b_2_i(packet, i)})
            i += 2
        s, i = str_from_i(packet, i)
        data.update({'NAME': s})
    elif data['TYPE'] == 0x90:  # ENCODERpac
        data['TYPE'] = 'ENCODER'
        data.update({'L_ENCODER': (b_2_i(packet, 6) << 16) | b_2_i(packet, 4),
                     'R_ENCODER': (b_2_i(packet, 10) << 16) | b_2_i(packet, 8)})
    return data


class ARCOSClient:
    def __init__(self, timeout=1.0, write_timeout=1.0, allowed_timeouts=2):
        self.timeout = timeout  # Timeout values, in seconds
        self.write_timeout = write_timeout
        # If more than this number of consecutive timeouts occur, close the port, as it is unlikely it is still usable
        self.allowed_timeouts = allowed_timeouts
        self.timeouts = 0
        self.ser = None  # The serial port, initially nonexistent
        self.serial_lock = Lock()  # A lock is needed so that packets sent by separate threads do not interfere
        self.pulse_running = False
        self.update_running = False
        self.standard = None  # Store the last packets received of each type, and make them trigger events
        self.standard_event = Event()
        self.config_pac = None
        self.config_event = Event()
        self.encoder_pac = None
        self.encoder_event = Event()
        self.sonars = [5000]*32  # Initialize all possible sonars to 5000 mm

    def send_packet(self, *data):
        """ Sends arbitrary data (in the form of a tuple of bytes) to the ARCOS server

            Thread-safe, by means of a serial lock
        """
        packet = [0xfa, 0xfb, len(data) + 2] + list(data)  # 0xfa, 0xfb are the packet header
        checksum = packet_checksum(packet)  # Calculate the checksum and append it
        packet.extend([checksum >> 8, checksum & 0xff])  # Big-endian two byte integer
        with self.serial_lock:
            self.ser.write(bytearray(packet))

    def receive_packet(self):
        """ Reads an entire ARCOS Packet from the open port, including header and checksum bytes

        If the header or checksum are invalid, a timeout occurs, fail silently and return None
        """
        def read():
                try:
                    b = ord(self.ser.read())
                except TypeError:  # A timeout has occurred, as 0 bytes were read
                    self.timeouts += 1
                    return None
                else:
                    return b
        with self.serial_lock:
            # Grab the packet header and ensure it is valid
            h1 = read()
            h2 = read()
            if h1 != 0xfa or h2 != 0xfb:
                return None
            data = [0xfa, 0xfb]
            l = read()
            data.append(l)
            for i in range(l):
                data.append(read())

        received_crc = (data[-1] & 0xFF) | (data[-2] << 8)
        crc = packet_checksum(data)
        if crc != received_crc:  # Checksum match failure
            return None
        return data

    def send_command(self, code, data=None):  # TODO
        """ Sends a command, assuming that its argument type is specified in command_types """
        if command_types[code] == None:
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
            b = [ord(c) for c in data].append(0)  # Convert the string to bytes and add a null terminator
            arg_type = 0x2b
            self.send_packet(code, arg_type, *b)
            
    def connect(self):
        """ Attempts to connect and sync with an ARCOS server over a serial port

            If successful, simply returns. Otherwise, raises an ARCOSError exception
        """
        ports = [port_info.device for port_info in comports()]  # Try every available port until we find a robot
        for port in ports:
            def connect_with_baud(baud):
                return Serial(port=port, baudrate=baud, timeout=self.timeout, writeTimeout=self.write_timeout)
            for baud in [115200, 57600, 38400, 19200, 9600]:  # Connect with the highest baudrate possible
                # Kill the microcontroller servers in case they are already running
                try:
                    self.ser = connect_with_baud(baud)
                    self.send_packet(CLOSE)
                    self.ser.close()

                    # Connect for real, and flush the input and output buffers
                    self.ser = connect_with_baud(baud)
                    self.ser.reset_input_buffer()
                    self.ser.reset_output_buffer()
                except SerialException as e:  # Any error opening the port (permissions, etc) will cause us to move on
                    break
                # Try to sync; if there is a timeout, the port is probably not connected to a robot, so move on
                try:
                    self.sync()
                    self.start()
                except Timeout:
                    continue
                else:
                    return
        raise ARCOSError('Unable to sync with any ARCOS servers--is the robot connected and the port accessible?')

    def disconnect(self):
        """ Stops the connected ARCOS server and closes the serial port """
        self.pulse_running = False  # Kill the pulse timer
        self.update_running = False
        if self.ser:  # Only attempt this if the serial port exists
            self.send_packet(STOP)  # Stop the robot
            self.send_packet(CLOSE)
            self.ser.close()

    def sync(self):
        """ Syncs with and initializes an ARCOS server connected over an open serial port """
        for sync in [SYNC0, SYNC1, SYNC2]:
            echo = None
            while sync != echo:  # TODO: Is it possible for this to hang?
                self.send_packet(sync)
                received = self.receive_packet()[3:-2]
                echo = received[0]
        s = ''
        for b in received[1:]:
            if b == 0:
                c = ' '
            else:
                c = chr(b)
            s += c

    def pulse(self):
        """ Continually sends the PULSE command so that the robot knows the client is alive """
        self.pulse_running = True
        while self.pulse_running:
            self.send_packet(PULSE)
            sleep(1.0)  # Default Watchdog interval is 2 seconds, so PULSE every second just to be safe

    def update(self):
        """ Continually receives and decodes packets, storing them as attributes """
        self.update_running = True
        while self.update_running:
            received = self.receive_packet()
            if received is None or self.timeouts > self.allowed_timeouts:  # If too many timeouts have occurred, close
                self.disconnect()
                break
            else:
                decoded = decode_packet(received)
                if decoded['TYPE'] == 'STANDARD':  # Trigger the standard SIP event, and update the latest sonar reading
                    self.standard = decoded
                    for sonar, dist in self.standard['SONARS'].items():
                        self.sonars[sonar] = dist
                    self.standard_event.set()
                elif decoded['TYPE'] == 'CONFIG':
                    self.config_pac = decoded
                    self.config_event.set()
                elif decoded['TYPE'] == 'ENCODER':
                    self.encoder_pac = decoded
                    self.encoder_event.set()

    def start(self):
        """ Open the servers, enable the motors & sonars, and start the pulse & update timers """
        self.send_packet(OPEN)
        pulse = Thread(target=self.pulse, daemon=True)
        pulse.start()
        update = Thread(target=self.update, daemon=True)
        update.start()
        self.wait_for(self.standard_event, 1.0, 'Failed to receive packets from the robot')  # TODO: Field name stylings
        while self.standard['FLAGS'] & 0x3 != 0x3:
            self.send_command(ENABLE, 1)
            self.send_command(SONAR, 1)
            sleep(2.0)

    def wait_for(self, event, timeout=None, message=''):
        """ Waits for an event to occur, with an optional timeout; if it has not occured by then, raise an exception """
        event_occurred = event.wait(timeout)
        event.clear()
        if not event_occurred:
            raise Timeout(message)

##foo = ARCOSClient()
##try:
##    foo.connect()
##    foo.send_command(CONFIG, 1)
##    foo.config_event.wait()
##    foo.config_event.clear()
##    print(foo.config_pac)
##    input()
##    foo.disconnect()
##except KeyboardInterrupt:
##    foo.disconnect()

