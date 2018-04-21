#!/usr/bin/env python
"""
Main file for the PhysBiblio application, a bibliography manager written in Python.

This file is part of the PhysBiblio package.
"""

import sys, traceback
import datetime

from PySide.QtGui import QApplication

try:
	from physbiblio.database import pBDB
	from physbiblio.errors import pBLogger
	from physbiblio.gui.MainWindow import MainWindow
except ImportError:
    print("Could not find physbiblio and its contents: configure your PYTHONPATH!")
    raise

def TorF(s):
	"""Get a True or False value from a command line option"""
	if s.lower() == "t" or s == 1 or s.lower() == "true":
		return True
	elif s.lower() == "f" or s == 0 or s.lower() == "false":
		return True
	else:
		return None

def call_clean(arguments):
	startFrom = arguments[0] if len(arguments) > 0 else 0
	pBDB.bibs.cleanBibtexs(startFrom = startFrom)
	pBDB.commit()
	exit()

def call_cli():
	from physbiblio.cli import cli as physBiblioCLI
	physBiblioCLI()
	exit()

def call_export(arguments):
	from physbiblio.export import pBExport
	if len(arguments) < 1:
		print("\nWrong usage of command line command 'export': mandatory argument 'fname' is missing.\n")
		exit()
	fname = arguments[0]
	pBExport.exportAll(fname)
	exit()

def call_tex(arguments):
	from physbiblio.export import pBExport
	if len(arguments) < 2:
		print("\nWrong usage of command line command 'tex': mandatory arguments are missing. Please use:")
		print("`physbiblio.py tex '/folder/where/tex/files/are/' 'name_of_output.bib' [overwrite [autosave]]`")
		print("(the optional arguments overwrite and autosave may be 1,T,t,True,true for True or 0,F,f,False,false for False. Default: overwrite = False, autosave = True)\n")
		exit()
	texFiles = arguments[0]
	bibFile = arguments[1]
	overwrite = TorF(arguments[2]) if len(arguments) > 2 else False
	autosave = TorF(arguments[3]) if len(arguments) > 3 else True
	if overwrite is None or autosave is None:
		print("\nInvalid value for overwrite or autosave. You may use 1,T,t,True,true for True or 0,F,f,False,false for False.\n")
	pBExport.exportForTexFile(texFiles, bibFile, overwrite = overwrite, autosave = autosave)
	exit()

def call_update(arguments):
	startFrom = int(arguments[0]) if len(arguments) > 0 else 0
	force = TorF(arguments[1]) if len(arguments) > 1 else False
	pBDB.bibs.searchOAIUpdates(startFrom = startFrom, force = force)
	pBDB.commit()
	exit()

def call_oaiDates(date1, date2):
	pBDB.bibs.getDailyInfoFromOAI(date1, date2)
	pBDB.commit()
	exit()

if __name__=='__main__':
	try:
		command = None
		dateLast = datetime.date.today().strftime("%Y-%m-%d")
		if len(sys.argv) > 1:
			command = sys.argv[1].lower()
		if command == "help":
			print("\nAvailable command line options:")
			print("* help: print this text;")
			print("* clean: parse and clean all the bibtex entries in the database;")
			print("* cli: open a command line where to directly run PhysBiblio functions;")
			print("* daily: retrieve records changed in the day from InspireOAI and update entries;")
			print("* export: export all the DB entries in a *.bib file;")
			print("* tex: read .tex file(s) and create a *.bib file with the cited bibtexs;")
			print("* update: use INSPIRE to update the information in the database;")
			print("* weekly: retrieve records changed in the week from InspireOAI and update entries.")
			print("")
			exit()
		elif command == "clean":
			call_clean(sys.argv[2:])
		elif command == "cli":
			call_cli()
		elif command == "daily":
			date1 = (datetime.date.today() - datetime.timedelta(1)).strftime("%Y-%m-%d")
			call_oaiDates(date1, dateLast)
		elif command == "export":
			call_export(sys.argv[2:])
		elif command == "tex":
			call_tex(sys.argv[2:])
		elif command == "update":
			call_update(sys.argv[2:])
		elif command == "weekly":
			date1 = (datetime.date.today() - datetime.timedelta(7)).strftime("%Y-%m-%d")
			call_oaiDates(date1, dateLast)

		app = QApplication(sys.argv)
		mainWin = MainWindow()
		mainWin.show()
		mainWin.raise_()
		sys.exit(app.exec_())
	except NameError:
		pBLogger.critical("NameError:", exc_info = True)
	except SystemExit:
		pBDB.closeDB()
		pBLogger.info("Closing main window...")
	except Exception as e:
		pBLogger.critical(str(e), exc_info = True)
