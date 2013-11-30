import wx
from ObjectListView import ObjectListView, ColumnDefn
from datetime import datetime
import shutil
import os
import wx.lib.agw.multidirdialog as MDD
import ctypes
import csv
import sqlite3

KERNELDLL = ctypes.windll.LoadLibrary("kernel32.dll")

FRAME_TITLE = "Symlink Manager"
FRAME_SIZE = (1200, 300)
FRAME_POS = (200,200)

# Heading strings
PREV_HEADING = "Previous Links"
CURR_HEADING = "Current Links"

make_columns = lambda link_name: [
        ColumnDefn("Date", valueGetter="date"),
        ColumnDefn("Original Path", valueGetter="original_path", isSpaceFilling=True),
        ColumnDefn(link_name, valueGetter="link_path", isSpaceFilling=True)
    ]
PREV_COLUMNS = make_columns("Last Link Path")
CURR_COLUMNS = make_columns("Current Link Path")

# sqlite tables
PREV_TABLE = "previous"
PREV_SQL_COLUMNS = "(date text, folder text, original_loc text, last_link text)"
PREV_TABLE_DECLARATION = "%s %s" % (PREV_TABLE, PREV_SQL_COLUMNS)
CURR_TABLE = "current"
CURR_SQL_COLUMNS = "(date text, folder text, original_loc text, current_link text)"
CURR_TABLE_DECLARATION = "%s %s" % (CURR_TABLE, CURR_SQL_COLUMNS)

# data files
PREV_HISTORY_FILE = "prev_history.csv"
CURR_HISTORY_FILE = "curr_history.csv"

LISTS = {
    "PREV": {"HEADING": PREV_HEADING, "COLUMNS": PREV_COLUMNS, "STATE": 0,
        "TABLE": PREV_TABLE, "TABLE_DECLARATION": PREV_TABLE_DECLARATION},
    "CURR": {"HEADING": CURR_HEADING, "COLUMNS": CURR_COLUMNS, "STATE": 1,
        "TABLE": CURR_TABLE, "TABLE_DECLARATION": CURR_TABLE_DECLARATION}
}

