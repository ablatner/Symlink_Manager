#! C:\python27\python.exe

import wx
from ObjectListView import ObjectListView, ColumnDefn
from datetime import datetime
import shutil
import wx.lib.agw.multidirdialog as MDD
from ctypes import windll, wintypes
import os, ctypes, struct
import sqlite3
import stat

# KERNEL32DLL = windll.LoadLibrary("kernel32.dll")
KERNEL32DLL = windll.kernel32

FRAME_TITLE = "Symlink Manager"
FRAME_SIZE = (1200, 300)
FRAME_POS = (200,200)

# Heading strings
PREV_HEADING = "Previous Links"
CURR_HEADING = "Current Links"

def make_columns(link_path, **link_path_keyword_args):
    return [ColumnDefn("Date", valueGetter="date"),
            ColumnDefn("Original Path", valueGetter="original_path"),
            ColumnDefn(link_path, valueGetter="link_path", **link_path_keyword_args)
    ]

PREV_COLUMNS = make_columns("Last Link Path")
CURR_COLUMNS = make_columns("Current Link Path", isEditable=True)

# sqlite tables
PREV_TABLE = "previous"
PREV_SQL_COLUMNS = "(original_name text, original_loc text, current_name text, link_loc text, date text)"
PREV_TABLE_DECLARATION = "%s %s" % (PREV_TABLE, PREV_SQL_COLUMNS)
CURR_TABLE = "current"
CURR_SQL_COLUMNS = "(original_name text, original_loc text, current_name text, link_loc text, date text)"
CURR_TABLE_DECLARATION = "%s %s" % (CURR_TABLE, CURR_SQL_COLUMNS)

# data files
maindb = "database.db"

LISTS = {
    "PREV": {"HEADING": PREV_HEADING, "COLUMNS": PREV_COLUMNS, "STATE": 0,
        "TABLE": PREV_TABLE, "TABLE_DECLARATION": PREV_TABLE_DECLARATION},
    "CURR": {"HEADING": CURR_HEADING, "COLUMNS": CURR_COLUMNS, "STATE": 1,
        "TABLE": CURR_TABLE, "TABLE_DECLARATION": CURR_TABLE_DECLARATION}
}
NEW_STATE = -1

