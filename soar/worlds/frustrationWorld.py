from soar.sim.world import *

world = World(dimensions=(4, 4), initial_position=(0.5, 0.5, 0),
              objects=[Wall((1, 0), (1, 2)),
                       Wall((1, 2), (2, 2)),
                       Wall((1, 3), (3, 3)),
                       Wall((3, 3), (3, 0)),
                       Wall((3, 1), (2, 1))])
