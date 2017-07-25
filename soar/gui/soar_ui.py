""" Soar v0.11.0 Main GUI

Classes for building the main GUI, which allows the user to load brains & worlds, start simulations, etc.
"""
import os
import traceback as tb
from queue import Queue
from threading import Thread
from tkinter import *
from tkinter import filedialog

from soar.common import *
from soar.gui.canvas import canvas_from_world
from soar.gui.output import OutputFrame, SoarIO


class ButtonFrame(Frame):
    """ A Tk frame containing an image Button and a Label immediately beneath it, arranged via the grid geometry manager.

    Attributes:
        button: The button inside the frame.
        label: The label inside the frame.

    Args:
        master: The parent widget or window in which to place the frame.
        image (optional): The image to place inside the button.
        text (optional): The text to place inside the label.
        command (optional): The function to call when the button is clicked.
        state (optional): The state of the button, either NORMAL or DISABLED.
    """
    def __init__(self, master, image=None, text=None, command=None, state=None):
        Frame.__init__(self, master)
        self.button = Button(self)
        self.label = Label(self)
        self.config(image, text, command, state)
        self.button.grid(row=0, column=0)
        self.label.grid(row=1, column=0)

    def config(self, image=None, text=None, command=None, state=None):
        """ Sets the parameters of the button/label.

        Args:
            image (optional): The image to place inside the button.
            text (optional): The text to place inside the label.
            command (optional): The function to call when the button is clicked.
            state (optional): The state of the button, either NORMAL or DISABLED.
        """
        if image:
            self.button.config(image=image)
        if text:
            self.label.config(text=text)
        if command:
            self.button.config(command=command)
        if state:
            self.button.config(state=state)

    def __getitem__(self, item):  # For getting the state of the widget
        if item == 'state':
            return self.button['state']
        else:
            raise KeyError


class IntegerEntry(Entry):
    """ A Tk entry that only allows integers.

    Args:
        parent: The parent Tk widget or window.
        value (str): The initial value. Must be able to be cast to ``int``.
        **kwargs: Arbitrary Tk keyword arguments.
    """
    def __init__(self, parent, value='', **kwargs):
        Entry.__init__(self, parent, **kwargs)
        vcmd = (self.register(self._validate), '%S')
        self.config(validate='key', vcmd=vcmd)
        self.insert(0, value)

    def _validate(self, S):
        try:
            int(S)
        except ValueError:
            self.bell()
            return False
        else:
            return True


class LoadingIcon(Label):
    """ An animated loading icon that can be shown or hidden.

    Args:
        parent: The parent Tk widget or window.
        file (str): The path to an animated ``.gif``. The last frame should be empty/transparent.
        frames (int): The number of frames in the ``.gif``.
    """
    def __init__(self, parent, file, frames):
        Label.__init__(self, parent)
        self.parent = parent
        self._frames = [PhotoImage(file=file, format='gif -index %i' % i) for i in range(frames)]
        self.config(image=self._frames[-1])
        self._current_frame = 0
        self.visible = False
        self._tk_loop = self.parent.after(0, lambda: None)

    def _frame_loop(self):
        if self.visible:
            self.config(image=self._frames[self._current_frame])
            self._current_frame += 1
            self._current_frame %= len(self._frames)-1
            self._tk_loop = self.parent.after(50, self._frame_loop)

    def show(self):
        if not self.visible:
            self.visible = True
            self._current_frame = 0
            self._frame_loop()

    def hide(self):
        self.visible = False
        self.config(image=self._frames[-1])
        self.parent.after_cancel(self._tk_loop)