FOLDER_ERRORS = (
    ("Cannot link drive", lambda folder: folder[-1] in (":", "//")),
    ("Cannot link symlink", lambda folder: islink(folder))
)
SYMLINK_ERRORS = (
    ("Cannot link drive", lambda folder: folder[-1] in (":", "//")),
    ("Cannot add folder", lambda folder: not islink(folder)))

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
                    (wx.ID_ANY, "&Clear Link Database", "Clears database of "
                     "links", self.on_clear),
                    (wx.ID_EXIT, "E&xit", "Close the program", self.on_exit)
                )
            ),
            # ("&Edit", (
            #     )
            # ),
            ("&Help", (
                    (wx.ID_ABOUT, "&About", "Information about this program",
                    self.on_about),
                )
            )
        )

        menu_bar = wx.MenuBar()
        for (label, item_list) in menus:
            menu = wx.Menu()
            for (id, item, help_text, handler) in item_list:
                if id is None:
                    menu.AppendSeperator()
                else:
                    item = menu.Append(id, item, help_text)
                    self.Bind(wx.EVT_MENU, handler, item)
            menu_bar.Append(menu, label)
        self.SetMenuBar(menu_bar)

    def init_database(self):
        self.connection = sqlite3.connect(maindb)
        MakeBackupFile(maindb, 'Could not backup database.')
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
        self.panel.Bind(wx.EVT_BUTTON, self.on_prev, prev_button)
        add_button = wx.Button(self.panel, id=-1, label = "Add existing")
        self.panel.Bind(wx.EVT_BUTTON, self.on_add, add_button)
        LISTS['PREV']['BUTTONS'] = (new_button, match_button, prev_button, add_button)

        unlink_button = wx.Button(self.panel, id=-1, label = "Unlink")
        self.panel.Bind(wx.EVT_BUTTON, self.on_unlink, unlink_button)
        LISTS['CURR']['BUTTONS'] = (unlink_button,)

        col_sizer = wx.BoxSizer(wx.HORIZONTAL)
        for val in LISTS.values():
            self.cursor.execute("select * from %s" % val['TABLE'])
            val["OBJECTLISTVIEW"] = make_olv(self.panel, val['COLUMNS'],
                [Folder(os.path.join(row[1],row[0]), row[2], row[3], val['STATE'], row[4])
                 for row in self.cursor.fetchall()])
            val['PANEL'] = make_column_panel(self.panel, val['HEADING'],
                                val["OBJECTLISTVIEW"], val['BUTTONS'])
            col_sizer.Add((20,0))
            col_sizer.Add(val['PANEL'], proportion=1, flag=wx.EXPAND)
        col_sizer.Add((20,0))
        self.panel.SetSizer(col_sizer)
        self.panel.Fit()

    def on_clear(self, event):
        if yes_no_dialog(self, "Clear history of links and delete database "
            "file?") == wx.ID_YES:
            for val in LISTS.values():
                self.cursor.execute("drop table if exists %s" % val['TABLE'])
            for val in LISTS.values():
                val["OBJECTLISTVIEW"].DeleteAllItems()
            self.connection.commit()
            self.connection.close()
            self.init_database()

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
        selection = self.get_full_folder_selection("move")
        if not selection:
            return
        new_dir_dialog = wx.DirDialog(self, message = "Choose new location")
        if new_dir_dialog.ShowModal() == wx.ID_OK:
            # new location chosen
            new_loc = make_proper_loc(new_dir_dialog.GetPath())
            question = "Link the following folders to %s?" % new_loc
            if self.confirm_folders(question, selection):
                for folder in selection:
                    self.link(folder, new_loc)
        new_dir_dialog.Destroy()

    def on_match(self, event):
        selection = self.get_full_folder_selection("match")
        if not selection:
            return
        new_dir_dialog = wx.DirDialog(self, message = "Choose new root location")
        if new_dir_dialog.ShowModal() == wx.ID_OK:
            # new location chosen
            new_loc = make_proper_loc(new_dir_dialog.GetPath())
            question = "Match the following folders relative path?"
            if self.confirm_folders(question, selection):
                for folder in selection:
                    self.link(folder, os.path.join(new_loc, folder.original_loc.split('\\', 1)[1]))
        new_dir_dialog.Destroy()

    def on_prev(self, event):
        selection = self.get_olv_selection()
        if not selection:
            return
        question = "Relink the following folders to their previous location?"
        if self.confirm_folders(question, selection):
            for folder in selection:
                self.link(folder, folder.link_loc)

    def on_unlink(self, event):
        selection = self.get_olv_selection()
        if not selection:
            return
        question = "Unlink the following folders?"
        if self.confirm_folders(question, selection):
            for folder in selection:
                old_state = folder.link_state
                if self.unlink(self.panel, folder) != 0:
                    print("Unlink for %s failed." % folder.original_path)
                else:
                    LISTS['CURR']['OBJECTLISTVIEW'].RemoveObject(folder)
                    self.cursor.execute("delete from current where "
                        "original_name='%s' and original_loc='%s'" %
                        (folder.original_name, folder.original_loc))
                    LISTS['PREV']['OBJECTLISTVIEW'].AddObject(folder)
                    self.cursor.execute("insert into previous values "
                        "('%s','%s','%s','%s','%s')" % (folder.original_name,
                        folder.original_loc, folder.link_name, folder.link_loc,
                        folder.date))
            self.connection.commit()

    def on_add(self, event):
        selection = self.get_dir_dialog_selection("symlink", "add", SYMLINK_ERRORS)
        if not selection:
            return
        question = "Add the following symlinks?"
        if self.confirm_folders(question, selection):
            for symlink in selection:
                try:
                    symlink.link_loc = readlink(symlink.original_path)
                    symlink.set_date()
                    symlink.link_state = LISTS['CURR']['STATE']
                    LISTS['CURR']['OBJECTLISTVIEW'].AddObject(symlink)
                    self.cursor.execute("insert into current values "
                        "('%s','%s','%s','%s','%s')" % (symlink.original_name,
                        symlink.original_loc, symlink.link_name, symlink.link_loc,
                        symlink.date))
                except:
                    print("Could not add symlink %s" % symlink.original_path)
        self.connection.commit()

    def get_full_folder_selection(self, cmd):
        selection = self.get_olv_selection()
        if not selection:
            selection = self.get_dir_dialog_selection("folders", cmd, FOLDER_ERRORS) # list of folder objects
        return selection

    def get_dir_dialog_selection(self, obj_type, cmd, errors):
        # errors of form ((error message, lambda conditional),(),...)
        new_folders = []
        choose_dir_dialog = MDD.MultiDirDialog(self, title="Select %s to %s" % (obj_type, cmd))
        if choose_dir_dialog.ShowModal() == wx.ID_OK:
            chosen_new_folders = choose_dir_dialog.GetPaths()
            # No folders selected
            if len(chosen_new_folders) == 0:
                message_dialog_answer(self, "No %s selected." % obj_type,
                                    "No selection", wx.OK|wx.CENTRE)
            # Folders selected
            invalid_folders = []
            # Sort valid and invalid folders
            for folder in chosen_new_folders:
                is_error = False
                for message, conditional_func in errors:
                    if conditional_func(folder):
                        invalid_folders.append((folder, message))
                        is_error = True
                if not is_error:
                    new_folders.append(folder)
            # If invalid folders, show error with list and give option
            # to cancel new link operation
            if len(invalid_folders) != 0 and \
                        self.invalid_folders(self, invalid_folders) != wx.ID_OK:
                new_folders = [] # invalid folders selected and user cancelled
        choose_dir_dialog.Destroy()
        return [Folder(path) for path in new_folders]

    def get_olv_selection(self):
        selection = []
        for olv in [val["OBJECTLISTVIEW"] for val in LISTS.values()]:
            selection += olv.GetSelectedObjects()
        return selection

    def invalid_folders(self, parent, invalid_folders):
        message = "One or more folders cannot be linked: "
        for folder, error in invalid_folders:
            message += "\n%s (%s)" % (folder, error)
        return message_dialog_answer(parent, message, "Error: Invalid folders",
                                     wx.OK|wx.CANCEL|wx.CENTRE)

    def link(self, folder, new_loc):
        old_state = folder.link_state
        if self.symlink(folder, new_loc) != 0:
            print("Link for %s failed." % folder.original_path)
            return
        if old_state == LISTS['CURR']['STATE']:
            LISTS['CURR']['OBJECTLISTVIEW'].RefreshObject(folder)
            self.cursor.execute("update current set link_loc='%s' "
                "where original_name='%s' and original_loc='%s'" %
                (folder.link_loc, folder.original_name, folder.original_path))
        else:
            if old_state == LISTS['PREV']['STATE']:
                LISTS['PREV']['OBJECTLISTVIEW'].RemoveObject(folder)
                self.cursor.execute("delete from previous where "
                    "original_name='%s' and original_loc='%s'" %
                    (folder.original_name, folder.original_loc))
            LISTS['CURR']['OBJECTLISTVIEW'].AddObject(folder)
            self.cursor.execute("insert into current values "
                "('%s','%s','%s','%s','%s')" % (folder.original_name,
                folder.original_loc, folder.link_name, folder.link_loc,
                folder.date))
        self.connection.commit()

    def symlink(self, folder, new_loc):
        new_path = os.path.join(new_loc, folder.link_name)
        if folder.link_state == LISTS['CURR']['STATE']:
            current_path = folder.link_path
        else:
            current_path = folder.original_path
        print("Setting permissions...")
        for root, dirs, files in os.walk(current_path, topdown=False):
            for dir in dirs:
                dir = os.path.join(root, dir)
                try:
                    os.chmod(dir, get_perm(dir) | stat.S_IWUSR)
                except:
                    print("Could not set permissions on folder: %s" % dir)
                    return -1
            for file in files:
                file = os.path.join(root, file)
                try:
                    os.chmod(file, get_perm(file) | stat.S_IWUSR)
                except:
                    print("Could not set permissions on file: %s" % file)
                    return -1
        print("Permissions set.")

        print("Moving...")
        try:
            shutil.move(current_path, new_path) # moves actual files
            print("Moved.")
        except:
            print("Move failed of folder %s" % folder.current_path)
            return -1

        if folder.link_state == LISTS['CURR']['STATE'] and islink(folder.original_path):
            print("Removing old symlink...")
            try:
                os.rmdir(folder.original_path) # removes old symlink
                print("Old symlink removed.")
            except:
                print("Could not remove old symlink at: %s" % folder.original_path)
                try:
                    shutil.move(new_path, current_path)
                except:
                    print("Could not move folder back to link path: %s" % current_path)
                return -1

        print("Symlinking...")
        try:
            KERNEL32DLL.CreateSymbolicLinkW(folder.original_path, new_path, 1)
            print("Symlinked.")
        except:
            print("Could not symlink from %s to %s" % (folder.original_path, new_path))
            try:
                shutil.move(new_path, current_path)
            except:
                print("Could not move folder back to link path: %s" % current_path)
            if folder.link_state == LISTS['CURR']['STATE']:
                try:
                    KERNEL32DLL.CreateSymbolicLinkW(folder.original_path, current_path, 1)
                except:
                    print("Could not recreate old symlink from %s to %s" % (folder.original_path, current_path))
            return -1
        folder.link_loc = new_loc
        folder.set_date()
        folder.link_state = LISTS['CURR']['STATE']
        return 0

    def unlink(self, parent, folder):
        if folder.link_state != LISTS['CURR']['STATE']:
            print("Folder %s not currently linked. Cannot unlink." % folder.original_path)
            return -1

        if islink(folder.original_path):
            print("Removing old symlink...")
            try:
                os.rmdir(folder.original_path) # removes old symlink
                print("Old symlink removed.")
            except:
                print("Could not remove old symlink at: %s" % folder.original_path)
                return -1
        else:
            if yes_no_dialog(parent, "Move target back to %s?" % folder.original_path,
                             "Symlink not present at original location.") == wx.ID_NO:
                return -1

        print("Moving to original location...")
        try:
            shutil.move(folder.link_path, folder.original_path) # moves actual folders
            print("Moved.")
        except:
            print("Move failed of folder %s" % folder.link_path)
            return -1
        folder.link_state = LISTS['PREV']['STATE']
        return 0

    def confirm_folders(self, question, selection):
        for folder in selection:
            question += "\n%s" % folder.original_path
        return yes_no_dialog(self.panel, question) == wx.ID_YES

