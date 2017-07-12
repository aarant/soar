"""SoaR v0.9.0 UI """

from queue import Queue
from threading import Thread, Lock, Event
import os
import sys
from time import sleep

from tkinter import *
from tkinter import filedialog

from soar import client
from soar.gui.canvas import SoarCanvas, SoarCanvasFrame
from soar.gui.output import OutputRedirect, OutputFrame, SoarIO
from soar.sim.world import World


class ButtonFrame(Frame):
    """ A Tk frame containing an image Button and a Label immediately beneath it, arranged via the grid geometry manager

    Attributes:
        button: The button inside the frame
        label: The label inside the frame

    Args:
        master: The parent widget or window in which to place the frame
        image (optional): The image to place inside the button
        text (optional): The text to place inside the label
        command (optional): The function to call when the button is clicked
        state (optional): The state of the button, either NORMAL or DISABLED
    """
    def __init__(self, master, image=None, text=None, command=None, state=None):
        Frame.__init__(self, master)
        self.button = Button(self)
        self.label = Label(self)
        self.config(image, text, command, state)
        self.button.grid(row=0, column=0)
        self.label.grid(row=1, column=0)

    def config(self, image=None, text=None, command=None, state=None):
        """ Sets the parameters of the button/label

        Args:
            image (optional): The image to place inside the button
            text (optional): The text to place inside the label
            command (optional): The function to call when the button is clicked
            state (optional): The state of the button, either NORMAL or DISABLED
        """
        if image:
            self.button.config(image=image)
        if text:
            self.label.config(text=text)
        if command:
            self.button.config(command=command)
        if state:
            self.button.config(state=state)


