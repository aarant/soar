from tkinter import *

class OutputField(Frame):
    def __init__(self, master):
        Frame.__init__(self, master, bg='white')
        self.scroll = Scrollbar(self)
        self.scroll.pack(side=RIGHT, fill=Y)
        self.text_field = Text(self, fg='black', bg='white', wrap=CHAR, yscrollcommand=self.scroll.set)
        self.text_field.config(height=16, padx=5, pady=5, state=DISABLED)
        self.text_field.pack()
        self.scroll.config(command=self.text_field.yview)

    def insert(self, text):
        self.text_field.config(state=NORMAL)
        self.text_field.insert(END, '> ' + str(text) + '\n')
        self.text_field.see(END)
        self.text_field.config(state=DISABLED)

    def clear(self):
        self.text_field.config(state=NORMAL)
        self.text_field.delete(1.0, END)
        self.text_field.config(state=DISABLED)
