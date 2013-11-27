import wx
import shutil
import wx.lib.agw.multidirdialog as MDD
import ctypes
import csv
import sqlite3

KERNELDLL = ctypes.windll.LoadLibrary("kernel32.dll")

FRAME_TITLE = "Symlink Manager"
FRAME_SIZE = (700, 500)
FRAME_POS = (200,200)

# Heading strings
PREV_HEADING = "Previous Links"
CURR_HEADING = "Current Links"
# folder name = original_loc+name
PREV_COLUMN_TITLES = ["Number", "Folder", "Last Link Path"]
CURR_COLUMN_TITLES = ["Folder", "Current Link Path"]

# sqlite tables
PREV_TABLE = "previous"
PREV_COLUMNS = "(id integer primary key, name text, " \
                    "original_loc text, last_link text)"
PREV_TABLE_DECLARATION = "%s %s" % (PREV_TABLE, PREV_COLUMNS)
CURR_TABLE = "current"
CURR_COLUMNS = "(name text, original_loc text, current_link text)"
CURR_TABLE_DECLARATION = "%s %s" % (CURR_TABLE, CURR_COLUMNS)

# data files
PREV_HISTORY_FILE = "prev_history.csv"
CURR_HISTORY_FILE = "curr_history.csv"

LISTS = {"PREV": {"HEADING": PREV_HEADING, "COLUMN_TITLES": PREV_COLUMN_TITLES,\
           "TABLE": PREV_TABLE, "TABLE_DECLARATION": PREV_TABLE_DECLARATION}, \
         "CURR": {"HEADING": CURR_HEADING, "COLUMN_TITLES": CURR_COLUMN_TITLES,\
           "TABLE": CURR_TABLE, "TABLE_DECLARATION": CURR_TABLE_DECLARATION}}


