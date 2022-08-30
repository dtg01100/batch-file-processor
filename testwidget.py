from shutil import move
import tkinter
import tkinter.ttk

root = tkinter.Tk()  # create root window
root.title("widget test")

columnlayout = ""

class columnSorterWidget():
    def __init__(self, parent_widget, input_column_layout_string=""):
        self.columnstring = input_column_layout_string
        self.entries_list = self.columnstring.split(",")
        self.containerframe = tkinter.ttk.Frame(master=parent_widget) 
        self.listcontainer_frame = tkinter.ttk.Frame(master=self.containerframe)
        self.entries_listbox = tkinter.Listbox(master=self.listcontainer_frame, height=len(self.entries_list))
        self.entries_listbox.pack()
        self.buildinterface()
        self.listcontainer_frame.pack(side=tkinter.LEFT)
        self.adjustframe = tkinter.ttk.Frame(master=self.containerframe)
        move_up_button = tkinter.ttk.Button(master=self.adjustframe, text="UP", command=lambda: self._move_entry(True))
        move_down_button = tkinter.ttk.Button(master=self.adjustframe, text="DOWN", command=lambda: self._move_entry(False))
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
            print(item)
            self.entries_listbox.insert(tkinter.END, item)

    def _move_entry(self, move_up = False):
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
            if counter != len(self.entries_list) -1:
                counter += 1
        self.entries_listbox.insert(counter, current_selection)
        self.entries_listbox.select_set(counter)

        for i in range(len(self.entries_list)):
            print(self.entries_listbox.get(i))

    def get(self):
        return ",".join([self.entries_listbox.get(i) for i in range(len(self.entries_list))])

test_sorterclass = columnSorterWidget(root)

test_sorterclass.set_columnstring("upc_number,qty_of_units,unit_cost,description,vendor_item")

test_sorterclass.containerframe.pack(side=tkinter.TOP)

def printsorter():
    print(test_sorterclass.get())

tkinter.ttk.Button(master=root, command=lambda: printsorter()).pack(side=tkinter.BOTTOM)

root.mainloop()
