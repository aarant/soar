from soar.sim.world import *

world = World(dimensions=(8, 8), initial_position=(1.0, 1.0, 0),
              objects=[Block((2, 0), (2, 4)),
                       Block((2, 4), (4, 4)),
                       Block((2, 6), (6, 6)),
                       Block((6, 6), (6, 0)),
                       Block((6, 2), (4, 2))])
