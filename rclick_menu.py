#  this module was from the following address
#  https://paperrobot.wordpress.com/2008/12/24/python-right-click-edit-menu-widget/

import tkinter
 
class RightClickMenu(object):
    """
    Simple widget to add basic right click menus to entry widgets.
 
    usage:
 
    rclickmenu = RightClickMenu(some_entry_widget)
    some_entry_widget.bind("<3>", rclickmenu)
 
    If you prefer to import Tkinter over Tkinter, just replace all Tkinter
    references with Tkinter and this will still work fine.
    """
    def __init__(self, parent):
        self.parent = parent
        # bind Control-A to select_all() to the widget.  All other
        # accelerators seem to work fine without binding such as
        # Ctrl-V, Ctrl-X, Ctrl-C etc.  Ctrl-A was the only one I had
        # issue with.
        self.parent.bind("<Control-a>", lambda e: self.select_all(), add='+')
        self.parent.bind("<Control-A>", lambda e: self.select_all(), add='+')
    def __call__(self, event):
        # if the entry widget is disabled do nothing.
        if self.parent.cget('state') == tkinter.DISABLED:
            return
        # grab focus of the entry widget.  this way you can see
        # the cursor and any marking selections
        self.parent.focus_force()
        self.build_menu(event)
    def build_menu(self, event):
        menu = tkinter.Menu(self.parent, tearoff=0)
        # check to see if there is any marked text in the entry widget.
        # if not then Cut and Copy are disabled.
        if not self.parent.selection_present():
            menu.add_command(label="Cut", state=tkinter.DISABLED)
            menu.add_command(label="Copy", state=tkinter.DISABLED)
        else:
            # use Tkinter's virtual events for brevity.  These could
            # be hardcoded with our own functions to immitate the same
            # actions but there's no point except as a novice exercise
            # (which I recommend if you're a novice).
            menu.add_command(
                label="Cut",
                command=lambda: self.parent.event_generate("<<Cut>>"))
            menu.add_command(
                label="Copy",
                command=lambda: self.parent.event_generate("<<Copy>>"))
        # if there's string data in the clipboard then make the normal
        # Paste command.  otherwise disable it.
        if self.paste_string_state():
            menu.add_command(
                label="Paste",
                command=lambda: self.parent.event_generate("<<Paste>>"))
        else:
            menu.add_command(label="Paste", state=tkinter.DISABLED)
        # again, if there's no marked text then the Delete option is disabled.
        if not self.parent.selection_present():
            menu.add_command(label="Delete", state=tkinter.DISABLED)
        else:
            menu.add_command(
                label="Delete",
                command=lambda: self.parent.event_generate("<<Clear>>"))
        # make things pretty with a horizontal separator
        menu.add_separator()
        # I don't know of if there's a virtual event for select all though
        # I did look in vain for documentation on -any- of Tkinter's
        # virtual events.  Regardless, the method itself is trivial.
        menu.add_command(label="Select All", command=self.select_all)
        menu.post(event.x_root, event.y_root)
    def select_all(self):
        self.parent.selection_range(0, tkinter.END)
        self.parent.icursor(tkinter.END)
        # return 'break' because, for some reason, Control-a (little 'a')
        # doesn't work otherwise.  There's some natural binding that
        # Tkinter entry widgets want to do that send the cursor to Home
        # and deselects.
        return 'break'
    def paste_string_state(self):
        """Returns true if a string is in the clipboard"""
        try:
            # this assignment will raise an exception if the data
            # in the clipboard isn't a string (such as a picture).
            # in which case we want to know about it so that the Paste
            # option can be appropriately set normal or disabled.
            clipboard = self.parent.selection_get(selection='CLIPBOARD')
        except tkinter.TclError:
            return False
        return True
 
if __name__ == '__main__':
    root = tkinter.Tk()
    root.geometry("156x65")
    tkinter.Label(root, text="Right mouse click in\nthe entry widget below:").pack()
    entry_w = tkinter.Entry(root)
    entry_w.pack()
    rclick = RightClickMenu(entry_w)
    entry_w.bind("<3>", rclick)
    root.mainloop()