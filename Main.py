import wx
import os

FRAME_TITLE = "Symlink Manager"
FRAME_SIZE = (700, 500)
FRAME_POS = (200,200)

class MainWindow(wx.Frame):
    def __init__(self):
        wx.Frame.__init__(self, None, wx.ID_ANY, FRAME_TITLE, size = FRAME_SIZE,
                          style = wx.DEFAULT_FRAME_STYLE)
        self.Position = FRAME_POS

        panel = wx.Panel(self) # wx.window that contains ctrls
        panel.BackgroundColour = (250,0,0)

        # Heading strings
        prev_heading = "Previous Links"
        curr_heading = "Current Links"

        # Create list controls
        prev_folder_listCtrl = FolderListCtrl(panel)
        curr_folder_listCtrl = FolderListCtrl(panel)

        # Create buttons
        match_button = wx.Button(panel, id=-1, label = "Match")
        new_button = wx.Button(panel, id=-1, label = "New")
        prev_button = wx.Button(panel, id=-1, label = "Prev")
        prev_buttons = (match_button, new_button, prev_button)

        unlink_button = wx.Button(panel, id=-1, label = "Unlink")
        relink_button = wx.Button(panel, id=-1, label = "Relink")
        curr_buttons = (unlink_button, relink_button)

        # Create column panels
        prev_panel = ColPanel(panel, prev_heading, prev_folder_listCtrl, prev_buttons)
        prev_panel.BackgroundColour = (0,255,0)

        curr_panel = ColPanel(panel, curr_heading, curr_folder_listCtrl, curr_buttons)
        curr_panel.BackgroundColour = (0,255,255)

        col_sizer = wx.BoxSizer(wx.HORIZONTAL) # Makes main column sizer
        col_sizer.Add((20,0)) # Adds blank space on left, 20 wide
        col_sizer.Add(prev_panel, proportion=1, flag=wx.EXPAND) # Adds first list panel
        col_sizer.Add((20,0)) # Adds blank space in middle
        col_sizer.Add(curr_panel, proportion=1, flag=wx.EXPAND) # Adds second list panel
        col_sizer.Add((20,0)) # Adds blank space on right

        panel.SetSizer(col_sizer)
        self.Layout()

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
    def __init__(self, parent):
        wx.ListCtrl.__init__(self, parent, size=(300,200))
        self.style = wx.LC_REPORT|wx.BORDER_SUNKEN
        self.InsertColumn(0, "Folder Name")
        self.InsertColumn(1, "Last Linked Path")
        self.SetBackgroundColour((255,255,255))

if __name__ == '__main__':
    app = wx.App()
    appFrame = MainWindow().Show()
    app.MainLoop()
