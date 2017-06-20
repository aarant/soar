from serial import *
from serial.tools.list_ports import comports

def packet_checksum(data):
    """ Calculates and returns the ARCOS packet checksum of a partial packet, most significant byte first

    Args:
        data (list): A list of data bytes

    Returns: # TODO
    """
    checksum = 0
    i = 3
    n = len(data)-2
    while n > 1:
        checksum += (data[i] << 8) | data[i+1]
        checksum &= 0xffff
        n -= 2
        i += 2
    if n > 0:
        checksum ^= data[i]
    return [checksum >> 8, checksum & 0xff]

class ArcosConnection:
    def __init__(self, timeout=1.0, writeTimeout=1.0):
        self.timeout = timeout
        self.writeTimeout = writeTimeout

    def send_packet(self, *data):
        # TODO: Data elements could be strings or ints
        packet = [0xfa, 0xfb, len(data) + 2] + data  # 0xfa, 0xfb are the packet header
        packet.extend(packet_checksum(packet))
        self.ser.write(bytes(packet))

    def connect(self):
        ports = [port_info.device for port_info in comports()]
        for port in ports:
            connect_with_baud = lambda baud: Serial(port=port, baudrate=baud, timeout=self.timeout, writeTimeout=self.writeTimeout)
            for baud in reversed([9600,19200,38400,57600,115200]):
                self.ser = connect_with_baud(baud)
                self.ser.open()

arcos = ArcosConnection()
arcos.connect()

