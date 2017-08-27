.. Soar documentation master file, created by
   sphinx-quickstart on Tue Jul 11 17:11:24 2017.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Soar Documentation
******************
Soar (Snakes on a Robot) is a Python framework for simulating and interacting with robots.

The software is designed to be the following:

* **painless**: Using Soar for its intended purpose should be *trivial*. A student using Soar as part of an intro
  robotics course should, in the ideal case, have to look at :doc:`getting_started` and nothing else.
  
* **extensible**: Soar can support nearly any type of robot and any type of connection, so long as the user 
  provides a suitable interface. Connect to robot's over a serial port, WiFi, Bluetooth, etc--Soar is 
  interface-agnostic. Though Soar provides basic physics for 2D collision detection and movement, the physics
  of simulated worlds and objects can be completely overidden.
  
* **simulation-driven**: The most typical use case of Soar will be to run some stepwise simulation on a certain
  robot type, with some :doc:`brain <brain_docs>` controlling it. It is not primarily designed for persistent robots that are always on or for situations where stepwise interaction is not suitable.
  
* **multiplatform**: Soar uses no platform specific features, and uses Python's standard GUI package, Tkinter_,
  for its GUI. Soar should thus work on any platform with a standard Python interpreter of version 3.5 or 
  later. Soar has been tested on Fedora 25 GNU/Linux, and Windows 8. If an issue arises running Soar on your platform, open an issue_ on GitHub.
  
* **open source**: Soar is licensed under the LGPLv3_, and may be used as a library by projects with other licenses.

To start using Soar, read the :doc:`getting_started` guide, or look at the documentation for :doc:`brains <brain_docs>` and :doc:`worlds <world_docs>`.

.. toctree::
   :maxdepth: 3
   :caption: Contents:
   
   getting_started
   brain_docs
   world_docs
   logging
   Module Documentation <soar>

.. _issue: https://github.com/arantonitis/soar/issues
.. _Tkinter: https://docs.python.org/3.5/library/tkinter.html
.. _LGPLv3: https://www.gnu.org/licenses/lgpl-3.0.en.html

Development
===========
Only stable releases of Soar will be published to PyPI_ or the releases_. Development versions will exist only in the GitHub repo itself, and will be marked ith a ``.dev<N>`` suffix.

Typical versioning will look like the following: ``<MAJOR>.<MINOR>.<PATCH>``. Major releases break backward compatibility, minor releases add functionality but maintain backward compatibility,
and patch releases address bugs or fix small things.

If you have a specific feature you'd like to see in Soar, or a specific robot type you'd like bundled with the base software, or just want to contribute, consider opening a pull request.

.. _PyPI: https://pypi.python.org/pypi/Soar/
.. _releases: https://github.com/arantonitis/soar/releases

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
