from Tkinter import *
from ttk import *


class DoingStuffOverlay:

    def __init__(self, parent):
        self.parent = parent


def make_overlay(parent, overlay_text, message=""):
    global doing_stuff_frame
    global doing_stuff
    global label_var
    global message_var
    global message_label
    label_var = StringVar()
    label_var.set(overlay_text)
    message_var = StringVar()
    message_var.set(message)
    doing_stuff_frame = Frame(parent, relief=RIDGE)
    doing_stuff_frame.grab_set()
    doing_stuff = Label(doing_stuff_frame, text=label_var.get())
    doing_stuff.place(relx=.5, rely=.5, anchor=CENTER)
    message_label = Label(doing_stuff_frame, text=message_var.get())
    message_label.place(relx=.05, rely=.85, anchor=W)
    doing_stuff_frame.place(relx=.5, rely=.5, height=100, relwidth=1, anchor=CENTER)
    parent.update()


def update_overlay(parent, overlay_text, message=""):
    doing_stuff.configure(text=overlay_text)
    message_label.configure(text=message)
    parent.update()


def destroy_overlay():
    doing_stuff_frame.destroy()