def get_perm(fname):
    return stat.S_IMODE(os.lstat(fname)[stat.ST_MODE])

'''
symlink handling with ctypes by crusherjoe on stackoverflow
http://stackoverflow.com/questions/1447575/symlinks-on-windows
'''
FSCTL_GET_REPARSE_POINT = 0x900a8

FILE_ATTRIBUTE_READONLY      = 0x0001
FILE_ATTRIBUTE_HIDDEN        = 0x0002
FILE_ATTRIBUTE_DIRECTORY     = 0x0010
FILE_ATTRIBUTE_NORMAL        = 0x0080
FILE_ATTRIBUTE_REPARSE_POINT = 0x0400

GENERIC_READ  = 0x80000000
GENERIC_WRITE = 0x40000000
OPEN_EXISTING = 3
FILE_READ_ATTRIBUTES = 0x80
FILE_FLAG_OPEN_REPARSE_POINT = 0x00200000
INVALID_HANDLE_VALUE = wintypes.HANDLE(-1).value

INVALID_FILE_ATTRIBUTES = 0xFFFFFFFF

FILE_FLAG_OPEN_REPARSE_POINT = 2097152
FILE_FLAG_BACKUP_SEMANTICS = 33554432
FILE_FLAG_REPARSE_BACKUP = 35651584