class MainWindow(wx.Frame):
    def __init__(self):
        wx.Frame.__init__(self, None, wx.ID_ANY, FRAME_TITLE, size=FRAME_SIZE,
                          style = wx.DEFAULT_FRAME_STYLE, pos = FRAME_POS)
        self.panel = wx.Panel(self) # wx.window that contains ctrls
        self.create_menu()
        self.CreateStatusBar()
        self.init_database()
        self.create_controls()
        self.Fit()

    def create_menu(self):
        menus = (("&File", \
                   ((wx.ID_EXIT, "E&xit", "Close the program", self.on_exit), \
                   ) \
                 ), \

                 ("&Edit", \
                   () \
                 ), \

                 ("&Help", \
                    ((wx.ID_ABOUT, "&About", "Information about this program", \
                      self.on_about), \
                    ) \
                 ) \
                )

        menu_bar = wx.MenuBar()
        for (label, menu_list) in menus:
            menu = wx.Menu()
            for (id, label, help_text, handler) in menu_list:
                if id == None:
                    menu.AppendSeperator()
                else:
                    item = menu.Append(id, label, help_text)
                    self.Bind(wx.EVT_MENU, handler, item)
            menu_bar.Append(menu, label)
        self.SetMenuBar(menu_bar)

    def init_database(self):
        MakeBackupFile('database.db', 'Database created.')
        self.connection = sqlite3.connect('database.db')
        self.cursor = self.connection.cursor()
        for val in LISTS.values():
            self.cursor.execute("create table if not exists %s" % \
                                 (val['TABLE_DECLARATION']))
        self.connection.commit()

    def create_controls(self):
        # Buttons
        new_button = wx.Button(self.panel, id=-1, label = "New")
        self.panel.Bind(wx.EVT_BUTTON, self.on_new, new_button)
        match_button = wx.Button(self.panel, id=-1, label = "Match")
        #match_button.Bind(wx.EVT_BUTTON, self.OnMatch, match_button)
        prev_button = wx.Button(self.panel, id=-1, label = "Prev")
        #self.panel.Bind(wx.EVT_BUTTON, self.OnPrev, prev_button)
        LISTS['PREV']['BUTTONS'] = (new_button, match_button, prev_button)

        unlink_button = wx.Button(self.panel, id=-1, label = "Unlink")
        self.panel.Bind(wx.EVT_BUTTON, self.on_unlink, unlink_button)
        LISTS['CURR']['BUTTONS'] = (unlink_button,)

        col_sizer = wx.BoxSizer(wx.HORIZONTAL)
        for val in LISTS.values():
            self.cursor.execute("select * from %s" % val['TABLE'])
            list_ctrl = FolderListCtrl(self.panel, val['COLUMN_TITLES'], \
                                           self.cursor.fetchall())
            val['PANEL'] = ColPanel(self.panel, val['HEADING'], \
                              list_ctrl, val['BUTTONS'])
            col_sizer.Add((20,0))
            col_sizer.Add(val['PANEL'], proportion=1, flag=wx.EXPAND)
        col_sizer.Add((20,0))
        self.SetSizer(col_sizer)

    def on_exit(self, event):
        self.connection.commit()
        self.connection.close()
        # OverwriteDataCSV(CURR_HISTORY_FILE, self.curr_data)
        self.Close()

    def on_about(self, event):
        dialog = wx.MessageDialog(self, "Create and manage symlinks.", "About "
                                  "Symlink Manager", wx.OK|wx.CENTRE)
        dialog.ShowModal()
        dialog.Destroy()

    def new_link(self, new_loc=None):
        prev_selection = get_selection(self.prev_listCtrl)
        curr_selection = get_selection(self.curr_listCtrl)
        if prev_selection == -1 and curr_selection == -1:
            # no folder selected
            choose_dir_dialog = MDD.MultiDirDialog(self, \
                                title="Select folders to move")
            # Clicked ok after selecting folders
            if choose_dir_dialog.ShowModal() == wx.ID_OK:
                pass

    def on_new(self, event):
        self.new_link()

    # def on_new(self. event):
    #     choose_dir_dialog = MDD.MultiDirDialog(self, \
    #                         title="Select folders to move")
    #     # Clicked ok on multi folder select
    #     if choose_dir_dialog.ShowModal() == wx.ID_OK:
    #         folders_list = choose_dir_dialog.GetPaths()
    #         # No folders selected
    #         if len(folders_list) == 0:
    #             self.no_folders(choose_dir_dialog)
    #         # Folders selected
    #         else:
    #             invalid_list, new_folders = [], []
    #             # Sort valid and invalid folders
    #             for folder in folders_list:
    #                 if folder[-1] in (":", "\\"):
    #                     invalid_list.append((folder, "Cannot add drive"))
    #                 else:
    #                     new_folders.append(folder)
    #             # If invalid folders, show error with list and give option to
    #             # cancel new link operation
    #             continue_op = wx.ID_OK
    #             if len(invalid_list) != 0:
    #                 continue_op = self.invalid_folders(choose_dir_dialog,
    #                                                    invalid_list)
    #             if len(new_folders) != 0 and continue_op == wx.ID_OK:
    #                 self.make_link(new_folders)
                    
    def on_unlink(self, event):
        pass

    def invalid_folders(self, parent, invalid_folders):
        message = "One or more folders cannot be linked: "
        for folder, error in invalid_folders:
            message += "\n%s (%s)" % (folder, error)
        bad_folder_diag = wx.MessageDialog(parent, message =
                        message, caption="Error: Invalid folders",
                        style=wx.OK|wx.CANCEL|wx.CENTRE)
        choice = bad_folder_diag.ShowModal()
        bad_folder_diag.Destroy()
        return choice

    def make_link(self, to_link):
        new_dir_dialog = wx.DirDialog(self, message = "Choose new location")
        new_links = []
        if new_dir_dialog.ShowModal() == wx.ID_OK:
            index, new_loc = 0, new_dir_dialog.GetPath()
            for folder in to_link:
                self.curr_listCtrl.InsertStringItem(index, folder)
                self.curr_listCtrl.SetStringItem(index, 1, new_loc)
                new_links.append(symlink(folder, new_loc))
                index += 1
        new_dir_dialog.Destroy()
        new_links.append(self.curr_data)
        self.curr_data = new_links

    def OnMatch(self, event):
        dialog = wx.MessageDialog(self, "Moves to same location on another "\
                                  "drive", "Matching", wx.OK|wx.CENTRE)
        dialog.ShowModal()
        dialog.Destroy()

    def no_folders(self, parent):
        none_dialog = wx.MessageDialog(parent, "No folders selected.",
                                        "No selection", wx.OK|wx.CENTRE)
        none_dialog.ShowModal()
        none_dialog.Destroy()

