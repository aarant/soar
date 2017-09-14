"""  Tkinter wrapper for plotting using matplotlib_

.. _matplotlib: http://matplotlib.org

Note:
    Unlike use of the :func:`soar.hooks.tkinter_hook`, use of this module will not force brain methods to run on the
    main thread alongside Soar's GUI event loop.

    `PlotWindow` is wrapped by the client if it is imported by a Soar brain. This wrapper ensures that the proper mode
    (GUI or headless) is enforced, despite what the brain might pass to the constructor.

    The client will also ensure that, if logging is occurring, any `PlotWindow` objects will have their image data
    included in the log whenever the controller is shut down.

Based on code written by Adam Hartz, August 1st 2012.
"""
# Tk backends, used for plotting in various modes (GUI or headless)
import matplotlib
import platform
if platform.system() == 'Darwin':  # TODO: Test this fix for Soar crashing on macOS
    matplotlib.use('TkAgg')
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, FigureCanvasAgg, NavigationToolbar2TkAgg
import matplotlib.pyplot as plt
from tkinter import Tk, Toplevel, TOP, BOTH


class PlotWindow(plt.Figure):
    """ Tk window containing a matplotlib plot. In addition to the functions described below, also supports all
    functions contained in matplotlib's Axes_ and Figure_ objects.

    .. _Axes: http://matplotlib.sourceforge.net/api/axes_api.html
    .. _Figure: http://matplotlib.sourceforge.net/api/figure_api.html

    Args:
        title (str): The title to be used for the initial window.
        visible (bool): Whether to actually display a Tk window (set to `False` to create and save plots without
            displaying a window).
        standalone (bool, optional): If `True`, plot windows will be kept open by keeping the Tk event loop alive.
    """
    _tk_started = False  # If this is True, uses Toplevel to create the window, otherwise creates a main window

    def __init__(self, title="Plotting Window", visible=True):
        plt.Figure.__init__(self)
        self.add_subplot(111)
        self.visible = visible
        self._destroyed = False
        if self.visible:  # If visible, use Tk's frontend
            # Use the correct method to create a window, then set the tk_started flag to True
            self.canvas = FigureCanvasTkAgg(self, Toplevel() if self.__class__._tk_started else Tk())
            self.__class__._tk_started = True
            self.title(title)
            self.make_window()
            self.show()
        else:
            self.canvas = FigureCanvasAgg(self)

    def make_window(self):
        """ Pack the plot and matplotlib toolbar into the containing Tk window.

        This method is called during initialization and it is unlikely you will need to call it elsewhere.
        """
        self.canvas.get_tk_widget().pack(side=TOP, fill=BOTH, expand=1)
        self.toolbar = NavigationToolbar2TkAgg(self.canvas, self.canvas._master)
        self.toolbar.update()
        self.canvas._tkcanvas.pack(side=TOP, fill=BOTH, expand=1)

    def destroy(self):
        """ Destroy the Tk window.

        Note that after calling this method (or manually closing the Tk window), this :py:class:`PlotWindow` cannot be
        used.
        """
        try:  # Try and destroy the window
            self.canvas._master.destroy()
        except:
            pass  # It was probably already destroyed
        self._destroyed = True

    def clear(self):
        """ Clear the plot, keeping the Tk window active. """
        self.clf()
        self.add_subplot(111)
        if self.visible:
            self.show()

    def show(self):
        """ Update the canvas image (automatically called for most functions). """
        self.canvas.show()

    def __getattr__(self, name):
        show = True
        if name.startswith('_'):
            name = name[1:]
            show = False
        if hasattr(self.axes[0], name):
            attr = getattr(self.axes[0], name)
            if hasattr(attr,'__call__'):
                if show:
                    def tmp(*args,**kwargs):
                        out = attr(*args,**kwargs)
                        if self.visible:
                            self.show()
                        return out
                    return tmp
                else:
                    return attr
            else:
                return attr
        else:
            raise AttributeError("PlotWindow object has no attribute %s" % name)
        
    def title(self, title):
        """ Change the title of the Tk window """
        self.canvas._master.title(title)
        
    def legend(self, *args):
        """ Create a legend for the figure (requires plots to have been made with labels) """
        handles, labels = self.axes[0].get_legend_handles_labels()
        self.axes[0].legend(handles, labels)
        if self.visible:
            self.show()

    def save(self, fname, **kwargs):
        """ Save this plot as an image.  File type determined by extension of filename passed in.

        See documentation for savefig_.

        .. _savefig: http://matplotlib.sourceforge.net/api/figure_api.html

        Args:
            fname: The file to create, which may be a path or a file-like object.
        """
        self.savefig(fname, **kwargs)

    def stay(self):
        """ Start the Tkinter window's main loop (e.g., to keep the plot open at the end of the execution of a script)
        """
        self.canvas._master.mainloop()

    def plot(self, *args, **kwargs):
        """ Plot lines and/or markers to the Axes. See pyplot_ for more information.

        .. _pyplot: https://matplotlib.org/api/pyplot_api.html#matplotlib.pyplot.plot
        """
        self.__getattr__('plot')(*args, **kwargs)
