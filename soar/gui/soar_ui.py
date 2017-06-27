"""SoaR v0.7.2 UI """

from queue import Queue
from threading import Thread, Lock
import os
from time import sleep

from tkinter import *
from tkinter import filedialog

from soar import client
from soar.gui.canvas import SoarCanvas, SoarCanvasFrame
from soar.gui.output import OutputFrame
from soar.world.base import World


class SoarUI(Tk):
    image_dir = os.path.dirname(__file__)

    def __init__(self, parent=None, brain_path=None, world_path=None, title='SoaR v0.7.2'):
        Tk.__init__(self, parent)
        self.title(title)
        self.play_image = PhotoImage(file=os.path.join(self.image_dir, 'play.gif'))
        self.pause_image = PhotoImage(file=os.path.join(self.image_dir, 'pause.gif'))
        self.step_image = PhotoImage(file=os.path.join(self.image_dir, 'step.gif'))
        self.stop_image = PhotoImage(file=os.path.join(self.image_dir, 'stop.gif'))
        self.play = Button(self)
        self.step = Button(self)
        self.stop = Button(self)
        self.reload = Button(self)
        self.brain_but = Button(self)
        self.world_but = Button(self)
        self.sim_but = Button(self)
        self.real = Button(self)
        self.output = OutputFrame(self)
        self.initialize()
        self.brain_path = brain_path
        self.world_path = world_path
        if self.brain_path is not None:
            self.load_brain()
        if self.world_path is not None:
            self.load_world()
        self.windows = []
        self.sim_canvas = None
        self.protocol('WM_DELETE_WINDOW', self.close)
        self.file_opt = {
            'defaultextension': '.py',
            'filetypes': [('all files', '.*'), ('python files',' .py')],
            'parent': parent,
            'title': "Find your file",
        }
        self.draw_queue = Queue(maxsize=1000)
        self.print_queue = Queue(maxsize=1000)

    def initialize(self):
        """ Initializes the grid geometry """
        self.grid()
        self.reset()
        self.play.grid(column=0, row=0, pady=5)
        self.step.grid(column=1, row=0, pady=5)
        self.stop.grid(column=2, row=0, pady=5)
        self.reload.grid(column=3, row=0, pady=5)
        self.brain_but.grid(column=4, row=0)
        self.world_but.grid(column=5, row=0)
        self.sim_but.grid(column=6, row=0)
        self.real.grid(column=7, row=0)
        self.output.grid(column=0, row=1, columnspan=8, sticky='EW')

    def reset(self):
        """ Resets all of the button states to what they are at the start of the program, before any files are loaded"""
        self.play.config(state=DISABLED, image=self.play_image, command=self.play_cmd)
        self.step.config(state=DISABLED, image=self.step_image, command=self.step_cmd)
        self.stop.config(state=DISABLED, image=self.stop_image, command=self.stop_cmd)
        self.reload.config(state=DISABLED, text='RELOAD', command=self.reload_cmd)
        self.brain_but.config(state=NORMAL, text='BRAIN', command=self.brain_cmd)
        self.world_but.config(state=NORMAL, text='WORLD', command=self.world_cmd)
        self.sim_but.config(state=DISABLED, text='SIMULATOR', command=self.sim_cmd)
        self.real.config(state=DISABLED, text='REAL ROBOT', command=self.real_cmd)
        self.output.clear()

    def mainloop(self, n=0):
        """ Enters the Tk event loop, and restarts the client as a new thread """
        t = Thread(target=client.mainloop, daemon=True)
        t.start()
        self.after(0, self.tick)
        Tk.mainloop(self, n)
        t.join()

    def toplevel(self, sim_linked=True):
        """ Adds a new window to the UI's internal list, and returns a new Toplevel window,
        optionally linking it to the simulator window's status

        Args:
            sim_linked (bool): If True, the window will be destroyed whenever the simulator window is destroyed.
        """
        t = Toplevel()
        self.windows.append((t, sim_linked))
        return t

    def canvas_from_world(self, world):
        dim_x, dim_y = world.dimensions
        max_dim = max(dim_x, dim_y)
        width = int(dim_x / max_dim * 500)
        height = int(dim_y / max_dim * 500)
        options = {'width': width, 'height': height, 'pixels_per_meter': 500 / max_dim, 'bg': 'white'}
        t = self.toplevel()
        t.title('SoaR v0.7.2 Simulation')
        t.protocol('WM_DELETE_WINDOW', self.close_cmd)
        t.aspect(width, height, width, height)
        f = SoarCanvasFrame(t)
        f.pack(fill=BOTH, expand=YES)
        c = SoarCanvas(f, **options)
        c.pack(fill=BOTH, expand=YES)
        self.sim_canvas = c
        return c

    def reset_ui(self):
        while not self.print_queue.empty():
            task = self.print_queue.get()
            self.print_queue.task_done()
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
        while not self.print_queue.empty():
            texts = self.print_queue.get()
            self.output.insert(texts)
            self.print_queue.task_done()
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
        client.message('CLOSE')  # HACK
        client.message('CLOSE')

    def play_cmd(self):
        self.play.config(image=self.pause_image, command=self.pause_cmd)
        self.stop.config(state=NORMAL)
        client.message(client.start_controller)

    def pause_cmd(self):
        self.play.config(image=self.play_image, command=self.play_cmd)
        client.message(client.pause_controller)

    def step_cmd(self):
        self.stop.config(state=NORMAL)
        client.message(client.step_controller)

    def stop_cmd(self):
        self.play.config(image=self.play_image, command=self.play_cmd, state=DISABLED)
        self.step.config(state=DISABLED)
        self.stop.config(state=DISABLED)
        client.message(client.stop_controller)

    def reload_cmd(self):
        # Reload consists of killing the brain, and simulator (or real robot process),
        # followed by opening them up again. We ignore brain death once when doing this.
        #
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
        if self.sim_canvas:
            self.sim_cmd()

    def close_cmd(self, shutdown=True):
        if shutdown:
            client.message(client.shutdown_controller)
        if self.sim_canvas:
            self.draw_queue.put('CLOSE_SIM')
        self.play.config(state=DISABLED, image=self.play_image, command=self.play_cmd)
        self.step.config(state=DISABLED, image=self.step_image, command=self.step_cmd)
        self.stop.config(state=DISABLED, image=self.stop_image, command=self.stop_cmd)
        self.reload.config(state=NORMAL)

    def load_brain(self):
        self.real.config(state=NORMAL)
        client.output('LOAD BRAIN:', self.brain_path)
        if self.world_path is not None:
            self.sim_but.config(state=NORMAL)

    def load_world(self):
        client.output('LOAD WORLD:', self.world_path)
        if self.brain_path is not None:
            self.sim_but.config(state=NORMAL)


    def brain_cmd(self):
        new_brain = filedialog.askopenfilename(**self.file_opt)
        if new_brain:
            if self.brain_path is not None and self.world_path is not None:
                self.brain_path = new_brain
                self.reload_cmd()
            else:
                self.brain_path = new_brain
                client.message(client.load_brain, new_brain)
                self.load_brain()

    def world_cmd(self):
        new_world = filedialog.askopenfilename(**self.file_opt)
        if new_world:
            if self.brain_path is not None and self.world_path is not None:
                self.world_path = new_world
                self.reload_cmd()
            else:
                self.world_path = new_world
                client.message(client.load_world, new_world)
                self.load_world()

    def sim_cmd(self):
        client.message(client.make_sim)  # TODO: Don't know how long this takes
        self.play.config(image=self.play_image, state=NORMAL)
        self.step.config(state=NORMAL)
        self.stop.config(state=DISABLED)
        self.reload.config(state=NORMAL)
        self.sim_but.config(state=DISABLED)
        self.real.config(state=DISABLED)

    def real_cmd(self):
        client.message(client.make_interface)
        self.play.config(image=self.play_image, state=NORMAL)
        self.sim_but.config(state=DISABLED)
        self.real.config(state=DISABLED)
