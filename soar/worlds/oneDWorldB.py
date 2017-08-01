from soar.sim.world import *
# Note: The boundary wall is a little unnecessary
world = World(dimensions=(8, 1.5), initial_position=(2.3, 0.5, 0.0), objects=[Wall((0, 1.5), (8, 1.5)),
                                                                              Wall((2, 1), (2.5, 1)),
                                                                              Wall((3.25, 1), (3.75, 1)),
                                                                              Wall((4.5, 1), (5.0, 1))])
