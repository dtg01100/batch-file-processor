import platform
import tkinter
import tkinter.ttk


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
