import wx
import shutil
import wx.lib.agw.multidirdialog as MDD
import ctypes
import csv

kerneldll = ctypes.windll.LoadLibrary("kernel32.dll")

FRAME_TITLE = "Symlink Manager"
FRAME_SIZE = (700, 500)
FRAME_POS = (200,200)

# data files
PREV_HISTORY_FILE = "prev_history.csv"
CURR_HISTORY_FILE = "curr_history.csv"

class MainWindow(wx.Frame):    
    def __init__(self):
        wx.Frame.__init__(self, None, wx.ID_ANY, FRAME_TITLE, size=FRAME_SIZE,
                          style = wx.DEFAULT_FRAME_STYLE, pos = FRAME_POS)
        self.panel = wx.Panel(self) # wx.window that contains ctrls
        self.panel.BackgroundColour = (250,0,0)

        self.create_menu()
        self.CreateStatusBar()

        self.create_controls()

        # Create column panels
        prev_panel = ColPanel(self.panel, self.prev_heading,
                              self.prev_listCtrl, self.prev_buttons)
        prev_panel.BackgroundColour = (0,255,0)
        curr_panel = ColPanel(self.panel, self.curr_heading,
                              self.curr_listCtrl, self.curr_buttons)
        curr_panel.BackgroundColour = (0,255,255)

        col_sizer = wx.BoxSizer(wx.HORIZONTAL)
        col_sizer.Add((20,0))
        col_sizer.Add(prev_panel, proportion=1, flag=wx.EXPAND)
        col_sizer.Add((20,0))
        col_sizer.Add(curr_panel, proportion=1, flag=wx.EXPAND)
        col_sizer.Add((20,0))

        self.SetSizer(col_sizer)
        self.Fit()

    def create_menu(self):
        file_menu = wx.Menu()
        for id, label, help_text, handler in \
            [(wx.ID_EXIT, "E&xit", "Close the program", self.on_exit)]:
            if id == None:
                file_menu.AppendSeperator()
            else:
                item = file_menu.Append(id, label, help_text)
                self.Bind(wx.EVT_MENU, handler, item)

        edit_menu = wx.Menu()
        for id, label, help_text, handler in \
            []:
            if id == None:
                edit_menu.AppendSeperator()
            else:
                item = edit_menu.Append(id, label, help_text)
                self.Bind(wx.EVT_MENU, handler, item)

        help_menu = wx.Menu()
        for id, label, help_text, handler in \
            [(wx.ID_ABOUT, "&About", "Information about this program",
              self.on_about)]:
            if id == None:
                help_menu.AppendSeperator()
            else:
                item = help_menu.Append(id, label, help_text)
                self.Bind(wx.EVT_MENU, handler, item)

        menus = ((file_menu, "&File"), (edit_menu, "&Edit"),
                     (help_menu, "&Help"))
        menu_bar = wx.MenuBar()
        for (menu, label) in menus:
            menu_bar.Append(menu, label)
        self.SetMenuBar(menu_bar)

    def on_exit(self, event):
        self.Close()

    def on_about(self, event):
        dialog = wx.MessageDialog(self, "Create and manage symlinks.", "About "
                                  "Symlink Manager", wx.OK|wx.CENTRE)
        dialog.ShowModal()
        dialog.Destroy()

    def create_controls(self):
        # Heading strings
        self.prev_heading = "Previous Links"
        self.curr_heading = "Current Links"
        # Folder lists
        init_prev_data = OpenDataCSV(PREV_HISTORY_FILE)
        self.prev_listCtrl = FolderListCtrl(self.panel, ["Folder Path",\
                             "Last Linked Path"], init_prev_data)
        init_curr_data = OpenDataCSV(CURR_HISTORY_FILE)
        self.curr_listCtrl = FolderListCtrl(self.panel, ["Folder Path",\
                             "Currently Linked Path"], init_curr_data)
        # Buttons
        new_button = wx.Button(self.panel, id=-1, label = "New")
        self.panel.Bind(wx.EVT_BUTTON, self.on_new, new_button)
        match_button = wx.Button(self.panel, id=-1, label = "Match")
        #match_button.Bind(wx.EVT_BUTTON, self.OnMatch, match_button)
        prev_button = wx.Button(self.panel, id=-1, label = "Prev")
        #self.panel.Bind(wx.EVT_BUTTON, self.OnPrev, prev_button)
        self.prev_buttons = (new_button, match_button, prev_button)

        unlink_button = wx.Button(self.panel, id=-1, label = "Unlink")
        #self.panel.Bind(wx.EVT_BUTTON, self.OnUnlink, unlink_button)
        relink_button = wx.Button(self.panel, id=-1, label = "Relink")
        #self.panel.Bind(wx.EVT_BUTTON, self.OnLink, relink_button)
        self.curr_buttons = (unlink_button, relink_button)

    def on_new(self, event):
        choose_dir_dialog = MDD.MultiDirDialog(self, title="Select folders to "
                                               "move")
        # Clicked ok on multi folder select
        if choose_dir_dialog.ShowModal() == wx.ID_OK:
            folders_list = choose_dir_dialog.GetPaths()
            # No folders selected
            if len(folders_list) == 0:
                self.no_folders(choose_dir_dialog)
            # Folders selected
            else:
                invalid_list, new_folders = [], []
                # Sort valid and invalid folders
                for folder in folders_list:
                    if folder[-1] in (":", "\\"):
                        invalid_list.append((folder, "Cannot add drive"))
                    else:
                        new_folders.append(folder)
                # If invalid folders, show error with list and give option to
                # cancel new link operation
                continue_op = wx.ID_OK
                if len(invalid_list) != 0:
                    continue_op = self.invalid_folders(choose_dir_dialog,
                                                       invalid_list)
                if len(new_folders) != 0 and continue_op == wx.ID_OK:
                    self.new_folders(new_folders)

    def no_folders(self, parent):
        none_dialog = wx.MessageDialog(parent, "No folders selected.",
                                       "No selection", wx.OK|wx.CENTRE)
        none_dialog.ShowModal()
        none_dialog.Destroy()

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

    def new_folders(self, new_folders):
        new_dir_dialog = wx.DirDialog(self, message = "Choose new location")
        new_links = []
        if new_dir_dialog.ShowModal() == wx.ID_OK:
            index, new_loc = 0, new_dir_dialog.GetPath()
            for folder in new_folders:
                self.prev_listCtrl.InsertStringItem(index, folder)
                self.prev_listCtrl.SetStringItem(index, 1, new_loc)
                new_links.append(self.symlink(folder, new_loc))
                index += 1
        new_dir_dialog.Destroy()
        self.SaveDataCSV(PREV_HISTORY_FILE, new_links)

    def OnMatch(self, event):
        dialog = wx.MessageDialog(self, "Moves to same location on another "\
                                  "drive", "Matching", wx.OK|wx.CENTRE)
        dialog.ShowModal()
        dialog.Destroy()

def symlink(self, old_path, new_loc):
    old_loc, folder_name = old_path.rsplit('\\', 1)
    new_path = new_loc + '\\' + folder_name
    print "Moving..."
    shutil.move(old_path, new_path)
    print "Moved."
    print "Symlinking..."
    kerneldll.CreateSymbolicLinkW(old_path, new_path, 1)
    print "Symlinked."
    return [folder_name, old_loc, new_loc]

def YesNoDialog(parent, question, caption = 'Yes or no?'):
    dlg = wx.MessageDialog(parent, question, caption, 
                           wx.YES|wx.NO|wx.ICON_QUESTION)
    answer = dlg.ShowModal()
    dlg.Destroy()
    return answer

def SaveDataCSV(file_name, data):
    with open(file_name, "ab") as file:
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
