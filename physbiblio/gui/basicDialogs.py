"""
Module with the classes and functions that manage many generic simple dialog windows of the PhysBiblio application.

This file is part of the physbiblio package.
"""
import sys
from PySide2.QtCore import Qt, Signal
from PySide2.QtGui import QTextCursor
from PySide2.QtWidgets import QCheckBox, QDesktopWidget, QDialog, QFileDialog, QGridLayout, QInputDialog, QLabel, QMessageBox, QProgressBar, QPushButton, QTableWidgetItem, QTextEdit
import traceback

if sys.version_info[0] < 3:
	from StringIO import StringIO
else:
	from io import StringIO

try:
	from physbiblio.config import pbConfig
	from physbiblio.gui.commonClasses import *
	from physbiblio.errors import pBLogger, pBErrorManager
	from physbiblio.database import pBDB
	from physbiblio.webimport.webInterf import physBiblioWeb
	import physbiblio.gui.resourcesPyside2
except ImportError:
	print("Could not find physbiblio and its contents: configure your PYTHONPATH!")

def askYesNo(message, title = "Question", testing = False):
	"""
	Uses `QMessageBox` to ask "Yes" or "No" for a given question.

	Parameters:
		message: the question to be displayed
		title: the window title
		testing (boolean, optional, default False): when doing tests, interrupt the execution before `exec_` is run and return the `QMessageBox` object and the two buttons.

	Output:
		if testing is True, return the `QMessageBox` object and the "Yes" and "No" buttons
		if testing is False, return True if the "Yes" button has been clicked, False otherwise
	"""
	mbox = QMessageBox(QMessageBox.Question, title, message)
	yesButton = mbox.addButton(QMessageBox.Yes)
	noButton = mbox.addButton(QMessageBox.No)
	mbox.setDefaultButton(noButton)
	if testing:
		return mbox, yesButton, noButton
	mbox.exec_()
	if mbox.clickedButton() == yesButton:
		return True
	else:
		return False

def infoMessage(message, title = "Information", testing = False):
	"""
	Uses `QMessageBox` to show a simple message.

	Parameters:
		message: the question to be displayed
		title: the window title
		testing (boolean, optional, default False): when doing tests, interrupt the execution before `exec_` is run and return the `QMessageBox` object

	Output:
		if testing is True, return the `QMessageBox` object
	"""
	mbox = QMessageBox(QMessageBox.Information, title, message)
	if testing:
		return mbox
	mbox.exec_()

def askGenericText(message, title, parent = None, testing = False):
	"""
	Uses `QInputDialog` to ask a text answer for a given question.

	Parameters:
		message: the question to be displayed
		title: the window title
		parent (optional, default None): the parent of the window
		testing (boolean, optional, default False): when doing tests, interrupt the execution before `exec_` is run and return the `QInputDialog` object

	Output:
		if testing is True, return the `QInputDialog` object
		if testing is False, return a tuple containing the text as first element and True/False (depending if the user selected "Ok" or "Cancel") as the second element
	"""
	dialog = QInputDialog(parent)
	dialog.setInputMode(QInputDialog.TextInput)
	dialog.setWindowTitle(title)
	dialog.setLabelText(message)
	if testing:
		return dialog
	out = dialog.exec_()
	return dialog.textValue(), out

def askFileName(parent = None, title = "Filename to use:", filter = "", dir = "", testing = False):
	"""
	Uses `QFileDialog` to ask the name of a single, existing file

	Parameters (all optional):
		parent (default None): the parent of the window
		title: the window title
		filter: the filter to be used when displaying files
		dir: the initial directory
		testing (boolean, default False): when doing tests, interrupt the execution before `exec_` is run and return the `QFileDialog` object

	Output:
		if testing is True, return the `QFileDialog` object
		if testing is False, return the filename or an empty string depending if the user selected "Ok" or "Cancel"
	"""
	dialog = QFileDialog(parent, title, dir, filter)
	dialog.setFileMode(QFileDialog.ExistingFile)
	if testing:
		return dialog
	if dialog.exec_():
		fileNames = dialog.selectedFiles()
		return fileNames[0]
	else:
		return ""

def askFileNames(parent = None, title = "Filename to use:", filter = "", dir = "", testing = False):
	"""
	Uses `QFileDialog` to ask the names of a set of existing files

	Parameters (all optional):
		parent (default None): the parent of the window
		title: the window title
		filter: the filter to be used when displaying files
		dir: the initial directory
		testing (boolean, default False): when doing tests, interrupt the execution before `exec_` is run and return the `QFileDialog` object

	Output:
		if testing is True, return the `QFileDialog` object
		if testing is False, return the filenames list or an empty list depending if the user selected "Ok" or "Cancel"
	"""
	dialog = QFileDialog(parent, title, dir, filter)
	dialog.setFileMode(QFileDialog.ExistingFiles)
	dialog.setOption(QFileDialog.DontConfirmOverwrite, True)
	if testing:
		return dialog
	if dialog.exec_():
		fileNames = dialog.selectedFiles()
		return fileNames
	else:
		return []

def askSaveFileName(parent = None, title = "Filename to use:", filter = "", dir = "", testing = False):
	"""
	Uses `QFileDialog` to ask the names of a single file where something will be saved (the file may not exist)

	Parameters (all optional):
		parent (default None): the parent of the window
		title: the window title
		filter: the filter to be used when displaying files
		dir: the initial directory
		testing (boolean, default False): when doing tests, interrupt the execution before `exec_` is run and return the `QFileDialog` object

	Output:
		if testing is True, return the `QFileDialog` object
		if testing is False, return the filename or an empty string depending if the user selected "Ok" or "Cancel"
	"""
	dialog = QFileDialog(parent, title, dir, filter)
	dialog.setFileMode(QFileDialog.AnyFile)
	dialog.setOption(QFileDialog.DontConfirmOverwrite, True)
	if testing:
		return dialog
	if dialog.exec_():
		fileNames = dialog.selectedFiles()
		return fileNames[0]
	else:
		return ""

def askDirName(parent = None, title = "Directory to use:", dir = "", testing = False):
	"""
	Uses `QFileDialog` to ask the names of a single directory

	Parameters (all optional):
		parent (default None): the parent of the window
		title: the window title
		dir: the initial directory
		testing (boolean, default False): when doing tests, interrupt the execution before `exec_` is run and return the `QFileDialog` object

	Output:
		if testing is True, return the `QFileDialog` object
		if testing is False, return the directory name or an empty string depending if the user selected "Ok" or "Cancel"
	"""
	dialog = QFileDialog(parent, title, dir)
	dialog.setFileMode(QFileDialog.Directory)
	dialog.setOption(QFileDialog.ShowDirsOnly, True)
	if testing:
		return dialog
	if dialog.exec_():
		fileNames = dialog.selectedFiles()
		return fileNames[0]
	else:
		return ""