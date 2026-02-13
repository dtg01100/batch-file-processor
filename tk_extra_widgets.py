import platform
import tkinter
import tkinter.ttk


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


# http://tkinter.unpythonic.net/wiki/VerticalScrolledFrame

class VerticalScrolledFrame(tkinter.ttk.Frame):
    """A pure Tkinter scrollable frame that actually works!
    * Use the 'interior' attribute to place widgets inside the scrollable frame
    * Construct and pack/place/grid normally
    * This frame only allows vertical scrolling

    """

    def __init__(self, parent, *args, **kw):
        tkinter.Frame.__init__(self, parent, *args, **kw)

        # create a canvas object and a vertical scrollbar for scrolling it
        vscrollbar = tkinter.ttk.Scrollbar(self, orient=tkinter.VERTICAL)
        vscrollbar.pack(fill=tkinter.Y, side=tkinter.RIGHT, expand=tkinter.FALSE)
        canvas = tkinter.Canvas(self, bd=0, highlightthickness=0,
                        yscrollcommand=vscrollbar.set)
        canvas.pack(side=tkinter.LEFT, fill=tkinter.BOTH, expand=tkinter.TRUE)
        vscrollbar.config(command=canvas.yview)

        # reset the view
        canvas.xview_moveto(0)
        canvas.yview_moveto(0)

        # create a frame inside the canvas which will be scrolled with it
        self.interior = interior = tkinter.ttk.Frame(canvas)
        interior_id = canvas.create_window(0, 0, window=interior,
                                           anchor=tkinter.NW)

        # track changes to the canvas and frame width and sync them,
        # also updating the scrollbar
        def _configure_interior(event):
            # configure scrollwheel on changes
            _configure_scrollwheel()
            # update the scrollbars to match the size of the inner frame
            size = (interior.winfo_reqwidth(), interior.winfo_reqheight())
            canvas.config(scrollregion="0 0 %s %s" % size)
            if interior.winfo_reqwidth() != canvas.winfo_width():
                # update the canvas's width to fit the inner frame
                canvas.config(width=interior.winfo_reqwidth())

        interior.bind('<Configure>', _configure_interior)

        def _configure_canvas(event):
            if interior.winfo_reqwidth() != canvas.winfo_width():
                # update the inner frame's width to fill the canvas
                canvas.itemconfigure(interior_id, width=canvas.winfo_width())

        canvas.bind('<Configure>', _configure_canvas)

        OS = platform.system()

        def _configure_scrollwheel():
            # giant try except block. this attempts to unbind scroll events,
            #  to keep from binding scroll events every time this is called.
            try:
                self.interior.unbind('<Enter>')
            except Exception:
                pass
            try:
                self.interior.unbind('<Leave>')
            except Exception:
                pass
            try:
                vscrollbar.unbind('<Enter>')
            except Exception:
                pass
            try:
                vscrollbar.unbind('<Leave>')
            except Exception:
                pass
            try:
                vscrollbar.unbind_all('<4>')
            except Exception:
                pass
            try:
                vscrollbar.unbind_all('<5>')
            except Exception:
                pass
            try:
                vscrollbar.unbind_all("<MouseWheel>")
            except Exception:
                pass

            if OS != "Windows" and OS != "Linux" and OS != "Darwin":
                pass
            else:
                canvas.configure(yscrollcommand=vscrollbar.set)
                vscrollbar['command'] = canvas.yview

                factor = 2

                activeArea = None

                def onMouseWheel(event):
                    global activeArea
                    if activeArea:
                        activeArea.onMouseWheel(event)

                def build_function_onMouseWheel(widget, orient, factor):
                    view_command = getattr(widget, orient + 'view')

                    if OS == 'Linux':
                        def onMouseWheel(event):
                            if event.num == 4:
                                view_command("scroll", (-1) * factor, "units")
                            elif event.num == 5:
                                view_command("scroll", factor, "units")

                    elif OS == 'Windows':
                        def onMouseWheel(event):
                            view_command("scroll", (-1) * int((event.delta / 120) * factor), "units")

                    elif OS == 'Darwin':
                        def onMouseWheel(event):
                            view_command("scroll", event.delta, "units")

                    return onMouseWheel

                if OS == "Linux":
                    vscrollbar.bind_all('<4>', onMouseWheel, add='+')
                    vscrollbar.bind_all('<5>', onMouseWheel, add='+')
                else:
                    # Windows and MacOS
                    vscrollbar.bind_all("<MouseWheel>", onMouseWheel, add='+')

                def mouseWheel_bind(self, widget):
                    global activeArea
                    activeArea = widget

                def mouseWheel_unbind(self):
                    global activeArea
                    activeArea = None

                if vscrollbar and not hasattr(vscrollbar, 'onMouseWheel'):
                    vscrollbar.onMouseWheel = build_function_onMouseWheel(canvas, 'y', factor)

                self.interior.bind('<Enter>', lambda event, scrollbar=vscrollbar: mouseWheel_bind(event, scrollbar))
                self.interior.bind('<Leave>', lambda event: mouseWheel_unbind(event))
                vscrollbar.bind('<Enter>', lambda event, scrollbar=vscrollbar: mouseWheel_bind(event, scrollbar))
                vscrollbar.bind('<Leave>', lambda event: mouseWheel_unbind(event))

                canvas.onMouseWheel = vscrollbar.onMouseWheel
        _configure_scrollwheel()