class SoarUI(Tk):
    image_dir = os.path.dirname(__file__)
    world_dir = os.path.join(image_dir, '../worlds/')
    brain_dir = os.path.join(image_dir, '../brains/')

    def __init__(self, parent=None, title='SoaR v0.9.0'):
        Tk.__init__(self, parent)
        self.brain_path = None
        self.world_path = None
        self.title(title)
        self.play_image = PhotoImage(file=os.path.join(self.image_dir, 'play.gif'))
        self.pause_image = PhotoImage(file=os.path.join(self.image_dir, 'pause.gif'))
        self.step_image = PhotoImage(file=os.path.join(self.image_dir, 'step.gif'))
        self.stop_image = PhotoImage(file=os.path.join(self.image_dir, 'stop.gif'))
        self.reload_image = PhotoImage(file=os.path.join(self.image_dir, 'reload.gif'))
        self.brain_image = PhotoImage(file=os.path.join(self.image_dir, 'brain.gif'))
        self.world_image = PhotoImage(file=os.path.join(self.image_dir, 'world.gif'))
        self.play = ButtonFrame(self)
        self.step = ButtonFrame(self)
        self.stop = ButtonFrame(self)
        self.reload = ButtonFrame(self)
        self.brain_but = ButtonFrame(self)
        self.world_but = ButtonFrame(self)
        self.sim_but = Button(self)
        self.real = Button(self)
        self.output = OutputFrame(self)
        self.initialize()
        self.windows = []
        self.sim_canvas = None
        self.connected = False
        self.protocol('WM_DELETE_WINDOW', self.close)
        self.file_opt = {
            'defaultextension': '.py',
            'filetypes': [('all files', '.*'), ('python files',' .py')],
            'parent': parent,
            'title': "Find your file",
        }
        self.draw_queue = Queue(maxsize=1000)

    def initialize(self):
        """ Initializes the grid geometry """
        self.grid()
        self.reset(clear_output=False)
        self.play.grid(column=0, row=0, pady=5, sticky='W')
        self.step.grid(column=1, row=0, pady=5, sticky='W')
        self.stop.grid(column=2, row=0, pady=5, sticky='W')
        self.reload.grid(column=3, row=0, pady=5, sticky='W')
        self.brain_but.grid(column=4, row=0, padx=5)
        self.world_but.grid(column=5, row=0, padx=5)
        self.sim_but.grid(column=6, row=0, sticky='E')
        self.real.grid(column=7, row=0, sticky='E')
        self.grid_columnconfigure(3, weight=1)
        self.grid_columnconfigure(6, weight=1)
        self.grid_rowconfigure(2, weight=1)
        self.output.grid(column=0, row=2, columnspan=8, sticky='NSEW')

    def reset(self, clear_output=True):
        """ Resets all of the button states to what they are at initialization, before any files are loaded

        Args:
            clear_output (bool, optional): If True, clears the contents of the output frame
        """
        self.play.config(image=self.play_image, text='Play', command=self.play_cmd, state=DISABLED)
        self.step.config(image=self.step_image, text='Step', command=self.step_cmd, state=DISABLED)
        self.stop.config(image=self.stop_image, text='Stop', command=self.stop_cmd, state=DISABLED)
        self.reload.config(image=self.reload_image, text='Reload', command=self.reload_cmd, state=DISABLED)
        self.brain_but.config(image=self.brain_image, text='Load Brain', command=self.brain_cmd, state=NORMAL)
        self.world_but.config(image=self.world_image, text='Load World', command=self.world_cmd, state=NORMAL)
        self.sim_but.config(text='SIMULATOR', command=self.sim_cmd, state=DISABLED)
        self.real.config(text='REAL ROBOT', command=self.real_cmd, state=DISABLED)
        if clear_output:
            self.output.clear()

    def mainloop(self, n=0):
        """ Enters the Tk event loop, and restarts the client as a new thread

        Redirects stdout and stderr to the GUI's output frame
        """
        t = Thread(target=client.mainloop, daemon=True)
        t.start()
        self.after(0, self.tick)
        _stdout = sys.stdout
        _stderr = sys.stderr
        sys.stdout = SoarIO(self.output.output)
        sys.stderr = SoarIO(self.output.error)
        Tk.mainloop(self, n)
        sys.stdout.close()
        sys.stderr.close()
        sys.stdout = _stdout
        sys.stderr = _stderr
        t.join()

    def toplevel(self, sim_linked=True):
        """ Adds a new window to the UI's internal list, and returns a new Toplevel window,
        optionally linking it to the simulator window

        Args:
            sim_linked (bool): If True, the window will be destroyed whenever the simulator window is destroyed.

        Returns:
            The new Toplevel window
        """
        t = Toplevel()
        self.windows.append((t, sim_linked))
        return t

    def canvas_from_world(self, world):
        """ Creates a SoarCanvas in a new window from a World

        Args:
            world: An instance of World or a subclass

        Returns:
            The new SoarCanvas
        """
        dim_x, dim_y = world.dimensions
        max_dim = max(dim_x, dim_y)
        width = int(dim_x / max_dim * 500)
        height = int(dim_y / max_dim * 500)
        options = {'width': width, 'height': height, 'pixels_per_meter': 500 / max_dim, 'bg': 'white'}
        t = self.toplevel()
        t.title('SoaR v0.9.0 Simulation')
        t.protocol('WM_DELETE_WINDOW', lambda: self.reload_cmd(False))
        t.aspect(width, height, width, height)
        f = SoarCanvasFrame(t)
        f.pack(fill=BOTH, expand=YES)
        c = SoarCanvas(f, **options)
        c.pack(fill=BOTH, expand=YES)
        self.sim_canvas = c
        return c

    def reset_ui(self):
        while not self.draw_queue.empty():
            task = self.draw_queue.get()
            self.draw_queue.task_done()
        for tup in reversed(self.windows):
            window, sim_linked = tup
            if sim_linked:
                self.windows.remove(tup)
                window.destroy()
        self.sim_canvas = None

    def tick(self):
        while not self.draw_queue.empty():
            obj = self.draw_queue.get()
            if isinstance(obj, World) and self.sim_canvas is None:
                self.sim_canvas = self.canvas_from_world(obj)
                obj.draw(self.sim_canvas)
            elif obj == 'CLOSE_SIM':  # Need to flush the queues and kill sim-linked windows
                self.reset_ui()
                break
            else:
                obj.delete(self.sim_canvas)
                obj.draw(self.sim_canvas)
            self.draw_queue.task_done()
        self.after(10, self.tick)

    def close(self):
        self.destroy()
        client.message(client.close)  # HACK TODO
        client.message(client.close)

    def play_cmd(self):
        if self.connected:
            self.play.config(state=DISABLED)
        else:
            self.play.config(image=self.pause_image, text='Pause', command=self.pause_cmd)
        self.stop.config(state=NORMAL)
        client.message(client.start_controller)

    def pause_cmd(self):
        self.play.config(image=self.play_image, text='Play', command=self.play_cmd)
        client.message(client.pause_controller)

    def step_cmd(self):
        self.stop.config(state=NORMAL)
        client.message(client.step_controller)

    def stop_cmd(self):
        self.play.config(image=self.play_image, command=self.play_cmd, state=DISABLED)
        self.step.config(state=DISABLED)
        self.stop.config(state=DISABLED)
        client.message(client.stop_controller)

    def reload_cmd(self, load_controller=True):
        """ Kill the controller, any sim-linked windows, and reload the brain and world """
        client.message(client.shutdown_controller)
        if self.sim_canvas:
            self.draw_queue.put('CLOSE_SIM')
        self.reset()
        if self.brain_path:
            client.message(client.load_brain, self.brain_path)
            self.load_brain()
        if self.world_path:
            client.message(client.load_world, self.world_path)
            self.load_world()
        if load_controller:
            if self.sim_canvas:
                self.sim_cmd()
            if self.connected:
                self.real_cmd()

    def brain_cmd(self):
        new_brain = filedialog.askopenfilename(initialdir=self.brain_dir, **self.file_opt)
        if new_brain:
            # If a brain and world were already loaded, reload
            if self.brain_path is not None and self.world_path is not None:
                self.brain_path = new_brain
                self.reload_cmd()
            else:
                self.brain_path = new_brain
                client.message(client.load_brain, new_brain)
                self.load_brain()
            self.brain_dir = os.path.dirname(self.brain_path)

    def world_cmd(self):
        new_world = filedialog.askopenfilename(initialdir=self.world_dir, **self.file_opt)
        if new_world:
            if self.brain_path is not None and self.world_path is not None:
                self.world_path = new_world
                self.reload_cmd()
            else:
                self.world_path = new_world
                client.message(client.load_world, new_world)
                self.load_world()
            self.world_dir = os.path.dirname(self.world_path)

    def sim_cmd(self):
        if self.connected:
            client.message(client.shutdown_controller)
            self.reload_cmd(False)
        client.message(client.make_sim)
        self.disable_all()  # Client could take arbitrarily long to create the simulator, so disable everything

    def real_cmd(self):
        if self.sim_canvas:
            client.message(client.shutdown_controller)
            self.reload_cmd(False)
        client.message(client.make_interface)
        self.disable_all()

    def controller_failure(self):
        self.reset(clear_output=False)
        self.reload.config(state=NORMAL)
        if self.sim_canvas:
            t = self.sim_canvas.master.master
            self.reload.config(command=lambda: self.reload_cmd(load_controller=False))
            t.protocol('WM_DELETE_WINDOW', lambda: self.draw_queue.put('CLOSE_SIM'))

    def sim_ready(self):
        self.connected = False
        self.play.config(image=self.play_image, state=NORMAL)
        self.step.config(state=NORMAL)
        self.stop.config(state=DISABLED)
        self.reload.config(state=NORMAL)
        self.brain_but.config(state=NORMAL)
        self.world_but.config(state=NORMAL)
        self.sim_but.config(state=DISABLED)
        self.real.config(state=NORMAL)

    def real_ready(self):
        self.connected = True
        self.sim_canvas = None
        self.play.config(image=self.play_image, state=NORMAL)
        self.step.config(state=DISABLED)
        self.stop.config(state=DISABLED)
        self.reload.config(state=NORMAL)
        self.brain_but.config(state=NORMAL)
        self.world_but.config(state=NORMAL)
        self.sim_but.config(state=NORMAL if self.world_path else DISABLED)
        self.real.config(state=DISABLED)

    def soft_reload(self):
        """ A soft reload, that sends no commands to the client """
        self.reset(clear_output=False)
        if self.brain_path is not None:
            self.load_brain()
        if self.world_path is not None:
            self.load_world()

    def load_brain(self):
        self.real.config(state=NORMAL)
        if self.world_path is not None:
            self.sim_but.config(state=NORMAL)

    def load_world(self):
        if self.brain_path is not None:
            self.sim_but.config(state=NORMAL)

    def disable_all(self):
        self.play.config(state=DISABLED)
        self.step.config(state=DISABLED)
        self.stop.config(state=DISABLED)
        self.reload.config(state=DISABLED)
        self.brain_but.config(state=DISABLED)
        self.world_but.config(state=DISABLED)
        self.sim_but.config(state=DISABLED)
        self.real.config(state=DISABLED)
