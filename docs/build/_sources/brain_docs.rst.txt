Brains
******
A Soar brain is a Python module used to control a robot. Brains can be used to control the movement of a simulated robot, connect to a real interface
to control a real one, or multiplex between the two. Whenever a brain is loaded by Soar, the content of the module is compiled and executed in an
isolated namespace, meaning that variable names will not conflict with those defined by Soar, except where documented below. All Python builtins are
available to brains--they are normal Python modules with certain reserved words used by Soar.

Properties
==========
A brain file must have the following attributes to be usable in Soar:

* `robot`: This should be an instance of :class:`soar.robot.base.BaseRobot`, an instance of a subclass (like :class:`soar.robot.pioneer.PioneerRobot`,
  or some object that supports identical methods. `robot` is what defines the interface, if any, to connect to something outside of Soar, as well as
  what can be done with that robot type--i.e movement, sensor readings, etc.
  
* `on_load()`, `on_start()`, `on_step(duration)`, `on_stop()`, `on_shutdown()` functions. While not strictly necessary (if any of these are not
  defined, they will be silently replaced by empty functions by Soar, they are the main ways in which the brain actually interacts with the controller.
  
  * `on_load()` is called exactly once, when the controller is loaded, and always after the robot's corresponding `on_load()` method.
  
  * `on_start()` is also called exactly once, when the controller is started for the first time, just before the first actual step. The robot's
    `on_start()` method is always called just before the brain's.
    
  * `on_step(duration)` is called whenever the controller steps, *before* the robot's `on_step(duration)` method is called. `duration` specifies how
    long the step lasts, which may not be constant from step to step. Note that if this function takes longer to execute than `duration`, the 
    `duration` argument that the robot receives will be lengthened accordingly.
    
  * `on_stop()` is called exactly once when the controller stops, *before* the robot's `on_stop()` method is called.
  
  * `on_shutdown()` is called exactly once when the controller is shut down, *before* the robot's `on_shutdown()` method. Typically, this function
    performs any cleanup desired.
    
These names should be considered reserved by Soar when used in a brain module.

Hooks
=====
Hooks are optional functions that brains can import to interact with Soar on a more flexible level than the controller provides. Hooks include everything
defined in :mod:`soar.hooks`, as well as GUI widgets like :class:`soar.gui.plot_window.PlotWindow`.

The names of hooks, as well as widget names like `PlotWindow`, should be considered reserved names and not used otherwise, as the client detects their
presence by name.

.. note::
   The usage of hooks outside of the controller methods (`on_load()`, `on_start()`, etc) is allowed but discouraged. Users may create 
   :class:`PlotWindow <soar.gui.plot_window.PlotWindow>` plots in the main body of the brain module, hook Tkinter widgets into the 
   :func:`tkinter_hook <soar.hooks.tkinter_hook>`, etc, with no issues, but should be aware that hooks like :func:`sim_completed <soar.hooks.sim_completed>` and
   :func:`elapsed <soar.hooks.elapsed>` may not function as expected outside of a controller (they do nothing and return `0.0`, respectively).
