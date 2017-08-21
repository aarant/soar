Logging
=======
Soar logging is done via JSON_ objects separated by newlines. All logged objects will contain a `type` key.
There are various types of logged objects:

* `meta`: A typical `meta` object might look like:
  
  .. code-block:: none
     
     {"version": "1.0.0dev3", "brain": "path/to/brain.py", "type": "meta", "world": "path/to/world.py", "simulated": false}
     
  containing information about the controller when it was loaded. When a simulation completes, the following `meta` object is logged:
  
  .. code-block:: none
  
     {"type": "meta", "completed": <time elapsed>}
     
* `step`: Step objects are logged before every step, and one is logged after the simulation is stopped as well:

  .. code-block:: none
     
     {"type": "meta", "step": <step_number>, "elapsed": <time elapsed>, "brain_print": <brain stdout>, "robot": <serialized robot data>}
     
  containing information about the step.
  
* `plot`: Plot objects are logged whenever the user closes a simulation with a :class:`PlotWindow <soar.gui.plot_window.PlotWindow>` open:

  .. code-block:: none
  
     {"type": "plot", "data": <hex data of png image of plot>}
          
.. _JSON: http://www.json.org/
