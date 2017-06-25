"""
Tkinter wrapper for plotting using matplotlib_

.. _matplotlib: http://matplotlib.org
"""
# hartz 01 august 2012

#imports for tk backend
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2TkAgg, FigureCanvasAgg
import matplotlib.pyplot as _p
import tkinter

# make mainloop() interruptable by periodically waking it
tcl =tkinter.Tcl()
def reafter():
        tcl.after(500,reafter)
tcl.after(500,reafter)

class PlotWindow(_p.Figure):
    """
    Tk window containing a matplotlib plot.  In addition to the functions
    described below, also supports all functions contained in matplotlib's
    Axes_ and Figure_ objects.

    .. _Axes: http://matplotlib.sourceforge.net/api/axes_api.html
    .. _Figure: http://matplotlib.sourceforge.net/api/figure_api.html
    """
    def __init__(self, title="Plotting Window", visible=True, toplevel=tkinter.Toplevel):
        """
        :param title: The title to be used for the window initially
        :param visible: Whether to actually display a Tk window (set to
                        ``False`` to create and save plots without a window
                        popping up)
        """
        _p.Figure.__init__(self)
        self.add_subplot(111)
        self.visible = visible
        if self.visible:
            self.canvas = FigureCanvasTkAgg(self, toplevel())
            self.title(title)
            self.makeWindow()
            self.show()
        else:
            self.canvas = FigureCanvasAgg(self)

    def makeWindow(self):
        """
        Pack the plot and matplotlib toolbar into the containing Tk window
        (called by initializer; you will probably never need to use this).
        """
        self.canvas.get_tk_widget().pack(side=tkinter.TOP, fill=tkinter.BOTH, expand=1)
        self.toolbar = NavigationToolbar2TkAgg( self.canvas, self.canvas._master )
        self.toolbar.update()
        self.canvas._tkcanvas.pack(side=tkinter.TOP, fill=tkinter.BOTH, expand=1)

    def destroy(self):
        """
        Destroy the Tk window.  Note that after calling this method (or
        manually closing the Tk window), this :py:class:`PlotWindow` cannot be
        used.
        """
        try:
            self.canvas._master.destroy()
        except:
            pass # probably already destroyed...

    def clear(self):
        """
        Clear the plot, keeping the Tk window active
        """
        self.clf()
        self.add_subplot(111)
        if self.visible:
            self.show()

    def show(self):
        """
        Update the canvas image (automatically called for most functions)
        """
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
        
    def title(self,title):
        """
        Change the title of the Tk window
        """
        self.canvas._master.title(title)
        
    def legend(self, *args):
        """
        Create a legend for the figure (requires plots to have been made with
        labels)
        """
        handles, labels = self.axes[0].get_legend_handles_labels()
        self.axes[0].legend(handles, labels)
        if self.visible:
            self.show()

    def save(self, fname):
        """
        Save this plot as an image.  File type determined by extension of filename passed in.  
        See documentation for savefig_.

        :param fname: The name of the file to create.

        .. _savefig: http://matplotlib.sourceforge.net/api/figure_api.html
        """
        self.savefig(fname)

    def stay(self):
        """
        Start the Tkinter window's main loop (e.g., to keep the plot open at
        the end of the execution of a script)
        """
        self.canvas._master.mainloop()
