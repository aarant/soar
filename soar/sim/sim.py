from time import sleep

from soar.client import client
from soar.client.messages import *
from soar.gui.canvas import Point
from math import pi

def start_sim():
    counter = 0
    while True:
        if counter > 1000:
            client.message(CLOSE_SIM)
            break
        client.message(MOVE_OBJECTS)
        counter += 1
        sleep(0.010)