#!/usr/bin/env python
import sys
from PySide.QtCore import *
from PySide.QtGui  import *
import subprocess
import traceback

try:
	#from physbiblio.database import *
	#from physbiblio.export import pBExport
	#import physbiblio.webimport.webInterf as webInt
	#from physbiblio.cli import cli as physBiblioCLI
	from physbiblio.config import pbConfig
	from physbiblio.gui.CommonClasses import *
	from physbiblio.errors import pBErrorManager
	from physbiblio.database import pBDB
except ImportError:
	print("Could not find physbiblio and its contents: configure your PYTHONPATH!")
try:
	import physbiblio.gui.Resources_pyside
except ImportError:
	print("Missing Resources_pyside.py: Run script update_resources.sh")

def askYesNo(message, title = "Question"):
	reply = QMessageBox.question(None, title, message, QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
	if reply == QMessageBox.Yes:
		return True
	if reply == QMessageBox.No:
		return False

def askFileName(parent = None, title = "Filename to use:", filter = ""):
	reply = QFileDialog.getOpenFileName(parent, title, "", filter)
	return reply[0]

def askFileNames(parent = None, title = "Filename to use:", filter = ""):
	reply = QFileDialog.getOpenFileNames(parent, title, "", filter)
	return reply[0]

def askSaveFileName(parent = None, title = "Filename to use:", filter = ""):
	reply = QFileDialog.getSaveFileName(parent, title, "", filter, options = QFileDialog.DontConfirmOverwrite)
	return reply[0]

def askDirName(parent = None, title = "Directory to use:"):
	reply = QFileDialog.getExistingDirectory(parent, title, "", options=QFileDialog.ShowDirsOnly)
	return reply

def askGenericText(message, title, parent = None):
	reply = QInputDialog.getText(parent, title, message)
	return reply[0]

def infoMessage(message, title = "Information"):
	reply = QMessageBox.information(None, title, message)

class pBGUIErrorManager():
	def __init__(self, message, trcbk = None, priority = 2):
		message += "\n"
		pBErrorManager(message, trcbk, priority = priority)
		error = QMessageBox()
		if priority == 0:
			error.information(error, unicode("Warning"), unicode(message.replace('\n', '<br>')))
		elif priority == 1:
			error.warning(error, unicode("Error"), unicode(message.replace('\n', '<br>')))
		else:
			error.critical(error, unicode("Critical error"), unicode(message.replace('\n', '<br>')))

def excepthook(cls, exception, trcbk):
	text = "".join(traceback.format_exception(cls, exception, trcbk))
	pBGUIErrorManager(text)

sys.excepthook = excepthook

class configEditColumns(QDialog):
	def __init__(self, parent = None):
		super(configEditColumns, self).__init__(parent)
		self.excludeCols = ["crossref", "bibtex", "exp_paper", "lecture", "phd_thesis", "review", "proceeding", "book", "noUpdate"]
		self.moreCols = ["title", "author", "journal", "volume", "pages", "primaryclass", "booktitle", "reportnumber"]
		self.initUI()

	def onCancel(self):
		self.result	= False
		self.close()

	def onOk(self):
		self.result = True
		self.selected = []
		for row in range(self.listSel.rowCount()):
			self.selected.append(self.listSel.item(row, 0).text())
		self.close()

	def initUI(self):
		self.layout = QGridLayout()
		self.setLayout(self.layout)

		self.listAll = MyDDTableWidget("Available columns")
		self.listSel = MyDDTableWidget("Selected columns")
		self.layout.addWidget(QLabel("Drag and drop items to order visible columns"), 0, 0, 1, 2)
		self.layout.addWidget(self.listAll, 1, 0)
		self.layout.addWidget(self.listSel, 1, 1)

		self.allItems = pBDB.descriptions["entries"].keys() + self.moreCols
		self.selItems = pbConfig.params["bibtexListColumns"]
		i=0
		for col in self.allItems:
			if col not in self.selItems and col not in self.excludeCols:
				item = QTableWidgetItem(col)
				self.listAll.insertRow(i)
				self.listAll.setItem(i, 0, item)
				i += 1
		for i, col in enumerate(self.selItems):
			item = QTableWidgetItem(col)
			self.listSel.insertRow(i)
			self.listSel.setItem(i, 0, item)

		self.acceptButton = QPushButton('OK', self)
		self.acceptButton.clicked.connect(self.onOk)
		self.layout.addWidget(self.acceptButton, 2, 0)

		# cancel button
		self.cancelButton = QPushButton('Cancel', self)
		self.cancelButton.clicked.connect(self.onCancel)
		self.cancelButton.setAutoDefault(True)
		self.layout.addWidget(self.cancelButton, 2, 1)

class configWindow(QDialog):
	"""create a window for editing the configuration settings"""
	def __init__(self, parent = None):
		super(configWindow, self).__init__(parent)
		self.textValues = []
		self.initUI()

	def onCancel(self):
		self.result	= False
		self.close()

	def onOk(self):
		self.result	= True
		self.close()

	def editColumns(self):
		ix = pbConfig.paramOrder.index("bibtexListColumns")
		window = configEditColumns(self)
		window.exec_()
		if window.result:
			columns = window.selected
			self.textValues[ix][1].setText(str(columns))

	def initUI(self):
		self.setWindowTitle('Configuration')

		grid = QGridLayout()
		grid.setSpacing(1)

		i = 0
		for k in pbConfig.paramOrder:
			i += 1
			val = pbConfig.params[k] if type(pbConfig.params[k]) is str else str(pbConfig.params[k])
			grid.addWidget(QLabel("%s (<i>%s</i>)"%(pbConfig.descriptions[k], k)), i-1, 0, 1, 2)
			#grid.addWidget(QLabel("(%s)"%pbConfig.descriptions[k]), i-1, 1)
			if k == "bibtexListColumns":
				self.textValues.append([k, QPushButton(val)])
				self.textValues[-1][1].clicked.connect(self.editColumns)
			else:
				self.textValues.append([k, QLineEdit(val)])
			grid.addWidget(self.textValues[i-1][1], i-1, 2, 1, 2)

		# OK button
		self.acceptButton = QPushButton('OK', self)
		self.acceptButton.clicked.connect(self.onOk)
		#width = self.acceptButton.fontMetrics().boundingRect('OK').width() + 7
		#self.acceptButton.setMaximumWidth(width)
		grid.addWidget(self.acceptButton, i, 0)

		# cancel button
		self.cancelButton = QPushButton('Cancel', self)
		self.cancelButton.clicked.connect(self.onCancel)
		self.cancelButton.setAutoDefault(True)
		#width = self.cancelButton.fontMetrics().boundingRect('Cancel').width() + 7
		#self.cancelButton.setMaximumWidth(width)
		grid.addWidget(self.cancelButton, i, 1)

		self.setGeometry(100,100,1000, 30*i)
		self.setLayout(grid)

		qr = self.frameGeometry()
		cp = QDesktopWidget().availableGeometry().center()
		qr.moveCenter(cp)
		self.move(qr.topLeft())

class askAction(QDialog):
	"""create a window for asking an action: modify, delete, view...?"""
	def __init__(self, parent = None):
		super(askAction, self).__init__(parent)
		self.message = None
		self.possibleActions = [
			["Modify", self.onModify],
			["Delete", self.onDelete]
			]

	def keyPressEvent(self, e):		
		if e.key() == Qt.Key_Escape:
			self.close()

	def onCancel(self):
		self.result	= False
		self.close()

	def onModify(self):
		self.result = "modify"
		self.close()

	def onDelete(self):
		self.result = "delete"
		self.close()

	def initUI(self):
		self.setWindowTitle('Select action')

		grid = QGridLayout()
		grid.setSpacing(1)

		i = 0
		if self.message is not None:
			grid.addWidget(QLabel("%s"%self.message), 0, 0)
			i += 1

		for act in self.possibleActions:
			i += 1
			button = QPushButton(act[0], self)
			button.clicked.connect(act[1])
			grid.addWidget(button, i, 0)

		# cancel button
		self.cancelButton = QPushButton('Cancel', self)
		self.cancelButton.clicked.connect(self.onCancel)
		self.cancelButton.setAutoDefault(True)
		grid.addWidget(self.cancelButton, i+1, 0)

		self.setGeometry(100,100,300, 30*i)
		self.setLayout(grid)

		qr = self.frameGeometry()
		cp = QDesktopWidget().availableGeometry().center()
		qr.moveCenter(cp)
		self.move(qr.topLeft())

class printText(QDialog):
	"""create a window for printing text of command line output"""
	stopped = Signal()

	def __init__(self, parent = None, title = "", progressBar = True, totStr = None, progrStr = None):
		super(printText, self).__init__(parent)
		self.message = None
		if title != "":
			self.title = title
		else:
			self.title = "Redirect print"
		self.setProgressBar = progressBar
		self._want_to_close = False
		self.totString = totStr if totStr is not None else "emptyString"
		self.progressString = progrStr if progrStr is not None else "emptyString"
		self.initUI()

	def closeEvent(self, evnt):
		if self._want_to_close:
			super(printText, self).closeEvent(evnt)
		else:
			evnt.ignore()
			#self.setWindowState(QtCore.Qt.WindowMinimized)

	def initUI(self):
		self.setWindowTitle(self.title)

		grid = QGridLayout()
		grid.setSpacing(1)

		i = 0
		if self.message is not None:
			grid.addWidget(QLabel("%s"%self.message), 0, 0)
			i += 1

		#main text
		self.textEdit = QTextEdit()
		grid.addWidget(self.textEdit)

		if self.setProgressBar:
			self.progressBar = QProgressBar(self)
			grid.addWidget(self.progressBar)

		# cancel button...should learn how to connect it with a thread kill
		self.cancelButton = QPushButton('Stop', self)
		self.cancelButton.clicked.connect(self.stopExec)
		self.cancelButton.setAutoDefault(True)
		grid.addWidget(self.cancelButton)
		self.closeButton = QPushButton('Close', self)
		self.closeButton.clicked.connect(self.reject)
		self.closeButton.setDisabled(True)
		grid.addWidget(self.closeButton)

		self.setGeometry(100,100,600, 600)
		self.setLayout(grid)

		qr = self.frameGeometry()
		cp = QDesktopWidget().availableGeometry().center()
		qr.moveCenter(cp)
		self.move(qr.topLeft())

	def append_text(self,text):
		if self.setProgressBar:
			if self.totString in text:
				tot = [int(s) for s in text.split() if s.isdigit()][0]
				self.progressBarMax(tot)
			elif self.progressString in text:
				curr = [int(s) for s in text.split() if s.isdigit()][0]
				self.progressBar.setValue(curr)
		self.textEdit.moveCursor(QTextCursor.End)
		self.textEdit.insertPlainText( text )

	def progressBarMin(self, minimum):
		if self.setProgressBar:
			self.progressBar.setMinimum(minimum)

	def progressBarMax(self, maximum):
		if self.setProgressBar:
			self.progressBar.setMaximum(maximum)

	def stopExec(self):
		self.cancelButton.setDisabled(True)
		self.stopped.emit()

	def enableClose(self):
		self._want_to_close = True
		self.closeButton.setEnabled(True)

class searchReplaceDialog(QDialog):
	"""create a window for search and replace"""
	def __init__(self, parent = None):
		super(searchReplaceDialog, self).__init__(parent)
		self.initUI()

	def onCancel(self):
		self.result	= False
		self.close()

	def onOk(self):
		self.result	= True
		self.close()

	def initUI(self):
		self.setWindowTitle('Search and replace')

		grid = QGridLayout()
		grid.setSpacing(1)

		#search
		grid.addWidget(QLabel("Search: "), 0, 0)
		self.searchEdit = QLineEdit("")
		grid.addWidget(self.searchEdit, 0, 1)

		#replace
		grid.addWidget(QLabel("Replace with: "), 1, 0)
		self.replaceEdit = QLineEdit("")
		grid.addWidget(self.replaceEdit, 1, 1)

		# OK button
		self.acceptButton = QPushButton('OK', self)
		self.acceptButton.clicked.connect(self.onOk)
		grid.addWidget(self.acceptButton, 2, 0)

		# cancel button
		self.cancelButton = QPushButton('Cancel', self)
		self.cancelButton.clicked.connect(self.onCancel)
		self.cancelButton.setAutoDefault(True)
		grid.addWidget(self.cancelButton, 2, 1)

		self.setGeometry(100,100,400, 100)
		self.setLayout(grid)

		qr = self.frameGeometry()
		cp = QDesktopWidget().availableGeometry().center()
		qr.moveCenter(cp)
		self.move(qr.topLeft())

class advImportDialog(QDialog):
	"""create a window for the advanced import"""
	def __init__(self, parent = None):
		super(advImportDialog, self).__init__(parent)
		self.initUI()

	def onCancel(self):
		self.result	= False
		self.close()

	def onOk(self):
		self.result	= True
		self.close()

	def initUI(self):
		self.setWindowTitle('Advanced import')

		grid = QGridLayout()
		grid.setSpacing(1)

		##search
		grid.addWidget(QLabel("Select method: "), 0, 0)
		self.comboMethod = MyComboBox(self,
			["Inspire", "arXiv", "DOI", "ISBN"],
			current = "Inspire")
		grid.addWidget(self.comboMethod, 0, 1)

		grid.addWidget(QLabel("Search string: "), 1, 0)
		self.searchStr = QLineEdit("")
		grid.addWidget(self.searchStr, 1, 1)

		# OK button
		self.acceptButton = QPushButton('OK', self)
		self.acceptButton.clicked.connect(self.onOk)
		grid.addWidget(self.acceptButton, 2, 0)

		# cancel button
		self.cancelButton = QPushButton('Cancel', self)
		self.cancelButton.clicked.connect(self.onCancel)
		self.cancelButton.setAutoDefault(True)
		grid.addWidget(self.cancelButton, 2, 1)

		self.setGeometry(100,100,400, 100)
		self.setLayout(grid)
		self.searchStr.setFocus()

		qr = self.frameGeometry()
		cp = QDesktopWidget().availableGeometry().center()
		qr.moveCenter(cp)
		self.move(qr.topLeft())

class advImportSelect(QDialog):
	"""create a window for the advanced import"""
	def __init__(self, bibs=[], parent = None):
		super(advImportSelect, self).__init__(parent)
		self.bibs = bibs
		self.oneNew = False
		self.checkBoxes = []
		self.initUI()

	def onCancel(self):
		self.result	= False
		self.close()

	def onOk(self):
		self.result	= True
		self.close()

	def initUI(self):
		self.setWindowTitle('Advanced import - results')

		grid = QGridLayout()
		grid.setSpacing(1)

		grid.addWidget(QLabel("This is the list of elements found.\nSelect the ones that you want to import:\n"), 0, 0, 1, 2)
		##search
		i = 0
		for bk, elDic in self.bibs.items():
			el = elDic["bibpars"]
			if elDic["exist"] is False:
				self.checkBoxes.append(QCheckBox(bk, self))
				self.checkBoxes[i].toggle()
				grid.addWidget(self.checkBoxes[i], i+1, 0)
				try:
					title = el["title"]
				except:
					title = "Title not found"
				try:
					authors = el["author"]
				except:
					authors = "Authors not found"
				try:
					arxiv = el["arxiv"]
				except:
					try:
						arxiv = el["eprint"]
					except:
						arxiv = "arXiv number not found"
				grid.addWidget(QLabel("%s\n%s\n%s"%(title, authors, arxiv)), i+1, 1)
				self.oneNew = True
			else:
				self.checkBoxes.append(QCheckBox(bk, self))
				self.checkBoxes[i].setDisabled(True)
				grid.addWidget(self.checkBoxes[i], i+1, 0)
				grid.addWidget(QLabel("Already existing"), i+1, 1)
			i += 1

		i += 2
		grid.addWidget(QLabel("\n"), i-1, 1)
		if self.oneNew:
			grid.addWidget(QLabel("Ask categories at the end?"), i, 1)
			self.askCats = QCheckBox("", self)
			self.askCats.toggle()
			grid.addWidget(self.askCats, i, 0)

			# OK button
			self.acceptButton = QPushButton('OK', self)
			self.acceptButton.clicked.connect(self.onOk)
			grid.addWidget(self.acceptButton, i+1, 0)

		# cancel button
		self.cancelButton = QPushButton('Cancel', self)
		self.cancelButton.clicked.connect(self.onCancel)
		self.cancelButton.setAutoDefault(True)
		grid.addWidget(self.cancelButton, i+1, 1)

		self.setGeometry(100,100,400, 100)
		self.setLayout(grid)

		qr = self.frameGeometry()
		cp = QDesktopWidget().availableGeometry().center()
		qr.moveCenter(cp)
		self.move(qr.topLeft())