class CreateToolTip(object):
    """
    create a tooltip for a given widget
    from https://stackoverflow.com/questions/3221956/how-do-i-display-tooltips-in-tkinter
    """
    def __init__(self, widget, text='widget info'):
        self.waittime = 500     #miliseconds
        self.wraplength = 180   #pixels
        self.widget = widget
        self.text = text
        self.widget.bind("<Enter>", self.enter)
        self.widget.bind("<Leave>", self.leave)
        self.widget.bind("<ButtonPress>", self.leave)
        self.id = None
        self.tw = None

    def enter(self, event=None):
        self.schedule()

    def leave(self, event=None):
        self.unschedule()
        self.hidetip()

    def schedule(self):
        self.unschedule()
        self.id = self.widget.after(self.waittime, self.showtip)

    def unschedule(self):
        id = self.id
        self.id = None
        if id:
            self.widget.after_cancel(id)

    def showtip(self, event=None):
        x = y = 0
        x, y, cx, cy = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 20
        # creates a toplevel window
        self.tw = tkinter.Toplevel(self.widget)
        # Leaves only the label and removes the app window
        self.tw.wm_overrideredirect(True)
        self.tw.wm_geometry("+%d+%d" % (x, y))
        label = tkinter.Label(self.tw, text=self.text, justify='left',
                       background="#ffffff", relief='solid', borderwidth=1,
                       wraplength = self.wraplength)
        label.pack(ipadx=1)

    def hidetip(self):
        tw = self.tw
        self.tw= None
        if tw:
            tw.destroy()


class columnSorterWidget:
    """A widget for sorting column entries with up/down controls."""

    def __init__(self, parent_widget, input_column_layout_string=""):
        self.columnstring = input_column_layout_string
        self.entries_list = self.columnstring.split(",")
        self.containerframe = tkinter.ttk.Frame(master=parent_widget)
        self.listcontainer_frame = tkinter.ttk.Frame(master=self.containerframe)
        self.entries_listbox = tkinter.Listbox(
            master=self.listcontainer_frame, height=len(self.entries_list)
        )
        self.entries_listbox.pack()
        self.buildinterface()
        self.listcontainer_frame.pack(side=tkinter.LEFT)
        self.adjustframe = tkinter.ttk.Frame(master=self.containerframe)
        move_up_button = tkinter.ttk.Button(
            master=self.adjustframe,
            text="UP",
            command=lambda: self._move_entry(True),
        )
        move_down_button = tkinter.ttk.Button(
            master=self.adjustframe,
            text="DOWN",
            command=lambda: self._move_entry(False),
        )
        move_up_button.pack(side=tkinter.TOP)
        move_down_button.pack(side=tkinter.BOTTOM)
        self.adjustframe.pack(side=tkinter.RIGHT)

    def set_columnstring(self, columnstring):
        self.columnstring = columnstring
        self.buildinterface()

    def buildinterface(self):
        self.entries_list = self.columnstring.split(",")
        self.entries_listbox.configure(height=1)
        for index in range(len(self.entries_list)):
            self.entries_listbox.delete(index)
        self.entries_listbox.configure(height=len(self.entries_list))
        for item in self.entries_list:
            self.entries_listbox.insert(tkinter.END, item)

    def _move_entry(self, move_up=False):
        current_selection = self.entries_listbox.selection_get()
        counter = 0
        for i in range(len(self.entries_list)):
            if current_selection == self.entries_listbox.get(i):
                break
            counter += 1
        self.entries_listbox.delete(counter)
        if move_up:
            if counter != 0:
                counter -= 1
        else:
            if counter != len(self.entries_list) - 1:
                counter += 1
        self.entries_listbox.insert(counter, current_selection)
        self.entries_listbox.select_set(counter)

    def get(self):
        return ",".join(
            [self.entries_listbox.get(i) for i in range(len(self.entries_list))]
        )