class SoarUI(Tk):
    """ The main GUI window.

    Args:
        client_msg: The function to call to send a message to the client.
        client_mainloop: The client's mainloop function, restarted after the main thread switches to Tk execution.
        parent (optional): The parent window. It is almost always unnecessary to change this from the default.
        title (str, optional): The main window title.
    """
    image_dir = os.path.dirname(__file__)
    world_dir = os.path.join(image_dir, '../worlds/')
    brain_dir = os.path.join(image_dir, '../brains/')

    def __init__(self, client_msg, client_mainloop, parent=None, title='SoaR v0.11.0'):
        Tk.__init__(self, parent)
        self.brain_path = None
        self.world_path = None
        self.title(title)
        self.client_msg = client_msg
        self.client_mainloop = client_mainloop
        self.play_image = PhotoImage(file=os.path.join(self.image_dir, 'play.gif'))
        self.pause_image = PhotoImage(file=os.path.join(self.image_dir, 'pause.gif'))
        self.step_image = PhotoImage(file=os.path.join(self.image_dir, 'step.gif'))
        self.stop_image = PhotoImage(file=os.path.join(self.image_dir, 'stop.gif'))
        self.reload_image = PhotoImage(file=os.path.join(self.image_dir, 'reload.gif'))
        self.brain_image = PhotoImage(file=os.path.join(self.image_dir, 'brain.gif'))
        self.world_image = PhotoImage(file=os.path.join(self.image_dir, 'world.gif'))
        self.sim_image = PhotoImage(file=os.path.join(self.image_dir, 'sim.gif'))
        self.real_image = PhotoImage(file=os.path.join(self.image_dir, 'real.gif'))
        self.close_image = PhotoImage(file=os.path.join(self.image_dir, 'close.gif'))
        self.play = ButtonFrame(self)
        self.step = ButtonFrame(self)
        self.step_counter = IntegerEntry(self.step, '1', width=4, justify=RIGHT)
        self.stop = ButtonFrame(self)
        self.reload = ButtonFrame(self)
        self.loading_icon = LoadingIcon(self, os.path.join(self.image_dir, 'loading.gif'), 9)
        self.brain_but = ButtonFrame(self)
        self.world_but = ButtonFrame(self)
        self.sim_but = ButtonFrame(self)
        self.real = ButtonFrame(self)
        self.close_but = Button(self)
        self.output = OutputFrame(self)
        self.initialize()
        self.windows = []
        self.sim_canvas = None
        self.connected = False
        self.button_list = [self.play, self.step, self.stop, self.reload, self.brain_but, self.world_but, self.sim_but,
                            self.real, self.close_but]
        self.button_state_frames = []
        self.protocol('WM_DELETE_WINDOW', self.on_close)
        self.file_opt = {
            'defaultextension': '.py',
            'filetypes': [('all files', '.*'), ('python files', ' .py')],
            'parent': parent,
            'title': "Choose file",
        }
        self.draw_queue = Queue()

    def initialize(self):
        """ Initialize the grid geometry. """
        self.grid()
        self.reset(clear_output=False)
        self.play.grid(column=0, row=0, pady=10, sticky='NW')
        self.step.grid(column=1, row=0, pady=10, sticky='NW')
        self.step_counter.grid(column=0, row=2)
        self.stop.grid(column=2, row=0, pady=10, sticky='NW')
        self.reload.grid(column=3, row=0, pady=10, sticky='NW')
        self.loading_icon.grid(column=4, row=0, pady=10, ipady=2, sticky='NW')
        self.brain_but.grid(column=5, row=0, padx=5, pady=10, sticky='N')
        self.world_but.grid(column=6, row=0, padx=5, pady=10, sticky='N')
        self.sim_but.grid(column=7, row=0, pady=10, sticky='NE')
        self.real.grid(column=8, row=0, pady=10, sticky='NE')
        self.close_but.grid(column=5, row=1, pady=5, columnspan=2, sticky='N')
        self.output.grid(column=0, row=2, columnspan=9, sticky='NSEW')
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(4, weight=1)
        self.grid_columnconfigure(7, weight=1)

    def report_callback_exception(self, exc, val, traceback):
        """ Report callback exception to sys.stderr, as well as notifying the Soar client. """
        Tk.report_callback_exception(self, exc, val, traceback)
        self.client_msg(GUI_ERROR)  # TODO: Tk errors may be more severe than GUIErrors

    def reset(self, clear_output=True):
        """ Reset all of the button states to what they are at initialization, before any files are loaded.

        Args:
            clear_output (bool, optional): If ``True``, clear the contents of the output frame.
        """
        self.play.config(image=self.play_image, text='Play', command=self.play_cmd, state=DISABLED)
        self.step.config(image=self.step_image, text='Step', command=self.step_cmd, state=DISABLED)
        self.stop.config(image=self.stop_image, text='Stop', command=self.stop_cmd, state=DISABLED)
        self.reload.config(image=self.reload_image, text='Reload', command=self.reload_cmd, state=DISABLED)
        self.brain_but.config(image=self.brain_image, text='Load Brain', command=self.brain_cmd, state=NORMAL)
        self.world_but.config(image=self.world_image, text='Load World', command=self.world_cmd, state=NORMAL)
        self.sim_but.config(image=self.sim_image, text='Simulator', command=self.sim_cmd, state=DISABLED)
        self.real.config(image=self.real_image, text='Real robot', command=self.real_cmd, state=DISABLED)
        self.close_but.config(text='Close all windows', command=lambda: self.reload_cmd(False, True))
        if clear_output:
            self.output.clear()

    def mainloop(self, n=0):
        """ Enter the Tk event loop, and restart the client as a new thread.

        Redirect stdout and stderr to the GUI's output frame.
        """
        _stdout = sys.stdout
        _stderr = sys.stderr
        sys.stdout = SoarIO(self.output.output)
        sys.stderr = SoarIO(self.output.error)
        t = Thread(target=self.client_mainloop, daemon=True)
        t.start()
        self.after(0, self.tick)
        Tk.mainloop(self, n)
        sys.stdout.close()
        sys.stderr.close()
        sys.stdout = _stdout
        sys.stderr = _stderr

    def toplevel(self, linked=True):
        """ Add a new window to the UI's internal list, and return a new Toplevel window, optionally linked.

        Args:
            linked (bool): If ``True``, the window will be destroyed whenever the simulator window is destroyed.

        Returns:
            The new Toplevel window.
        """
        t = Toplevel()
        self.windows.append((t, linked))
        return t

    def close_windows(self, close_unlinked=False):
        """ Close windows, optionally unlinked ones, clear the draw queue, and set the simulator canvas to ``None``.

        Args:
            close_unlinked (bool): If ``True``, closes all windows. Otherwise, closes only the linked ones.
        """
        while not self.draw_queue.empty():
            _ = self.draw_queue.get()
            self.draw_queue.task_done()
        for tup in reversed(self.windows):
            window, linked = tup
            if linked or close_unlinked:
                self.windows.remove(tup)
                try:
                    window.destroy()
                except Exception:  # Probably already destroyed?
                    pass
        self.sim_canvas = None

    def message(self, msg, *data):
        """ Sends a message to the GUI's tick loop. """
        self.draw_queue.put((msg, data))

    def tick(self):
        """ Called 100 times per second to update the canvas. """
        while not self.draw_queue.empty():
            msg, data = self.draw_queue.get()
            if msg == CLOSE_LINKED:  # Need to flush the queues and kill linked windows
                self.close_windows()
            elif msg == CLOSE_ALL:
                self.close_windows(close_unlinked=True)
            elif msg == MAKE_WORLD_CANVAS:
                try:
                    world = data[0]
                    self.sim_canvas = canvas_from_world(world, toplevel=self.toplevel,
                                                        close_cmd=lambda: self.reload_cmd(reload_controller=False))
                    world.draw(self.sim_canvas)
                    self.sim_ready()
                except Exception:
                    self.client_msg(GUI_ERROR)
                    tb.print_exc()
            elif msg == DRAW:
                if self.sim_canvas is not None:  # Don't draw objects if there isn't a canvas
                    try:
                        data[0].delete(self.sim_canvas)
                        data[0].draw(self.sim_canvas)
                    except Exception:
                        self.client_msg(GUI_ERROR)
                        tb.print_exc()
            self.draw_queue.task_done()
        self.after(10, self.tick)

    def on_close(self):
        """ Called when the main window is closed. """
        self.destroy()

    def wait_for(self, condition, func):
        """ Execute a function in the main Tk thread when some condition evaluates to true.

        Args:
            func: The function to eventually execute.
            condition: The condition function. Should return a boolean.
        """
        if condition():
            func()
        else:
            self.after(10, lambda: self.wait_for(condition, func))

    def play_cmd(self):
        """ Called when the play button is pushed. """
        self.loading()
        self.client_msg(START_CONTROLLER, callback=self.play_ready)

    def play_ready(self):
        """ Called after the controller has started playing. """
        self.done_loading()
        if self.connected:  # Pausing is not supported while connected to a real robot
            self.play.config(state=DISABLED)
        else:
            self.play.config(image=self.pause_image, text='Pause', command=self.pause_cmd)
            self.step.config(state=DISABLED)
        self.stop.config(state=NORMAL)

    def pause_cmd(self):
        """ Called when the pause button is pushed. """
        self.loading()
        self.client_msg(PAUSE_CONTROLLER, callback=self.pause_ready)

    def pause_ready(self):
        """ Called when the controller has finished pausing. """
        self.done_loading()
        self.play.config(image=self.play_image, text='Play', command=self.play_cmd)
        self.step.config(state=NORMAL)

    def step_cmd(self):
        """ Called when the step button is pushed. """
        try:
            n_steps = int(self.step_counter.get())
        except ValueError:
            self.step_counter.delete(0, END)
            self.step_counter.insert(0, '1')
            n_steps = 1
        if n_steps == 0:
            self.step_counter.delete(0, END)
            self.step_counter.insert(0, '1')
            n_steps = 1
        self.play.config(image=self.pause_image, text='Pause', command=self.pause_cmd)
        self.step.config(state=DISABLED)
        self.stop.config(state=NORMAL)
        self.client_msg(STEP_CONTROLLER, n_steps)

    def step_finished(self):
        """ Called when the controller finishes multi-stepping. """
        self.play.config(image=self.play_image, text='Play', command=self.play_cmd)
        self.step.config(state=NORMAL)

    def stop_cmd(self):
        """ Called when the stop button is pushed. """
        self.loading()
        self.client_msg(STOP_CONTROLLER, callback=self.stop_ready)

    def stop_ready(self):
        """ Called when the controller has stopped. """
        self.done_loading()
        self.play.config(image=self.play_image, text='Play', command=self.play_cmd, state=DISABLED)
        self.step.config(state=DISABLED)
        self.stop.config(state=DISABLED)

    def reload_cmd(self, reload_controller=True, clear_output=True, silent=False, close_unlinked=False, callback=None):
        """ Kill the controller, close windows, and reload the brain and world.

        Args:
            reload_controller (bool): If ``True``, immediately reload whatever controller was in effect previously.
            close_unlinked (bool): If ``True``, close all windows, not just the linked ones.
            clear_output (bool): If ``True``, clears the output of the output frame.
            silent (bool): If ``True``, stops the client from printing 'LOAD BRAIN'-like messages.
            callback: The function to call after the reload has finished, or ``None``.
        """
        sim_canvas, connected = self.sim_canvas, self.connected
        self.reset(clear_output=clear_output)
        self.loading()
        self.client_msg(SHUTDOWN_CONTROLLER)
        if close_unlinked:
            self.message(CLOSE_ALL)
        else:
            self.message(CLOSE_LINKED)
        if self.brain_path:
            self.client_msg(LOAD_BRAIN, self.brain_path, silent=silent)
        if self.world_path:
            self.client_msg(LOAD_WORLD, self.world_path, silent=silent),
        self.client_msg(NOP, callback=lambda: self.reload_finished(reload_controller, sim_canvas, connected, callback))

    def reload_finished(self, reload_controller, sim_canvas, connected, callback):
        """ Called after the client has finished reloading.

        Args:
            reload_controller (bool): reload_controller (bool): If ``True``, reload the previous controller.
            sim_canvas: If not ``None``, the controller to be reloaded is the simulator.
            connected: If ``True``, the controller to be reloaded is the real robot controller.
            callback: A function to call once the reload has finished, or ``None``.
        """
        if self.brain_path:
            self.brain_ready()
        if self.world_path:
            self.world_ready()
        self.done_loading()
        if reload_controller:  # If previously we were simulating or connected, reload those
            if sim_canvas:
                self.wait_for(self.draw_queue.empty, self.sim_load)
            elif connected:
                self.wait_for(self.draw_queue.empty, self.real_load)
        if callback:
            callback()

    def brain_cmd(self):
        """ Called when the brain button is pushed. """
        new_brain = filedialog.askopenfilename(initialdir=self.brain_dir, **self.file_opt)
        if new_brain:
            # If a brain and world were already loaded, reload
            if self.brain_path is not None and self.world_path is not None:
                self.brain_path = new_brain
                self.reload_cmd()
            else:
                self.brain_path = new_brain
                self.loading()
                self.client_msg(LOAD_BRAIN, new_brain, callback=self.brain_ready)

    def brain_ready(self,):
        """ Configure buttons and paths when a brain is loaded. """
        self.done_loading()
        self.brain_dir = os.path.dirname(self.brain_path)
        self.real.config(state=NORMAL)
        if self.world_path is not None:
            self.sim_but.config(state=NORMAL)

    def world_cmd(self):
        """ Called when the world button is pushed. """
        new_world = filedialog.askopenfilename(initialdir=self.world_dir, **self.file_opt)
        if new_world:
            if self.brain_path is not None and self.world_path is not None:
                self.world_path = new_world
                self.reload_cmd()
            else:
                self.world_path = new_world
                self.loading()
                self.client_msg(LOAD_WORLD, new_world, callback=self.world_ready)

    def world_ready(self):
        """ Configure buttons and paths when a world is ready. """
        self.done_loading()
        self.world_dir = os.path.dirname(self.world_path)
        if self.brain_path is not None:
            self.sim_but.config(state=NORMAL)

    def sim_cmd(self):
        """ Called when the simulator button is pushed. """
        if self.sim_canvas or self.connected:  # If a controller is already running, we need to reload
            self.reload_cmd(reload_controller=False, callback=self.sim_load)
        else:
            self.sim_load()

    def sim_load(self):
        """ Called when the simulator's reload has finished. """
        self.loading()
        # Need to wait for the draw queue to be empty twice: Once before the simulator is made, again after while the
        # world is being drawn.
        self.wait_for(self.draw_queue.empty,
                      lambda: self.client_msg(MAKE_CONTROLLER, simulated=True,
                                              callback=self.wait_for(self.draw_queue.empty, self.sim_ready)))

    def sim_ready(self):
        """ Called when the simulator is ready. """
        self.done_loading()
        self.connected = False
        self.play.config(image=self.play_image, state=NORMAL)
        self.step.config(state=NORMAL)
        self.stop.config(state=DISABLED)
        self.reload.config(state=NORMAL)
        self.brain_but.config(state=NORMAL)
        self.world_but.config(state=NORMAL)
        self.sim_but.config(state=NORMAL)
        self.real.config(state=NORMAL)
        self.close_but.config(state=NORMAL)

    def real_cmd(self):
        """ Called when the real robot button is pushed. """
        if self.sim_canvas or self.connected:  # If a controller is already running, we need to reload
            self.reload_cmd(reload_controller=False, callback=self.real_load)
        else:
            self.real_load()

    def real_load(self):
        """ Called when the real robot's requested reload has finished. """
        self.loading()
        self.wait_for(self.draw_queue.empty,
                      lambda: self.client_msg(MAKE_CONTROLLER, simulated=False, callback=self.real_ready))

    def real_ready(self):
        """ Called when the real robot is ready. """
        self.done_loading()
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
        self.close_but.config(state=NORMAL)

    def gui_error(self):
        """ Called when a GUI error occurs, such as an error while drawing a world or window. """
        self.cancel_all_loading()
        self.reset(clear_output=False)
        self.reload.config(state=NORMAL, command=lambda: self.reload_cmd(reload_controller=False))
        if self.sim_canvas:
            t = self.sim_canvas.master.master
            t.protocol('WM_DELETE_WINDOW', lambda: self.message(CLOSE_LINKED))

    def controller_io_error(self):
        """ Called when an error occurs connecting to the real robot. """
        self.cancel_all_loading()
        self.after(0, lambda: self.reload_cmd(clear_output=False, silent=True, reload_controller=False))

    def controller_failure(self):
        """ Called by the client when the controller fails. """
        self.cancel_all_loading()
        self.reset(clear_output=False)
        self.reload.config(state=NORMAL)

    def loading(self):
        """ Disable user interaction and animate the loading icon. """
        button_states = []
        for button in self.button_list:
            if button['state'] == 'disabled':
                button_states.append(DISABLED)
            else:
                button_states.append(NORMAL)
        self.button_state_frames.append(button_states)
        self.play.config(state=DISABLED)
        self.step.config(state=DISABLED)
        self.stop.config(state=DISABLED)
        self.reload.config(state=DISABLED)
        self.brain_but.config(state=DISABLED)
        self.world_but.config(state=DISABLED)
        self.sim_but.config(state=DISABLED)
        self.real.config(state=DISABLED)
        self.close_but.config(state=DISABLED)
        if not self.loading_icon.visible:
            self.loading_icon.show()

    def done_loading(self):
        """ Re-enable user interaction, and hide the loading icon. """
        if len(self.button_state_frames) > 0:
            button_states = self.button_state_frames.pop()
            for i, button in enumerate(self.button_list):
                button.config(state=button_states[i])
        if len(self.button_state_frames) == 0 and self.loading_icon.visible:
            self.loading_icon.hide()

    def cancel_all_loading(self):
        """ Hide the loading icon and delete all button state frames. """
        self.button_state_frames = []
        self.loading_icon.hide()
