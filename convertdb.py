import sqlite3, os

PREV_HEADING = "Previous Links"
CURR_HEADING = "Current Links"

PREV_COLUMNS = None
CURR_COLUMNS = None

# sqlite tables
PREV_TABLE = "previous"
PREV_SQL_COLUMNS = "(original_name text, original_loc text, current_name text, link_loc text, date text)"
PREV_TABLE_DECLARATION = "%s %s" % (PREV_TABLE, PREV_SQL_COLUMNS)
CURR_TABLE = "current"
CURR_SQL_COLUMNS = "(original_name text, original_loc text, current_name text, link_loc text, date text)"
CURR_TABLE_DECLARATION = "%s %s" % (CURR_TABLE, CURR_SQL_COLUMNS)

LISTS = {
    "PREV": {"HEADING": PREV_HEADING, "COLUMNS": PREV_COLUMNS, "STATE": 0,
        "TABLE": PREV_TABLE, "TABLE_DECLARATION": PREV_TABLE_DECLARATION},
    "CURR": {"HEADING": CURR_HEADING, "COLUMNS": CURR_COLUMNS, "STATE": 1,
        "TABLE": CURR_TABLE, "TABLE_DECLARATION": CURR_TABLE_DECLARATION}
}

def make_proper_loc(improper_loc):
    if improper_loc[-1] != u'\\':
        return improper_loc + u'\\'
    return improper_loc

class Folder():
    def __init__(self, original_path, link_name=None, link_loc=None, link_state=-1, date=None):
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
        return self.link_loc + self.link_name

    def set_date(self):
        self.date = str(datetime.now())[:-7]


connection = sqlite3.connect("database.db")
cursor = connection.cursor()
connection2 = sqlite3.connect("new.db")
cursor2 = connection2.cursor()
for val in LISTS.values():
    cursor2.execute("create table if not exists %s" %
                         (val['TABLE_DECLARATION']))

cursor.execute("select * from current")
original_items = [Folder(os.path.join(row[1],row[0]), row[0], row[2], val['STATE'], row[3])
                  for row in cursor.fetchall()]

for folder in original_items:
	cursor2.execute("insert into current values "
                "('%s','%s','%s','%s','%s')" % (folder.original_name,
                folder.original_loc, folder.link_name, folder.link_loc,
                folder.date))
connection2.commit()