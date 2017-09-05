# Soar (Snakes on a Robot): A Python robotics framework.
# Copyright (C) 2017 Andrew Antonitis. Licensed under the LGPLv3.
#
# soar/gui/output.py
""" Soar output classes.

Tk widgets allowing the capture and display of text output in the GUI.
"""
import webbrowser
from io import StringIO

from tkinter import *


class SoarIO(StringIO):
    def __init__(self, write_func):
        StringIO.__init__(self)
        self.write_func = write_func

    def write(self, s):
        self.write_func(s)


_link_id = 0


def _new_link_id():
    global _link_id
    return 'link' + str(_link_id)
    _link_id += 1


class OutputFrame(Frame):
    """ A read-only Tk output frame that can display normal and error output.

    Args:
        master: The parent widget or window.
        initial_text (str, optional): The text to have initially in the output frame.
    """
    def __init__(self, master, initial_text=''):
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
        if initial_text != '':
            self.output(initial_text)

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

    def link(self, text):
        """ Insert a clickable link at the end of the text field.

        Args:
            text (str): The link text to insert.
        """
        tag = _new_link_id()
        self.text_field.tag_config(tag, foreground='blue', underline=1)
        self.text_field.tag_bind(tag, '<Button-1>', lambda event: webbrowser.open_new(text))
        self.text_field.tag_bind(tag, '<Enter>', lambda event: self.text_field.config(cursor='hand1'))
        self.text_field.tag_bind(tag, '<Leave>', lambda event: self.text_field.config(cursor=''))
        self.insert(text, tag)

    def clear(self):
        """ Clear the entire text field. """
        self.text_field.config(state=NORMAL)
        self.text_field.delete(1.0, END)
        self.text_field.config(state=DISABLED)