GetFileAttributes = windll.kernel32.GetFileAttributesW
_CreateFileW = windll.kernel32.CreateFileW
_DevIoCtl = windll.kernel32.DeviceIoControl
_DevIoCtl.argtypes = [
    wintypes.HANDLE, #HANDLE hDevice
    wintypes.DWORD, #DWORD dwIoControlCode
    wintypes.LPVOID, #LPVOID lpInBuffer
    wintypes.DWORD, #DWORD nInBufferSize
    wintypes.LPVOID, #LPVOID lpOutBuffer
    wintypes.DWORD, #DWORD nOutBufferSize
    ctypes.POINTER(wintypes.DWORD), #LPDWORD lpBytesReturned
    wintypes.LPVOID] #LPOVERLAPPED lpOverlapped
_DevIoCtl.restype = wintypes.BOOL

def islink(path):
    assert os.path.isdir(path), path
    if GetFileAttributes(path) & FILE_ATTRIBUTE_REPARSE_POINT:
        return True
    else:
        return False

def DeviceIoControl(hDevice, ioControlCode, input, output):
    # DeviceIoControl Function
    # http://msdn.microsoft.com/en-us/library/aa363216(v=vs.85).aspx
    if input:
        input_size = len(input)
    else:
        input_size = 0
    if isinstance(output, int):
        output = ctypes.create_string_buffer(output)
    output_size = len(output)
    assert isinstance(output, ctypes.Array)
    bytesReturned = wintypes.DWORD()
    status = _DevIoCtl(hDevice, ioControlCode, input,
                       input_size, output, output_size, bytesReturned, None)
    if status != 0:
        return output[:bytesReturned.value]
    else:
        return None


