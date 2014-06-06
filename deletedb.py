import os
name = "database.db"
if os.path.exists(name):
	if os.path.isfile(name):
		if input("Delete symlink database? (type delete): ") == "delete":
			try:
				os.remove("database.db")
			except OSError:
				print("Could not delete database.")
	else:
		print("Database must be file.")
else:
	print("Database does not exist.")
input()