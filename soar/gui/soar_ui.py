import time
from queue import Queue
from threading import Thread

from tkinter import *
from tkinter import filedialog

from soar.client import client
from soar.client.messages import *
from soar.geometry import *
from soar.gui.canvas import SoarCanvas

def polygon():

    # Building the 8-sided shape of the sonar faces
    s = [Point(0, 0) for i in range(9)]
    s[1].add((1, 0))
    s[2].add((2, 0))
    s[2].rotate(s[1], 2 * pi / 14.0)
    for i in range(3, 9):
        s[i].add(s[i - 1])
        s[i].scale(2.0, s[i - 2])
        s[i].rotate(s[i - 1], 2 * pi / 14.0)
    s = PointCollection(s, fill='red', tags='poly')
    return s

class SoarUI(Tk):
    def __init__(self, parent=None, brain=None, world=None, title='SoaR v0.3.0'):
        Tk.__init__(self, parent)
        self.parent = parent
        self.initialize()
        self.real_set = False
        self.brain = brain
        self.world = world
        self.title(title)
        self.protocol('WM_DELETE_WINDOW', self.close)
        self.file_opt = {
            'defaultextension': '.py',
            'filetypes': [('all files','.*'),('python files','.py')],
            'parent': parent,
            'title': "Find your file",
        }
        self.queue = Queue(maxsize=1000)

    def mainloop(self, n=0):
        t = Thread(target=client.mainloop, daemon=True)
        t.start()
        Tk.mainloop(self, n)
        t.join()

    def close(self):
        self.destroy()
        client.message(CLOSE)  # HACK
        client.message(CLOSE)

    def initialize(self):
        self.grid()

        self.start = Button(self,text=u'START',command=self.start_cmd, padx=50, pady=50, state=DISABLED)
        self.pause = Button(self,text=u'PAUSE',command=self.pause_cmd, padx=50, pady=50, state=DISABLED)
        self.step = Button(self,text=u'STEP',command=self.step_cmd, padx=50, pady=50, state=DISABLED)
        self.reload = Button(self,text=u'RELOAD',command=self.reload_cmd, padx=50, pady=50, state=DISABLED)
        self.world_but = Button(self,text=u'WORLD',command=self.world_cmd, padx=50, pady=50, state=NORMAL)
        self.brain_but = Button(self,text=u'BRAIN',command=self.brain_cmd, padx=50, pady=50, state=NORMAL)
        self.sim = Button(self,text=u'SIMULATOR',command=self.sim_cmd, padx=50, pady=50, state=DISABLED)
        self.real = Button(self,text=u'REAL ROBOT',command=self.real_cmd, padx=50, pady=50, state=DISABLED)

        self.start.grid(column = 0, row = 0, sticky='EW')
        self.pause.grid(column = 1, row = 0, sticky='EW')
        self.step.grid(column = 2, row = 0, sticky='EW')
        self.reload.grid(column = 3, row = 0, sticky='EW')
        self.brain_but.grid(column = 4, row = 0, sticky='EW')
        self.world_but.grid(column = 5, row = 0, sticky='EW')
        self.sim.grid(column = 6, row = 0, sticky='EW')
        self.real.grid(column = 7, row = 0, sticky='EW')

        self.grid_columnconfigure(0,weight=1)
        self.resizable(True,False)

    def reset(self):
        ready_for_action = NORMAL if self.world is not None and self.brain is not None else DISABLED
        self.start.config(state=ready_for_action)
        self.pause.config(state=ready_for_action)
        self.step.config(state=ready_for_action)
        self.reload.config(state=ready_for_action)
        self.sim.config(state=ready_for_action)
        self.real.config(state=ready_for_action)

    def start_cmd(self):
        assert self.brain is not None and (self.real_set or self.world is not None)
        client.message(START_SIM, self.queue)

    def pause_cmd(self):
        assert self.brain is not None and (self.real_set or self.world is not None)
        client.message(PAUSE_SIM, self.queue)

    def step_cmd(self):
        assert self.brain is not None and not self.real_set and self.world is not None
        client.message(STEP_SIM, self.queue)

    def reload_cmd(self):
        # Reload consists of killing the brain, and simulator (or real robot process),
        # followed by opening them up again. We ignore brain death once when doing this.
        #
        client.message(CLOSE_SIM)
        client.message(LOAD_WORLD, self.world)
        client.message(LOAD_BRAIN, self.brain)

    def brain_cmd(self):
        new_brain = filedialog.askopenfilename(**self.file_opt)
        old_brain = self.brain
        if new_brain:
            self.brain = new_brain
            client.message(LOAD_BRAIN, new_brain)
        else:
            return
        if self.world is not None:
            self.reload_cmd()
        self.reset()

    def world_cmd(self):
        new_world = filedialog.askopenfilename(**self.file_opt)
        if new_world:
            self.world = new_world
        else:
            return
        client.message(LOAD_WORLD, self.world)

        #if self.brain is not None:
            #self.reload_cmd()
        self.reset()

    def sim_cmd(self):
        assert self.world is not None
        self.real_set = False
        client.message(MAKE_SIM)
        world_options = self.queue.get()
        self.queue.task_done()
        self.sim = SoarCanvas(self, **world_options)
        self.sim.grid(row=1)

        def tick():
            while not self.queue.empty():
                obj = self.queue.get()
                if obj == 'DESTROY':
                    self.sim.destroy()
                    self.queue.task_done()
                    return
                obj.delete(self.sim)
                obj.draw(self.sim)
                self.queue.task_done()
            self.after(10, tick)

        self.after(0, tick)


    def real_cmd(self):
        self.real_set = True
        self.pause_cmd()
        client.message(SIM_MSG,CLOSE_MSG)
        client.message(OPEN_MSG,PIONEER_PROC)
