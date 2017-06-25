""" ARCOS (Advanced Robot Control and Operations Software) Client

Classes and functions for communicating with an ARCOS server running on an Adept MobileRobot platform
(typically Pioneer 2 and 3)
"""


from threading import Thread, Lock
from time import sleep
from serial import *
from serial.tools.list_ports import comports

# ARCOS Client command codes

SYNC0 = 0
SYNC1 = 1
SYNC2 = 2
PULSE = 0  # Reset server watchdog (typically sent every second so that the robot knows the client is alive_
OPEN = 1  # Start up ARCOS server
CLOSE = 2  # Close servers and client connection
POLLING = 3  # Change sonar polling sequence
ENABLE = 4  # if argument is 1, enables the motors, if 0, disables them
SETA = 5
SETV = 6
SETO = 7
MOVE = 8
ROTATE = 9
SETRV = 10
VEL = 11  # Translate at mm/sec forward (if positive) or backward (if negative), limited to velocity cap
HEAD = 12
DHEAD = 13
SAY = 15
JOYREQUEST = 17
CONFIG = 18
ENCODER = 19
RVEL = 21  # Rotate (degrees/sec) counterclockwise (positive) or clockwise (negative)
DCHEAD = 22
SETRA = 23
SONAR = 28  # TODO
STOP = 29  # Stops the robot without disabling the motors
DIGOUT = 30
VEL2 = 32
GRIPPER = 33
ADSEL = 35
GRIPPERVAL = 36
GRIPREQUEST = 37
# TODO

command_types = {
    PULSE: None,
    OPEN: None,
    CLOSE: None,
    ENABLE: int,
    VEL: int,
    RVEL: int,
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
        dict: A dictionary with field names as keys and values as corresponding numbers
    """

    def b_2_i(l, i):  # Takes a list and an index and returns the two bytes combined into an int
        return (l[i] << 8) | (l[i] & 0xff)

    data = {'TYPE': packet[3], 'XPOS': b_2_i(packet, 4), 'YPOS': b_2_i(packet, 6),
            'THPOS': b_2_i(packet, 8), 'L VEL': b_2_i(packet, 10), 'R VEL': b_2_i(packet, 12),
            'BATTERY': packet[14], 'STALL AND BUMPERS': b_2_i(packet, 15), 'CONTROL': b_2_i(packet, 17),
            'FLAGS': b_2_i(packet, 19), 'COMPASS': packet[21], 'SONAR_COUNT': packet[22]}
    sonars = {}
    i = 23
    for sonar in range(data['SONAR_COUNT']):
        number = packet[i]
        dist = b_2_i(packet, i + 1)
        sonars.update({number: dist})
        i += 3
    data.update({'SONARS': sonars})
    return data


class ARCOSClient:
    def __init__(self, timeout=1.0, write_timeout=1.0):
        self.timeout = timeout
        self.write_timeout = write_timeout
        self.serial_lock = Lock()  # A lock is needed so that packets sent by separate threads do not interfere
        self.pulse_running = False

    def send_packet(self, *data):
        """ Sends arbitrary data (in the form of a tuple of bytes) to the ARCOS server

            Thread-safe, by means of a serial lock
        """
        packet = [0xfa, 0xfb, len(data) + 2] + list(data)  # 0xfa, 0xfb are the packet header
        checksum = packet_checksum(packet)  # Calculate the checksum and append it
        packet.extend([checksum >> 8, checksum & 0xff])  # Big-endian two byte integer
        if data[0] != PULSE:  # TODO: For debugging purposes
            print('Sent packet:', [b for b in packet])
        with self.serial_lock:
            self.ser.write(bytearray(packet))

    def receive_packet(self):
        """ Reads an entire ARCOS Packet from the open port, including header and checksum bytes

            If the header or checksum are invalid, raises an InvalidPacket exception
        """
        def read():
            try:
                b = ord(self.ser.read())
            except TypeError:
                raise Timeout
            else:
                return b

        # Grab the packet header and ensure it is valid
        h1 = read()
        h2 = read()
        if h1 != 0xfa or h2 != 0xfb:
            raise InvalidPacket
        data = [0xfa, 0xfb]
        l = read()
        data.append(l)
        for i in range(l):
            data.append(read())

        received_crc = (data[-1] & 0xFF) | (data[-2] << 8)
        crc = packet_checksum(data)
        if crc != received_crc:  # Checksum match failure
            raise InvalidPacket
        # print('Received packet:', [b for b in data])
        return data

    def send_command(self, code, data=None):  # TODO
        if command_types[code] == None:
            self.send_packet(code)
        elif command_types[code] == int:
            arg_type = 0x1b  # Negative or absolute integer
            b = [data >> 8, data & 0xff]
            b.reverse()
            self.send_packet(code, arg_type, *b)
            
    def connect(self):
        """ Attempts to connect and sync with an ARCOS server over a serial port

            If successful, simply returns. Otherwise, raises an ARCOSError exception
        """
        ports = [port_info.device for port_info in comports()]  # Try every available port until we find a robot
        for port in ports:
            connect_with_baud = lambda baud: Serial(port=port, baudrate=baud,
                                                    timeout=self.timeout, writeTimeout=self.write_timeout)
            for baud in [115200, 57600, 38400, 19200, 9600]:  # Connect with the highest baudrate possible
                # Kill the microcontroller servers in case they are already running
                self.ser = connect_with_baud(baud)
                self.send_packet(CLOSE)
                self.ser.close()

                # Connect for real, and flush the input and output buffers
                self.ser = connect_with_baud(baud)
                self.ser.reset_input_buffer()
                self.ser.reset_output_buffer()
                # Try to sync; if there is a timeout, the port is probably not connected to a robot, so move on
                try:
                    self.sync()
                except Timeout:
                    pass
                else:
                    return
        raise ARCOSError('Unable to sync with any ARCOS servers')

    def disconnect(self):
        """ Stops the connected ARCOS server and closes the serial port """
        self.pulse_running = False  # Kill the pulse timer
        self.send_packet(STOP)  # Stop the robot
        self.send_packet(CLOSE)
        self.ser.close()

    def sync(self):
        """ Syncs with and initializes an ARCOS server connected over an open serial port

            Initialization includes enabling the motors and setting up the pulse timer thread
        """
        for sync in [SYNC0, SYNC1, SYNC2]:
            echo = None
            while sync != echo:  # TODO: Is it possible for this to hang?
                self.send_packet(sync)
                received = self.receive_packet()[3:-2]
                echo = received[0]
        s = ''
        for b in received[1:]:
            print(b)
            if b == 0:
                c = ' '
            else:
                c = chr(b)
            s += c
        print(s)

        # Once we've synced, open the servers, enable the motors, and set up the pulse timer
        self.send_packet(OPEN)
        self.send_command(ENABLE, 1)
        t = Thread(target=self.pulse, daemon=True)
        t.start()

    def pulse(self):
        self.pulse_running = True
        while self.pulse_running:
            self.send_packet(PULSE)
            packet = self.receive_packet()
            # print(hex(packet[3]))
            sleep(1.0)
        
            
        

arcos = ARCOSClient()
arcos.connect()

