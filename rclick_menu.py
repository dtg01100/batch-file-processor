#  this module was from the following address
#  https://paperrobot.wordpress.com/2008/12/24/python-right-click-edit-menu-widget/

import tkinter

from tk_extra_widgets import RightClickMenu
 
if __name__ == '__main__':
    root = tkinter.Tk()
    root.geometry("156x65")
    tkinter.Label(root, text="Right mouse click in\nthe entry widget below:").pack()
    entry_w = tkinter.Entry(root)
    entry_w.pack()
    rclick = RightClickMenu(entry_w)
    entry_w.bind("<3>", rclick)
    root.mainloop()