class MainWindow(wx.Frame):
    def __init__(self):
        wx.Frame.__init__(self, None, wx.ID_ANY, FRAME_TITLE, size=FRAME_SIZE,
                          style = wx.DEFAULT_FRAME_STYLE, pos = FRAME_POS)
        self.panel = wx.Panel(self) # wx.window that contains ctrls
        self.create_menu()
        self.CreateStatusBar()
        self.init_database()
        self.create_controls()

    def create_menu(self):
        menus = (
            ("&File", (
                    (wx.ID_EXIT, "E&xit", "Close the program", self.on_exit),
                )
            ),
            ("&Edit", (
                )
            ),
            ("&Help", (
                    (wx.ID_ABOUT, "&About", "Information about this program",
                    self.on_about),
                )
            )
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
            self.cursor.execute("create table if not exists %s" %
                                 (val['TABLE_DECLARATION']))
        self.connection.commit()

    def create_controls(self):
        # Buttons
        new_button = wx.Button(self.panel, id=-1, label = "New")
        self.panel.Bind(wx.EVT_BUTTON, self.on_new, new_button)
        match_button = wx.Button(self.panel, id=-1, label = "Match")
        match_button.Bind(wx.EVT_BUTTON, self.on_match, match_button)
        prev_button = wx.Button(self.panel, id=-1, label = "Prev")
        #self.panel.Bind(wx.EVT_BUTTON, self.OnPrev, prev_button)
        LISTS['PREV']['BUTTONS'] = (new_button, match_button, prev_button)

        unlink_button = wx.Button(self.panel, id=-1, label = "Unlink")
        self.panel.Bind(wx.EVT_BUTTON, self.on_unlink, unlink_button)
        LISTS['CURR']['BUTTONS'] = (unlink_button,)

        col_sizer = wx.BoxSizer(wx.HORIZONTAL)
        for val in LISTS.values():
            self.cursor.execute("select * from %s" % val['TABLE'])
            val["ObjectListView"] = make_olv(self.panel, val['COLUMNS'], [
                Folder(row[2]+'\\'+row[1], row[3], val['STATE'], row[0]) for row 
                in self.cursor.fetchall()])
            val['PANEL'] = ColPanel(self.panel, val['HEADING'],
                                val["ObjectListView"], val['BUTTONS'])
            col_sizer.Add((20,0))
            col_sizer.Add(val['PANEL'], proportion=1, flag=wx.EXPAND)
        col_sizer.Add((20,0))
        self.panel.SetSizer(col_sizer)
        self.panel.Fit()

    def on_exit(self, event):
        self.connection.commit()
        self.connection.close()
        self.Close()

    def on_about(self, event):
        dialog = wx.MessageDialog(self, "Create and manage symlinks.", "About "
                                  "Symlink Manager", wx.OK|wx.CENTRE)
        dialog.ShowModal()
        dialog.Destroy()

    def new_links(self, folders, new_loc):
        pass
     # def on_new(self. event):
        #     choose_dir_dialog = MDD.MultiDirDialog(self, \
        #                         title="Select folders to move")
        #     # Clicked ok on multi folder select
        #     if choose_dir_dialog.ShowModal() == wx.ID_OK:
                # folders_list = choose_dir_dialog.GetPaths()
                # # No folders selected
                # if len(folders_list) == 0:
                #     self.no_folders(choose_dir_dialog)
                # # Folders selected
                # else:
                #     invalid_list, new_folders = [], []
                #     # Sort valid and invalid folders
                #     for folder in folders_list:
                #         if folder[-1] in (":", "\\"):
                #             invalid_list.append((folder, "Cannot add drive"))
                #         else:
                #             new_folders.append(folder)
                #     # If invalid folders, show error with list and give option to
                #     # cancel new link operation
                #     continue_op = wx.ID_OK
                #     if len(invalid_list) != 0:
                #         continue_op = self.invalid_folders(choose_dir_dialog,
                #                                            invalid_list)
                #     if len(new_folders) != 0 and continue_op == wx.ID_OK:
                #         self.make_link(new_folders)

    def on_new(self, event):
        selection = self.get_selection()
        new_dir_dialog = wx.DirDialog(self, message = "Choose new location")
        if new_dir_dialog.ShowModal() == wx.ID_OK:
            new_loc = new_dir_dialog.GetPath()
            for folder in selection:
                if folder.link_state == -1:
                    folder.link_loc = new_loc
                    folder.link_state = 1
                    # LISTS['CURR']['ObjectListView'].AddObject(folder)
                    for current in LISTS["CURR"]["ObjectListView"].GetObjects():
                        if current.link_path == folder.original_path:
                            # dialog about folder being result of symlink
                            # ask for confirmation and use move_symlink()
                            pass
                elif folder.link_state == 0:
                    LISTS['CURR']['ObjectListView'].AddObject(
                        Folder(folder.original_path, new_loc, 1))
                elif folder.link_state == 1:
                    folder
                self.cursor.execute("insert into current values "
                    "('%s','%s','%s','%s')" % 
                    (folder.date, folder.name, folder.original_loc,
                    folder.link_loc))
                symlink(folder.original_path, folder.link_path)
            self.connection.commit()

        new_dir_dialog.Destroy()

    def on_match(self, event):
        self.new_link()
                    
    def on_unlink(self, event):
        pass

    def get_selection(self):
        prev_selection = LISTS["PREV"]["ObjectListView"].GetSelectedObjects()
        curr_selection = LISTS["CURR"]["ObjectListView"].GetSelectedObjects()
        if not (prev_selection or curr_selection):
            # no folder selected
            choose_dir_dialog = MDD.MultiDirDialog(self, \
                                title="Select folders to move")
            # Clicked ok after selecting folders
            if choose_dir_dialog.ShowModal() == wx.ID_OK:
                chosen_new_folders = choose_dir_dialog.GetPaths()
                # No folders selected
                if len(chosen_new_folders) == 0:
                    self.no_folders(choose_dir_dialog)
                # Folders selected
                else:
                    invalid_folders, new_folders = [], []
                    # Sort valid and invalid folders
                    for folder in chosen_new_folders:
                        if folder[-1] in (":", "\\"):
                            invalid_folders.append((folder, "Cannot add drive"))
                        else:
                            new_folders.append(folder)
                    # If invalid folders, show error with list and give option
                    # to cancel new link operation
                    continue_op = wx.ID_OK
                    if len(invalid_folders) != 0:
                        continue_op = self.invalid_folders(choose_dir_dialog,
                                                           invalid_folders)
                    if len(new_folders) != 0 and continue_op == wx.ID_OK:
                        return [Folder(path, None) for path in new_folders]
        return prev_selection + curr_selection

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

    def no_folders(self, parent):
        none_dialog = wx.MessageDialog(parent, "No folders selected.",
                                        "No selection", wx.OK|wx.CENTRE)
        none_dialog.ShowModal()
        none_dialog.Destroy()


def symlink(old_path, new_path):
    print("Moving...")
    shutil.move(old_path, new_path)
    print("Moved.")
    print("Symlinking...")
    KERNELDLL.CreateSymbolicLinkW(old_path, new_path, 1)
    print("Symlinked.")

def move_symlink(original_path, old_link_path, new_link_path):
    print("Moving...")
    shutil.move(old_link_path, new_link_path)
    print("Moved.")
    print("Removing old link...")
    os.rmdir(original_path)
    print("Old link removed.")
    print("Symlinking...")
    KERNELDLL.CreateSymbolicLinkW(original_path, new_link_path, 1)
    print("Symlinked.")

def YesNoDialog(parent, question, caption = 'Yes or no?'):
    dlg = wx.MessageDialog(parent, question, caption, 
                           wx.YES|wx.NO|wx.ICON_QUESTION)
    answer = dlg.ShowModal()
    dlg.Destroy()
    return answer

def MakeBackupFile(file_name, error_message):
    try:
        shutil.copy(file_name, '~' + file_name)
    except:
        print(error_message)

class ColPanel(wx.Panel):
    def __init__(self, parent, heading_txt, olv, button_tup):
        wx.Panel.__init__(self, parent, -1)
        heading_text = wx.StaticText(self, -1, heading_txt)
        olv.Reparent(self)
        button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        for button in button_tup:
            button_sizer.Add(button, flag=wx.ALL, border=5)
            button.Reparent(self)

        list_sizer = wx.BoxSizer(wx.VERTICAL)
        list_sizer.Add(heading_text, flag=wx.ALIGN_CENTER)
        list_sizer.Add(olv, flag=wx.ALIGN_CENTER|wx.EXPAND, proportion=1)
        list_sizer.Add(button_sizer, flag=wx.ALIGN_CENTER)
        self.SetSizer(list_sizer)
        self.Layout()

def make_olv(parent, col_titles, init_objects):
    olv = ObjectListView(parent, style=wx.LC_REPORT|wx.BORDER_SUNKEN)
    olv.SetColumns(col_titles)
    olv.SetObjects(init_objects)
    olv.AutoSizeColumns()
    return olv

class Folder():
    def __init__(self, original_path, link_loc, link_state=-1, date=None):
        # link_state: -1 for new folder
        #              0 for previously
        #              1 for currently
        self.original_path = original_path
        self.original_loc, self.name = original_path.rsplit('\\', 1)
        self.link_loc = link_loc
        self.link_state = link_state
        if date == None:
            self.date = str(datetime.now())[:-7]
        else:
            self.date = date
    @property
    def link_path():
        return link_loc + '\\' + self.name

if __name__ == '__main__':
    app = wx.App(redirect=False)
    MainWindow().Show()
    app.MainLoop()