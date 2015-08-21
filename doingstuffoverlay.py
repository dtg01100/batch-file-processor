from Tkinter import *
from ttk import *


class DoingStuffOverlay:

    def __init__(self, parent):
        self.parent = parent


def make_overlay(parent, overlay_text):
    global doing_stuff_frame
    global doing_stuff
    global label_var
    label_var = StringVar()
    label_var.set(overlay_text)
    doing_stuff_frame = Frame(parent, relief=RIDGE)
    doing_stuff_frame.grab_set()
    doing_stuff = Label(doing_stuff_frame, text=label_var.get())
    doing_stuff.place(relx=.5, rely=.5, anchor=CENTER)
    doing_stuff_frame.place(relx=.5, rely=.5, height=100, relwidth=1, anchor=CENTER)
    parent.update()


def destroy_overlay():
    doing_stuff_frame.destroy()
