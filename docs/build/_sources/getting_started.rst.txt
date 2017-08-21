Getting Started
***************
This guide will outline how to install and use Soar. For greater detail see the documentation on 
:doc:`brains <brain_docs>` and :doc:`worlds <world_docs>`, or perhaps the :doc:`Module Documentation <soar>`.

Installation
============
Installing Soar is (hopefully) painless and primarily done 3 ways, ordered by decreasing ease:

.. note::
   
   * Most Python installations will already have `setuptools`, necessary to install Soar, but if not, see `this documentation`_ to install it.

   * Installing Soar will also install pyserial_ version 3.0 or later.

   * Soar was developed exclusively with `Python 3.5`_ or later in mind. Your mileage may vary or be nonexistent if using an earlier version.

From PyPI
---------
Soar can be installed from the `Python Package Index (PyPI)`_ by running ``pip install soar``.

This will install the latest stable (not development) release.

From Releases
-------------
An arbitrary stable (not development) Soar release can be installed from the `github releases`_, by downloading the
`.zip` archive and running ``pip install <path-to-zip>``.

From latest source
--------------------
Clone or download the `git repo`_, navigate to the directory, then run:
::
    python3 setup.py sdist
    cd dist
    pip install Soar-<version>.tar.gz

.. _Python Package Index (PyPI): https://pypi.python.org/pypi
.. _pyserial: https://pythonhosted.org/pyserial/
.. _this documentation: https://setuptools.readthedocs.io/en/latest/
.. _github releases: https://github.com/arantonitis/soar/releases
.. _git repo: https://github.com/arantonitis/soar
.. _Python 3.5: https://www.python.org/downloads/release/python-350/

Usage
=====
There are two major 'modes' of operation that Soar offers: simulation of a robot (and possibly other objects), or connecting via a robot-defined
interface. The latter is only usable when running from the GUI; when running headless or from another project, only simulation may be used.

Soar's functionality can be accessed through multiple interfaces, documented below.

Also see the documentation for :doc:`brain_docs` and :doc:`world_docs`.

GUI
---
.. figure:: _static/gui.png
   :align: center
   
   Soar v1.0.0dev3 in KDE

Soar can be started in GUI mode simply by running ``soar`` from the command line. The main interface is fully resizable.

From the main interface, there are multiple panels to interact with:

1. The playback panel. When a robot controller has been loaded, either simulated or through some robot-defined interface, this is available
   and can be used to control playback. Pressing the ``Play`` button for the first time will start the controller and repeatedly step the robot.
   Pressing it while a simulation is running will ``Pause`` it. The ``Step`` button, and its associated entry, will step the controller that many
   times, although this functionality is only available for simulations. The ``Stop`` button stops the controller, and the ``Reload`` button reloads
   the currently loaded brain and world.
   
2. The brain/world loading panel. These buttons are used to load Soar brains and worlds. The default directory for brains is the user's home
   directory. The default directory for worlds is Soar's own soar/worlds/ directory, installed with the project. In order to simulate a robot,
   both a brain and world must be loaded. If connecting through a robot-defined interface, only a brain must be loaded and any loaded world will be
   ignored.
   
3. The simulation/connect panel. These buttons are used to prepare for simulation, or connecting to a robot-defined interface. If a controller has
   already been loaded, clicking either of these will kill it and reload the brain and/or world and prepare a controller of the desired type.
   
4. The output panel. All controller-related output will appear here. Any text the brain prints to ``stdout`` (via `print()`) will appear prefixed by
   `'>>>'`. If an exception occurs when running the controller, its full traceback will also be printed here. The panel is cleared whenever a reload
   occurs.
   
.. figure:: _static/sim.png
   :align: center
   
   Soar v1.0.0dev3 Simulation in KDE
   
The simulation window opens whenever a simulation controller is loaded. Soar widgets like :class:`soar.gui.plot_window.PlotWindow` are linked to this
window, and will be closed whenever it is closed. User-created windows may also be linked to it via use of the :func:`soar.hooks.tkinter_hook`.

The simulation window opens with a default maximum dimension (width or height) of 500 pixels, but may be resized to any size that matches the aspect
ratio of the corresponding world.

Command Line/Headless
---------------------
See the :doc:`command_line` and the documentation for :doc:`logging`.

When running in headless mode, both a brain and world file are required. The simulation will be immediately started, and may never complete if the
brain does not raise an exception or call :func:`soar.hooks.sim_completed`. Typical usage might be to capture the ``stdout`` and ``stderr`` of the
process, terminate it after a set period or time, or ensure that the brain will end the simulation at some point.

In another project
------------------

To use Soar from within another Python project, import :func:`soar.client.main` and pass arguments accordingly. Unless you desire to build Soar's
GUI interface when invoking this function, you will have to pass `headless=True`.

.. note::
   When using Soar's entrypoint from another Python project, you have the advantage of being able to use file-like objects such as `StringIO`
   as log outputs instead of actual files.
