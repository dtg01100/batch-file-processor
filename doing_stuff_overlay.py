from Tkinter import *
from ttk import *

class doing_stuff_overlay():


    def __init__(self, parent):
        self.parent = parent


def make_overlay(parent, overlaytext):
    print("making overlay")
    global doing_stuff_frame
    global doing_stuff
    global labelvar
    labelvar = StringVar()
    labelvar.set(overlaytext)
    doing_stuff_frame = Frame(parent, relief=RIDGE)
    doing_stuff_frame.grab_set()
    doing_stuff = Label(doing_stuff_frame, text=labelvar.get())
    doing_stuff.place(relx=.5, rely=.5, anchor=CENTER)
    doing_stuff_frame.place(relx=.5, rely=.5, relheight=.40, relwidth=1, anchor=CENTER)
    parent.update()

def destroy_overlay():
    print("destroying overlay")
    doing_stuff_frame.destroy()
