import wx
from ObjectListView import ObjectListView, ColumnDefn
from datetime import datetime
from shutil import move, copy
from os import rmdir
import wx.lib.agw.multidirdialog as MDD
from ctypes import windll
import sqlite3

KERNELDLL = windll.LoadLibrary("kernel32.dll")

FRAME_TITLE = "Symlink Manager"
FRAME_SIZE = (1200, 300)
FRAME_POS = (200,200)

# Heading strings
PREV_HEADING = "Previous Links"
CURR_HEADING = "Current Links"

make_columns = lambda link_path: [
        ColumnDefn("Date", valueGetter="date", minimumWidth=75),
        ColumnDefn("Original Path", valueGetter="original_path", isSpaceFilling=True),
        ColumnDefn(link_path, valueGetter="link_path", isSpaceFilling=True)
    ]
PREV_COLUMNS = make_columns("Last Link Path")
CURR_COLUMNS = make_columns("Current Link Path")

# sqlite tables
PREV_TABLE = "previous"
PREV_SQL_COLUMNS = "(folder text, original_loc text, last_link text, date text)"
PREV_TABLE_DECLARATION = "%s %s" % (PREV_TABLE, PREV_SQL_COLUMNS)
CURR_TABLE = "current"
CURR_SQL_COLUMNS = "(folder text, original_loc text, current_link text, date text)"
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
NEW_STATE = -1
"""
'HEADING': Headings shown in actual GUI
'COLUMNS': Actual ColumnDefn's used by the ObjectListViews to make the lists
'STATE': Keeps track of whether folder is newly added, prev/curr linked;
         abstracts actual state values
'TABLE': SQL table names
'TABLE_DECLARATION': String used in SQL to make table
'OBJECTLISTVIEW': Stores data used in GUI list
'BUTTONS': Stores list of wx buttons used for looping
'PANEL': Stores the wx panel object used for each column
"""

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
                if id is None:
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
            val["OBJECTLISTVIEW"] = make_olv(self.panel, val['COLUMNS'], [
                Folder(row[1]+row[0], row[2], val['STATE'], row[3]) for row 
                in self.cursor.fetchall()])
            val['PANEL'] = make_column_panel(self.panel, val['HEADING'],
                                val["OBJECTLISTVIEW"], val['BUTTONS'])
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

    def on_new(self, event):
        selection = self.get_selection() # list of folder objects
        if not selection: # nothing selected; nothing to do
            return
        new_dir_dialog = wx.DirDialog(self, message = "Choose new location")
        if new_dir_dialog.ShowModal() == wx.ID_OK:
            # new location chosen
            new_loc = make_proper_loc(new_dir_dialog.GetPath())
            for folder in selection:
                old_state = folder.link_state
                symlink(folder, new_loc)
                if old_state == LISTS['CURR']['STATE']:
                    LISTS['CURR']['OBJECTLISTVIEW'].RefreshObject(folder)
                    self.cursor.execute("update current set current_link='%s' "
                        "where original_loc='%s'" %
                        (folder.link_loc, folder.original_loc))
                else:
                    if old_state == LISTS['PREV']['STATE']:
                        LISTS['PREV']['OBJECTLISTVIEW'].RemoveObject(folder)
                        self.cursor.execute("delete from previous where "
                            "original_loc='%s'" % (folder.original_loc))
                    LISTS['CURR']['OBJECTLISTVIEW'].AddObject(folder)
                    self.cursor.execute("insert into current values "
                        "('%s','%s','%s','%s')" % (folder.name,
                        folder.original_loc, folder.link_loc, folder.date))
                self.connection.commit()
        new_dir_dialog.Destroy()

    def on_match(self, event):
        self.new_link()
                    
    def on_unlink(self, event):
        pass

    def get_selection(self):
        """
        Return selected folders or ask user to select with DirDialog

        Return value: List of Folder objects, or None
        """
        prev_selection = LISTS["PREV"]["OBJECTLISTVIEW"].GetSelectedObjects()
        curr_selection = LISTS["CURR"]["OBJECTLISTVIEW"].GetSelectedObjects()
        if prev_selection or curr_selection:
            return prev_selection + curr_selection
        # no folder selected
        choose_dir_dialog = MDD.MultiDirDialog(self, title="Select folders to move")
        # Clicked ok after selecting folders
        returned_folders = None
        if choose_dir_dialog.ShowModal() == wx.ID_OK:
            chosen_new_folders = choose_dir_dialog.GetPaths()
            print "chosen: ", chosen_new_folders
            # No folders selected
            if len(chosen_new_folders) == 0:
                message_dialog_answer(self, "No folders selected.",
                                    "No selection", wx.OK|wx.CENTRE)
            # Folders selected
            invalid_folders, new_folders = [], []
            # Sort valid and invalid folders
            for folder in chosen_new_folders:
                if folder[-1] in (":", "\\"):
                    invalid_folders.append((folder, "Cannot add drive"))
                else:
                    new_folders.append(folder)
            # If invalid folders, show error with list and give option
            # to cancel new link operation
            if len(invalid_folders) != 0 and \
                        self.invalid_folders(self, invalid_folders) != wx.ID_OK:
                pass # invalid folders selected and user cancelled
            elif len(new_folders) != 0:
                returned_folders = [Folder(path) for path in new_folders]
        choose_dir_dialog.Destroy()
        return returned_folders

    def invalid_folders(self, parent, invalid_folders):
        message = "One or more folders cannot be linked: "
        for folder, error in invalid_folders:
            message += "\n%s (%s)" % (folder, error)
        return message_dialog_answer(parent, message, "Error: Invalid folders",
                                     wx.OK|wx.CANCEL|wx.CENTRE)

