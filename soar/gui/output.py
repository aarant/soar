import sys
from io import StringIO

from tkinter import *


class SoarIO(StringIO):
    def __init__(self, write_func):
        StringIO.__init__(self)
        self.write_func = write_func

    def write(self, s):
        self.write_func(s)


class OutputRedirect:
    def __init__(self, frame):
        self.frame = frame

    def __enter__(self):
        self._stdout = sys.stdout
        self._stderr = sys.stderr
        sys.stdout = SoarIO(self.frame.output)
        sys.stderr = SoarIO(self.frame.error)
        return self

    def __exit__(self):
        self._stdout.write('whut')
        sys.stdout.close()
        sys.stderr.close()
        sys.stdout = self._stdout
        sys.stderr = self._stderr


class OutputFrame(Frame):
    def __init__(self, master):
        Frame.__init__(self, master, bg='white')
        self.scroll = Scrollbar(self)
        self.scroll.pack(side=RIGHT, fill=Y)
        self.text_field = Text(self, fg='black', bg='white', wrap=WORD, yscrollcommand=self.scroll.set)
        self.text_field.config(height=16, padx=5, pady=5, state=DISABLED)
        self.text_field.tag_config('output', background='white', foreground='black')
        self.text_field.tag_config('error', background='white', foreground='red')
        self.text_field.pack()
        self.scroll.config(command=self.text_field.yview)
        self.output('SoaR v0.8.0: Snakes on a robot: An extensible Python framework for simulating and '
                    'interacting with robots\n\nOutput will appear in this window\n')

    def insert(self, text, *tags):
        self.text_field.config(state=NORMAL)
        self.text_field.insert(END, text, *tags)
        self.text_field.see(END)  # Ensure the inserted text is visible
        self.text_field.config(state=DISABLED)

    def output(self, text):
        self.insert(text, 'output')

    def error(self, text):
        self.insert(text, 'error')

    def clear(self):
        self.text_field.config(state=NORMAL)
        self.text_field.delete(1.0, END)
        self.text_field.config(state=DISABLED)