def symlink(old_path, new_loc):
    old_loc, folder_name = old_path.rsplit('\\', 1)
    new_path = new_loc + '\\' + folder_name
    print("Moving...")
    shutil.move(old_path, new_path)
    print("Moved.")
    print("Symlinking...")
    KERNELDLL.CreateSymbolicLinkW(old_path, new_path, 1)
    print("Symlinked.")
    return [folder_name, old_loc, new_loc]

def YesNoDialog(parent, question, caption = 'Yes or no?'):
    dlg = wx.MessageDialog(parent, question, caption, 
                           wx.YES|wx.NO|wx.ICON_QUESTION)
    answer = dlg.ShowModal()
    dlg.Destroy()
    return answer

def OverwriteDataCSV(file_name, data):
    with open(file_name, "b") as file:
        writer = csv.writer(file)
        writer.writerows(data)

def OpenDataCSV(file_name):
    data = []
    try:
        with open(file_name, "rb") as file:
            reader = csv.reader(file, delimiter = ',')
            for row in reader:
                data.append(row)
    except IOError:
        pass
    return data

def MakeBackupFile(file_name, error_message):
    try:
        shutil.copy(file_name, '~' + file_name)
    except:
        print(error_message)

def get_selection(list_ctrl, coL_reader=None):
    # col reader is function that selects desired columns and handles strings
    if list_ctrl.GetSelectedItemCount() > 0:
        selection = [list_ctrl.GetFirstSelected()]
        while len(selection) < list_ctrl.GetSelectedItemCount():
            # gets list of indicies of selected items
            # NOT the items themselves
            next_item = list_ctrl.GetNextSelected(selection[-1])
            selection.append(next_item)
        return selection
    return -1

class ColPanel(wx.Panel):
    def __init__(self, parent, heading_txt, folder_listCtrl, button_tup):
        wx.Panel.__init__(self, parent, -1)

        heading_text = wx.StaticText(self, -1, heading_txt)

        folder_listCtrl.Reparent(self)

        button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        for button in button_tup:
            button_sizer.Add(button, flag=wx.ALL, border=5)
            button.Reparent(self)

        list_sizer = wx.BoxSizer(wx.VERTICAL)
        list_sizer.Add(heading_text, flag=wx.ALIGN_CENTER)
        list_sizer.Add(folder_listCtrl, flag=wx.ALIGN_CENTER)
        list_sizer.Add(button_sizer, flag=wx.ALIGN_CENTER)

        self.SetSizer(list_sizer)
        self.Layout()

class FolderListCtrl(wx.ListCtrl):
    def __init__(self, parent, col_titles, init_data):
        wx.ListCtrl.__init__(self, parent, size=(300,200))
        self.SetSingleStyle(wx.LC_REPORT|wx.BORDER_SUNKEN)
        for title in col_titles:
            self.InsertColumn(col_titles.index(title), title)
        for row in init_data:
            self.Append(row)

if __name__ == '__main__':
    app = wx.App()
    appFrame = MainWindow().Show()
    app.MainLoop()