def CreateFile(path, access, sharemode, creation, flags):
    return _CreateFileW(path, access, sharemode, None, creation, flags, None)

SymbolicLinkReparseFormat = "LHHHHHHL"
SymbolicLinkReparseSize = struct.calcsize(SymbolicLinkReparseFormat);

def readlink(path):
    """ Windows readlink implementation. """
    # This wouldn't return true if the file didn't exist, as far as I know.
    assert islink(path)
    assert type(path) == unicode

    # Open the file correctly depending on the string type.
    hfile = CreateFile(path, GENERIC_READ, 0, OPEN_EXISTING,
                       FILE_FLAG_REPARSE_BACKUP)
    # MAXIMUM_REPARSE_DATA_BUFFER_SIZE = 16384 = (16*1024)
    buffer = DeviceIoControl(hfile, FSCTL_GET_REPARSE_POINT, None, 16384)
    KERNEL32DLL.CloseHandle(hfile)

    # Minimum possible length (assuming length of the target is bigger than 0)
    if not buffer or len(buffer) < 9:
        return None

    # Only handle SymbolicLinkReparseBuffer
    (tag, dataLength, reserver, SubstituteNameOffset, SubstituteNameLength,
     PrintNameOffset, PrintNameLength,
     Flags) = struct.unpack(SymbolicLinkReparseFormat,
                            buffer[:SymbolicLinkReparseSize])
    start = SubstituteNameOffset + SymbolicLinkReparseSize
    actualPath = buffer[start : start + SubstituteNameLength].decode("utf-16")
    # This utf-16 string is null terminated
    index = actualPath.find(u"\0")
    assert index > 0
    if index > 0:
        actualPath = actualPath[:index]
    if actualPath.startswith(u"?\\"):
        return actualPath[2:]
    else:
        return actualPath
'''
end code from crusherjoe
'''

def message_dialog_answer(parent, message, title, styles):
    dlg = wx.MessageDialog(parent, message, title, styles)
    answer = dlg.ShowModal()
    dlg.Destroy()
    return answer

def yes_no_dialog(parent, question, caption = 'Yes or no?'):
    return message_dialog_answer(parent, question, caption,
                                 wx.YES_NO|wx.ICON_QUESTION)

def MakeBackupFile(file_name, error_message):
    try:
        shutil.copy(file_name, '~' + file_name)
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
    olv = ObjectListView(parent, style=wx.LC_REPORT|wx.BORDER_SUNKEN,
        cellEditMode=ObjectListView.CELLEDIT_DOUBLECLICK)
    olv.SetColumns(col_titles)
    olv.SetObjects(init_objects)
    olv.AutoSizeColumns()
    return olv

def make_proper_loc(improper_loc):
    if improper_loc[-1] != u'\\':
        return improper_loc + u'\\'
    return improper_loc

class Folder():
    def __init__(self, original_path, link_name=None, link_loc=None, link_state=NEW_STATE, date=None):
        self.original_path = original_path
        self.original_loc, self.original_name = original_path.rsplit('\\', 1)
        self.original_loc = make_proper_loc(self.original_loc)

        self.link_state = link_state
        if link_loc is None:
            self.link_loc = self.original_loc
        else:
            self.link_loc = link_loc
        if link_name is None:
            self.link_name = self.original_name
        else:
            self.link_name = link_name

        if date is None:
            self.date = self.set_date()
        else:
            self.date = date

    @property
    def link_path(self):
        return os.path.join(self.link_loc, self.link_name)

    def set_date(self):
        self.date = str(datetime.now())[:-7]

class MainApp(wx.App):
    def OnInit(self):
        frame = MainWindow()
        frame.Show(True)
        self.SetTopWindow(frame)
        return True

if __name__ == '__main__':
    app = MainApp()
    app.MainLoop()