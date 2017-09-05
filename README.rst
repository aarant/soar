|pypi|_ |docs|_ |license|_

.. |pypi| image:: https://img.shields.io/pypi/v/soar.svg
.. _pypi: https://pypi.python.org/pypi/Soar
.. |docs| image:: https://readthedocs.org/projects/snakes-on-a-robot/badge/?version=latest
.. _docs: http://snakes-on-a-robot.readthedocs.io/en/latest
.. |license| image:: https://img.shields.io/github/license/arantonitis/soar.svg
.. _license: https://github.com/arantonitis/soar/blob/master/LICENSE

Soar
****
Soar (Snakes on a Robot) is a Python framework for simulating and interacting with robots.

The software is designed to be the following:

* **painless**: Using Soar for its intended purpose should be *trivial*. A student using Soar as part of an intro
  robotics course should, in the ideal case, have to look at `Getting Started`_ and nothing else.
  
* **extensible**: Soar can support nearly any type of robot and any type of connection, so long as the user 
  provides a suitable interface. Connect to robot's over a serial port, WiFi, Bluetooth, etc--Soar is 
  interface-agnostic. Though Soar provides basic physics for 2D collision detection and movement, the physics
  of simulated worlds and objects can be completely overidden.
  
* **simulation-driven**: The most typical use case of Soar will be to run some stepwise simulation on a certain
  robot type, with some `brain`_ controlling it. It is not primarily designed for persistent robots that are always on or for situations where stepwise interaction is not suitable.
  
* **multiplatform**: Soar uses no platform specific features, and uses Python's standard GUI package, Tkinter_,
  for its GUI. Soar should thus work on any platform with a standard Python interpreter of version 3.5 or 
  later. Soar has been tested on Fedora 25 GNU/Linux, and Windows 8. If an issue arises running Soar on your platform, open an issue_ on GitHub.
  
* **open source**: Soar is licensed under the LGPLv3_, and may be used as a library by projects with other licenses.

To get started using Soar, see the `Getting Started`_ or the `documentation`_.

Installation
============
Installing Soar is (hopefully) painless and primarily done 3 ways, ordered by decreasing ease:

.. note::
   
   * Most Python installations will already have `setuptools`, necessary to install Soar, but if not, see `this documentation`_ to install it.

   * Installing Soar will also install pyserial_ version 3.0 or later, as well as matplotlib_ version 2.0 or later.

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
Clone or download the `git repo`_, navigate to the directory, then run::
   
   python3 setup.py sdist
   cd dist
   pip install Soar-<version>.tar.gz

.. _issue: https://github.com/arantonitis/soar/issues
.. _brain: http://snakes-on-a-robot.readthedocs.io/en/latest/brain_docs.html
.. _Tkinter: https://docs.python.org/3.5/library/tkinter.html
.. _LGPLv3: https://www.gnu.org/licenses/lgpl-3.0.en.html
.. _Getting Started: http://snakes-on-a-robot.readthedocs.io/en/latest/getting_started.html
.. _documentation: http://snakes-on-a-robot.readthedocs.io/en/latest/index.html
.. _Python Package Index (PyPI): https://pypi.python.org/pypi
.. _pyserial: https://pythonhosted.org/pyserial/
.. _matplotlib: https://matplotlib.org/
.. _this documentation: https://setuptools.readthedocs.io/en/latest/
.. _github releases: https://github.com/arantonitis/soar/releases
.. _git repo: https://github.com/arantonitis/soar
.. _Python 3.5: https://www.python.org/downloads/release/python-350/

Development
===========
Only stable releases of Soar will be published to PyPI_ or the `github releases`_. Development versions will exist only in the GitHub repo itself, and will be marked with a ``.dev<N>`` suffix.

Typical versioning will look like the following: ``<MAJOR>.<MINOR>.<PATCH>``. Major releases break backward compatibility, minor releases add functionality but maintain backward compatibility,
and patch releases address bugs or fix small things.

If you have a specific feature you'd like to see in Soar, or a specific robot type you'd like bundled with the base software, or just want to contribute, consider opening a pull request.

Building Documentation
======================
Building a local copy of the docs will require Sphinx_.

Navigate to the ``docs/`` directory and run ``sphinx-build -b html source/ <BUILD_DIR>``.

.. _Sphinx: http://www.sphinx-doc.org/en/stable/
