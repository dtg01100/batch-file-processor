from Tkinter import *
from ttk import *


class DoingStuffOverlay:

    def __init__(self, parent):
        self.parent = parent


def make_overlay(parent, overlay_text, header="", footer=""):
    global doing_stuff_frame
    global doing_stuff
    global label_var
    global header_var
    global header_label
    global footer_var
    global footer_label
    label_var = StringVar()
    label_var.set(overlay_text)
    header_var = StringVar()
    header_var.set(header)
    footer_var = StringVar()
    footer_var.set(footer)
    doing_stuff_frame = Frame(parent, relief=RIDGE)
    doing_stuff_frame.grab_set()
    doing_stuff = Label(doing_stuff_frame, text=label_var.get())
    doing_stuff.place(relx=.5, rely=.5, anchor=CENTER)
    header_label = Label(doing_stuff_frame, text=header_var.get())
    header_label.place(relx=.05, rely=.15, anchor=W)
    footer_label = Label(doing_stuff_frame, text=footer_var.get())
    footer_label.place(relx=.05, rely=.85, anchor=W)
    doing_stuff_frame.place(relx=.5, rely=.5, height=120, relwidth=1, anchor=CENTER)
    parent.update()


def update_overlay(parent, overlay_text, header="", footer=""):
    doing_stuff.configure(text=overlay_text)
    header_label.configure(text=header)
    footer_label.configure(text=footer)
    parent.update()


def destroy_overlay():
    doing_stuff_frame.destroy()
