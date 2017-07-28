""" Soar output classes.

Tk widgets allowing the capture and display of text output in the GUI.

TODO: Make output capturing more elegant.
"""
from io import StringIO

from tkinter import *


class SoarIO(StringIO):
    def __init__(self, write_func):
        StringIO.__init__(self)
        self.write_func = write_func

    def write(self, s):
        self.write_func(s)


class OutputRedirect:  # TODO: Class may no longer be necessary
    def __init__(self, frame):
        self.frame = frame

    def __enter__(self):
        self._stdout = sys.stdout
        self._stderr = sys.stderr
        sys.stdout = SoarIO(self.frame.output)
        sys.stderr = SoarIO(self.frame.error)
        return self

    def __exit__(self):
        sys.stdout.close()
        sys.stderr.close()
        sys.stdout = self._stdout
        sys.stderr = self._stderr


class OutputFrame(Frame):
    """ A read-only Tk output frame that can display normal and error output.

    Args:
        master: The parent widget or window.
    """
    def __init__(self, master):
        Frame.__init__(self, master, bg='white')
        self.scroll = Scrollbar(self)
        self.scroll.pack(side=RIGHT, fill=Y)
        self.text_field = Text(self, fg='black', bg='white', wrap=WORD, yscrollcommand=self.scroll.set)
        self.text_field.config(height=16, padx=5, pady=5, state=DISABLED)
        self.text_field.tag_config('output', foreground='black')
        self.text_field.tag_config('error', foreground='red')
        self.text_field.bind("<1>", lambda event: self.text_field.focus_set())
        self.text_field.pack(expand=True, fill='both')
        self.scroll.config(command=self.text_field.yview)
        self.output('SoaR v1.0.0.dev0: Snakes on a robot: Output will appear in this window\n\n')

    def insert(self, text, *tags):
        """ Insert text at the end of the text field.

        Args:
            text (str): The text to insert.
            *tags: Variable length `str` list of tags to attach to the text. The `'output'` tag signifies normal output,
                   and the `'error'` tag signifies that the text will be red.
        """
        self.text_field.config(state=NORMAL)
        self.text_field.insert(END, text, *tags)
        self.text_field.see("%s-2c" % END)  # Ensure the inserted text is visible
        self.text_field.config(state=DISABLED)

    def output(self, text):
        """ Insert normal output text at the end of the text field.

        Args:
            text (str): The text to insert.
        """
        self.insert(text, 'output')

    def error(self, text):
        """ Insert error output text at the end of the text field.

        Args:
             text (str): The text to insert.
        """
        self.insert(text, 'error')

    def clear(self):
        """ Clear the entire text field. """
        self.text_field.config(state=NORMAL)
        self.text_field.delete(1.0, END)
        self.text_field.config(state=DISABLED)
