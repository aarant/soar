from math import pi

from soar.sim.world import *
world = World(dimensions=(8, 1.5), initial_position=(2.0, 0.5, -pi/6), objects=[Wall((2, 1), (2.5, 1)),
                                                                                Wall((3.25, 1), (3.75, 1)),
                                                                                Wall((4.5, 1), (5.0, 1))])
