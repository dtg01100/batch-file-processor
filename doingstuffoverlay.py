import tkinter
import tkinter.ttk

# Initialize global variables at module level
doing_stuff_frame = None
doing_stuff = None
label_var = None
header_var = None
header_label = None
footer_var = None
footer_label = None


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
    # Destroy existing overlay if present to prevent memory leaks
    if doing_stuff_frame is not None:
        try:
            doing_stuff_frame.grab_release()
        except tkinter.TclError:
            pass  # Widget may already be destroyed
        doing_stuff_frame.destroy()
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
    if doing_stuff is None or doing_stuff_frame is None:
        return
    doing_stuff.configure(text=overlay_text)
    header_label.configure(text=header)
    footer_label.configure(text=footer)
    if overlay_height is not None and overlay_height != doing_stuff_frame.winfo_height():
        doing_stuff_frame.place(height=overlay_height)
    parent.update()


def destroy_overlay():
    global doing_stuff_frame
    if doing_stuff_frame is not None:
        try:
            doing_stuff_frame.grab_release()
        except tkinter.TclError:
            pass  # Widget may already be destroyed
        doing_stuff_frame.destroy()
        doing_stuff_frame = None