def symlink(folder, new_loc):
    new_path = new_loc + folder.name
    print("Moving...")
    move(folder.link_path, new_path) # moves actual files
    print("Moved.")
    if folder.link_path != folder.original_path:
        print("Removing old symlink...")
        rmdir(folder.original_path) # removes old symlink
        print("Old symlink removed.")
    print("Symlinking...")
    KERNELDLL.CreateSymbolicLinkW(folder.original_path, new_path, 1)
    print("Symlinked.")
    folder.set_link_loc(new_loc)

def message_dialog_answer(parent, message, title, styles):
    dlg = wx.MessageDialog(parent, message, title, styles)
    answer = dlg.ShowModal()
    dlg.Destroy()
    return answer

def yes_no_dialog(parent, question, caption = 'Yes or no?'):
    return message_dialog_answer(parent, question, caption, 
                                 wx.YES|wx.NO|wx.ICON_QUESTION)

def MakeBackupFile(file_name, error_message):
    try:
        copy(file_name, '~' + file_name)
    except:
        print(error_message)

def make_column_panel(parent, heading_txt, olv, button_tup):
    panel = wx.Panel(parent, -1)
    heading_text = wx.StaticText(panel, -1, heading_txt)
    olv.Reparent(panel)
    button_sizer = wx.BoxSizer(wx.HORIZONTAL)
    for button in button_tup:
        button_sizer.Add(button, flag=wx.ALL, border=5)
        button.Reparent(panel)
    list_sizer = wx.BoxSizer(wx.VERTICAL)
    list_sizer.Add(heading_text, flag=wx.ALIGN_CENTER)
    list_sizer.Add(olv, flag=wx.ALIGN_CENTER|wx.EXPAND, proportion=1)
    list_sizer.Add(button_sizer, flag=wx.ALIGN_CENTER)
    panel.SetSizer(list_sizer)
    panel.Layout()
    return panel

def make_olv(parent, col_titles, init_objects):
    olv = ObjectListView(parent, style=wx.LC_REPORT|wx.BORDER_SUNKEN)
    olv.SetColumns(col_titles)
    olv.SetObjects(init_objects)
    olv.AutoSizeColumns()
    return olv

def make_proper_loc(improper_loc):
    if improper_loc[-1] != u'\\':
        return improper_loc + u'\\'
    return improper_loc

class Folder():
    def __init__(self, original_path, link_loc=None, link_state=NEW_STATE, date=None):
        self.original_path = original_path
        self.original_loc, self.name = original_path.rsplit('\\', 1)
        self.original_loc = make_proper_loc(self.original_loc)
        self.link_state = link_state
        if link_loc is None:
            self.link_loc = self.original_loc
        else:
            self.link_loc = link_loc
        if date is not None:
            self.date = self.set_date()
        else:
            self.date = date

    @property
    def link_path(self):
        return self.link_loc + self.name

    def set_link_loc(self, link_loc):
        self.link_loc = link_loc
        self.set_date()
        self.link_state = LISTS['CURR']['STATE']

    def set_date(self):
        self.date = str(datetime.now())[:-7]

if __name__ == '__main__':
    app = wx.App(redirect=False)
    MainWindow().Show()
    app.MainLoop()