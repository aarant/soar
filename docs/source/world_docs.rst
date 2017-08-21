Worlds
******
A Soar world is a Python file containing the definition of a world used for simulation. It may contain any number of simulated objects, and subclasses
of :class:`soar.sim.world.World` may change its behavior further.

Properties
==========
To be usable in Soar, each world file must have the following attributes:

* `world`: An instance of :class:`soar.sim.world.World`, or an instance of a subclass defined by the user.

:class:`WorldObjects <soar.sim.world.WorldObject>` may be added to the world in the initial constructor, or after the object has been created, as long 
as this is done in the world file at some point.
