import tkinter
import tkinter.ttk


class DoingStuffOverlay:
    def __init__(self, parent):
        self.parent = parent


def make_overlay(parent, overlay_text, header="", footer="", overlay_height=100):
    global doing_stuff_frame
    global doing_stuff
    global label_var
    global header_var
    global header_label
    global footer_var
    global footer_label
    label_var = tkinter.StringVar()
    label_var.set(overlay_text)
    header_var = tkinter.StringVar()
    header_var.set(header)
    footer_var = tkinter.StringVar()
    footer_var.set(footer)
    doing_stuff_frame = tkinter.ttk.Frame(parent, relief=tkinter.RIDGE)
    doing_stuff_frame.grab_set()
    doing_stuff = tkinter.ttk.Label(doing_stuff_frame, text=label_var.get())
    doing_stuff.place(relx=.5, rely=.5, anchor=tkinter.CENTER)
    header_label = tkinter.ttk.Label(doing_stuff_frame, text=header_var.get())
    header_label.place(relx=.05, rely=.15, anchor=tkinter.W)
    footer_label = tkinter.ttk.Label(doing_stuff_frame, text=footer_var.get())
    footer_label.place(relx=.05, rely=.85, anchor=tkinter.W)
    doing_stuff_frame.place(relx=.5, rely=.5, height=overlay_height, relwidth=1, anchor=tkinter.CENTER)
    parent.update()


def update_overlay(parent, overlay_text, header="", footer="", overlay_height=None):
    doing_stuff.configure(text=overlay_text)
    header_label.configure(text=header)
    footer_label.configure(text=footer)
    if overlay_height is not None and overlay_height != doing_stuff_frame.winfo_height():
        doing_stuff_frame.place(height=overlay_height)
    parent.update()


def destroy_overlay():
    doing_stuff_frame.destroy()
