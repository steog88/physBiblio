#!/usr/bin/env python

import sys
from Queue import Queue
from PySide.QtCore import *
from PySide.QtGui  import *
import signal
import ast
import glob

try:
	from physbiblio.errors import pBErrorManager
	from physbiblio.database import *
	from physbiblio.export import pBExport
	import physbiblio.webimport.webInterf as webInt
	from physbiblio.cli import cli as physBiblioCLI
	from physbiblio.config import pbConfig
	from physbiblio.pdf import pBPDF
	from physbiblio.gui.DialogWindows import *
	from physbiblio.gui.BibWindows import *
	from physbiblio.gui.CatWindows import *
	from physbiblio.gui.ExpWindows import *
	from physbiblio.gui.inspireStatsGUI import *
	from physbiblio.gui.ProfilesManager import *
	from physbiblio.gui.ThreadElements import *
except ImportError:
	print("Could not find physbiblio and its contents: configure your PYTHONPATH!")
try:
	import physbiblio.gui.Resources_pyside
except ImportError:
	print("Missing Resources_pyside.py: Run script update_resources.sh")

class MainWindow(QMainWindow):
	def __init__(self):
		QMainWindow.__init__(self)
		availableWidth		= QDesktopWidget().availableGeometry().width()
		availableHeight		= QDesktopWidget().availableGeometry().height() 
		self.setWindowTitle('PhysBiblio')
		self.setGeometry(0, 0, availableWidth, availableHeight)#x,y of topleft corner, width, height
		self.setMinimumHeight(400)
		self.setMinimumWidth(600)
		self.myStatusBar = QStatusBar()
		self.createActions()
		self.createMenusAndToolBar()
		self.createMainLayout()
		self.setIcon()
		self.CreateStatusBar()
		self.lastAuthorStats = None

		#Catch Ctrl+C in shell
		signal.signal(signal.SIGINT, signal.SIG_DFL)
	
	def setIcon(self):
		appIcon=QIcon(':/images/icon.png')
		self.setWindowIcon(appIcon)
		
	def createActions(self):
		"""
		Create Qt actions used in GUI.
		"""
		self.profilesAct = QAction(QIcon(":/images/profiles.png"),
								"&Profiles", self,
								shortcut="Ctrl+P",
								statusTip="Manage profiles",
								triggered=self.manageProfiles)

		self.editProfilesAct = QAction(
								"&Edit profiles", self,
								shortcut="Ctrl+Alt+P",
								statusTip="Edit profiles",
								triggered=self.editProfiles)

		self.saveAct = QAction(QIcon(":/images/file-save.png"),
								"&Save database", self,
								shortcut="Ctrl+S",
								statusTip="Save the modifications",
								triggered=self.save)
								
		self.exportAct = QAction(QIcon(":/images/export.png"),
								"Ex&port last as *.bib", self,
								#shortcut="Ctrl+P",
								statusTip="Export last query as *.bib",
								triggered=self.export)
								
		self.exportAllAct = QAction(QIcon(":/images/export-table.png"),
								"Export &all as *.bib", self,
								shortcut="Ctrl+A",
								statusTip="Export complete bibliography as *.bib",
								triggered=self.exportAll)

		self.exportFileAct = QAction(#QIcon(":/images/export-table.png"),
								"Export for a *.&tex", self,
								shortcut="Ctrl+X",
								statusTip="Export as *.bib the bibliography needed to compile a .tex file",
								triggered=self.exportFile)

		self.exportUpdateAct = QAction(#QIcon(":/images/export-table.png"),
								"Update an existing *.&bib file", self,
								shortcut="Ctrl+Shift+X",
								statusTip="Read a *.bib file and update the existing elements inside it",
								triggered=self.exportUpdate)

		self.exitAct = QAction(QIcon(":/images/application-exit.png"),
								"E&xit", self,
								shortcut="Ctrl+Q",
								statusTip="Exit application",
								triggered=self.close)

		self.CatAct = QAction("&Categories", self,
								shortcut="Ctrl+C",
								statusTip="Manage Categories",
								triggered=self.categories)

		self.newCatAct = QAction("Ne&w Category", self,
								shortcut="Ctrl+Shift+C",
								statusTip="New Category",
								triggered=self.newCategory)

		self.ExpAct = QAction("&Experiments", self,
								shortcut="Ctrl+E",
								statusTip="List of Experiments",
								triggered=self.experimentList)

		self.newExpAct = QAction("&New Experiment", self,
								shortcut="Ctrl+Shift+E",
								statusTip="New Experiment",
								triggered=self.newExperiment)

		self.searchBibAct = QAction(QIcon(":/images/find.png"),
								"&Find Bibtex entries", self,
								shortcut="Ctrl+F",
								statusTip="Open the search dialog to filter the bibtex list",
								triggered=self.searchBiblio)

		self.searchReplaceAct = QAction(QIcon(":/images/edit-find-replace.png"),
								"&Search and replace bibtexs", self,
								shortcut="Ctrl+H",
								statusTip="Open the search&replace dialog",
								triggered=self.searchAndReplace)

		self.newBibAct = QAction(QIcon(":/images/file-add.png"),
								"New &Bib item", self,
								shortcut="Ctrl+N",
								statusTip="New bibliographic item",
								triggered=self.newBibtex)

		self.inspireLoadAndInsertAct = QAction("&Load from Inspires", self,
								shortcut="Ctrl+Shift+I",
								statusTip="Use Inspires to load and insert bibtex entries",
								triggered=self.inspireLoadAndInsert)

		self.inspireLoadAndInsertWithCatsAct = QAction("&Load from Inspires (ask categories)", self,
								shortcut="Ctrl+I",
								statusTip="Use Inspires to load and insert bibtex entries, then ask the categories for each",
								triggered=self.inspireLoadAndInsertWithCats)

		self.advImportAct = QAction("&Advanced Import", self,
								shortcut="Ctrl+Alt+I",
								statusTip="Open the advanced import window",
								triggered=self.advancedImport)

		self.updateAllBibtexsAct = QAction("&Update bibtexs", self,
								shortcut="Ctrl+U",
								statusTip="Update all the journal info of bibtexs",
								triggered=self.updateAllBibtexs)

		self.updateAllBibtexsAskAct = QAction("Update bibtexs (&personalized)", self,
								shortcut="Ctrl+Shift+U",
								statusTip="Update all the journal info of bibtexs, but with non-standard options (start from, force, ...)",
								triggered=self.updateAllBibtexsAsk)

		self.cleanAllBibtexsAct = QAction("&Clean bibtexs", self,
								shortcut="Ctrl+L",
								statusTip="Clean all the bibtexs",
								triggered=self.cleanAllBibtexs)

		self.cleanAllBibtexsAskAct = QAction("C&lean bibtexs (from ...)", self,
								shortcut="Ctrl+Shift+L",
								statusTip="Clean all the bibtexs, starting from a given one",
								triggered=self.cleanAllBibtexsAsk)

		self.authorStatsAct = QAction("&AuthorStats", self,
								shortcut="Ctrl+Shift+A",
								statusTip="Search publication and citation stats of an author from INSPIRES",
								triggered=self.authorStats)

		self.cliAct = QAction(QIcon(":/images/terminal.png"),
								"&CLI", self,
								shortcut="Ctrl+T",
								statusTip="CommandLine Interface",
								triggered=self.cli)

		self.configAct = QAction(QIcon(":/images/settings.png"),
								"Settin&gs", self,
								shortcut="Ctrl+Shift+S",
								statusTip="Save the settings",
								triggered=self.config)

		self.refreshAct = QAction(QIcon(":/images/refresh2.png"),
								"&Refresh current entries list", self,
								shortcut="Ctrl+R",
								statusTip="Refresh the current list of entries",
								triggered=self.refreshMainContent)

		self.reloadAct = QAction(QIcon(":/images/refresh.png"),
								"&Reload (reset) main table", self,
								shortcut="Ctrl+Shift+R",
								statusTip="Reload the list of bibtex entries",
								triggered=self.reloadMainContent)

		self.aboutAct = QAction(QIcon(":/images/help-about.png"),
								"&About", self,
								statusTip="Show About box",
								triggered=self.showAbout)

		self.dbstatsAct = QAction(QIcon(":/images/stats.png"),
								"&Database info", self,
								statusTip="Show some statistics about the current database",
								triggered=self.showDBStats)

		self.cleanSpareAct = QAction(
								"&Clean spare entries", self,
								statusTip="Remove spare entries from the connection tables.",
								triggered=self.cleanSpare)

	def closeEvent(self, event):
		if pBDB.checkUncommitted():
			if askYesNo("There may be unsaved changes to the database.\nDo you really want to exit?"):
				event.accept()
			else:
				event.ignore()
		elif pbConfig.params["askBeforeExit"] and not askYesNo("Do you really want to exit?"):
			event.ignore()
		else:
			event.accept()

	def createMenusAndToolBar(self):
		"""
		Create Qt menus.
		"""
		self.fileMenu = self.menuBar().addMenu("&File")
		self.fileMenu.addAction(self.saveAct)
		self.fileMenu.addSeparator()
		self.fileMenu.addAction(self.exportAct)
		self.fileMenu.addAction(self.exportFileAct)
		self.fileMenu.addAction(self.exportAllAct)
		self.fileMenu.addAction(self.exportUpdateAct)
		self.fileMenu.addSeparator()
		self.fileMenu.addAction(self.profilesAct)
		self.fileMenu.addAction(self.editProfilesAct)
		self.fileMenu.addAction(self.configAct)
		self.fileMenu.addSeparator()
		self.fileMenu.addAction(self.exitAct)

		self.bibMenu = self.menuBar().addMenu("&Bibliography")
		self.bibMenu.addAction(self.newBibAct)
		self.bibMenu.addAction(self.inspireLoadAndInsertWithCatsAct)
		self.bibMenu.addAction(self.inspireLoadAndInsertAct)
		self.bibMenu.addAction(self.advImportAct)
		self.bibMenu.addSeparator()
		self.bibMenu.addAction(self.cleanAllBibtexsAct)
		self.bibMenu.addAction(self.cleanAllBibtexsAskAct)
		self.bibMenu.addSeparator()
		self.bibMenu.addAction(self.updateAllBibtexsAct)
		self.bibMenu.addAction(self.updateAllBibtexsAskAct)
		self.bibMenu.addSeparator()
		self.bibMenu.addAction(self.searchBibAct)
		self.bibMenu.addAction(self.searchReplaceAct)
		self.bibMenu.addAction(self.refreshAct)
		self.bibMenu.addAction(self.reloadAct)

		self.menuBar().addSeparator()
		self.catMenu = self.menuBar().addMenu("&Categories")
		self.catMenu.addAction(self.CatAct)
		self.catMenu.addAction(self.newCatAct)
		
		self.menuBar().addSeparator()
		self.expMenu = self.menuBar().addMenu("&Experiments")
		self.expMenu.addAction(self.ExpAct)
		self.expMenu.addAction(self.newExpAct)
		
		self.menuBar().addSeparator()
		self.toolMenu = self.menuBar().addMenu("&Tools")
		self.toolMenu.addAction(self.cleanSpareAct)
		self.toolMenu.addSeparator()
		self.toolMenu.addAction(self.authorStatsAct)
		# self.toolMenu.addSeparator()
		# self.toolMenu.addAction(self.cliAct)
		#self.optionMenu.addAction(self.optionsAct)
		#self.optionMenu.addAction(self.plotOptionsAct)
		#self.optionMenu.addAction(self.configOptionsAct)

		self.menuBar().addSeparator()
		self.helpMenu = self.menuBar().addMenu("&Help")
		self.helpMenu.addAction(self.dbstatsAct)
		self.helpMenu.addAction(self.aboutAct)
		
		self.mainToolBar = self.addToolBar('Toolbar')
		self.mainToolBar.addAction(self.saveAct)
		self.mainToolBar.addSeparator()
		self.mainToolBar.addAction(self.newBibAct)
		self.mainToolBar.addAction(self.searchBibAct)
		self.mainToolBar.addAction(self.searchReplaceAct)
		self.mainToolBar.addAction(self.exportAct)
		self.mainToolBar.addAction(self.exportAllAct)
		self.mainToolBar.addSeparator()
		self.mainToolBar.addAction(self.refreshAct)
		self.mainToolBar.addAction(self.reloadAct)
		# self.mainToolBar.addAction(self.cliAct)
		self.mainToolBar.addSeparator()
		self.mainToolBar.addAction(self.configAct)
		self.mainToolBar.addAction(self.dbstatsAct)
		self.mainToolBar.addAction(self.aboutAct)
		self.mainToolBar.addSeparator()
		self.mainToolBar.addAction(self.exitAct)

	def createMainLayout(self):
		#will contain the list of bibtex entries
		self.bibtexList = bibtexList(self)
		self.bibtexList.setFrameShape(QFrame.StyledPanel)

		#will contain the bibtex code:
		self.bottomLeft = bibtexWindow(self)
		self.bottomLeft.setFrameShape(QFrame.StyledPanel)

		#will contain other info on the bibtex entry:
		self.bottomRight = bibtexInfo(self)
		self.bottomRight.setFrameShape(QFrame.StyledPanel)

		splitter = QSplitter(Qt.Vertical)
		splitter.addWidget(self.bibtexList)
		splitterBottom = QSplitter(Qt.Horizontal)
		splitterBottom.addWidget(self.bottomLeft)
		splitterBottom.addWidget(self.bottomRight)
		splitter.addWidget(splitterBottom)
		splitter.setStretchFactor(0,3)
		splitter.setStretchFactor(1,1)

		availableWidth		= QDesktopWidget().availableGeometry().width()
		availableHeight		= QDesktopWidget().availableGeometry().height()
		#splitterBottom.setMinimumHeight(0.2*availableHeight)
		#splitterBottom.setMaximumHeight(0.4*availableHeight)
		#splitter.setMinimumHeight(0.8*availableHeight)
		#splitter.setMaximumHeight(0.8*availableHeight)
		splitter.setGeometry(0, 0, availableWidth, availableHeight)

		self.setCentralWidget(splitter)
		#self.setLayout(hbox)
		#QtGui.QApplication.setStyle(QtGui.QStyleFactory.create('Cleanlooks'))

		#self.setWindowTitle('QtGui.QSplitter')
		#self.show()

	def refreshMainContent(self, bibs = None):
		"""delete previous table widget and create a new one, using last used query"""
		self.StatusBarMessage("Reloading main table...")
		self.bibtexList.recreateTable(pBDB.bibs.fetchFromLast().lastFetched)
		self.done()

	def reloadMainContent(self, bibs = None):
		"""delete previous table widget and create a new one"""
		self.StatusBarMessage("Reloading main table...")
		self.bibtexList.recreateTable(bibs)
		self.done()

	def manageProfiles(self):
		"""change profile"""
		profilesWin = selectProfiles(self)
		profilesWin.exec_()

	def editProfiles(self):
		editProf(self, self)

	def config(self):
		cfgWin = configWindow(self)
		cfgWin.exec_()
		if cfgWin.result:
			for q in cfgWin.textValues:
				s = "%s"%q[1].text()
				if pbConfig.params[q[0]] != s:
					pbConfig.params[q[0]] = s
			pbConfig.saveConfigFile()
			pbConfig.readConfigFile()
			self.reloadConfig()
			self.refreshMainContent()
			self.StatusBarMessage("Configuration saved")
		else:
			self.StatusBarMessage("Changes discarded")

	def reloadConfig(self):
		self.StatusBarMessage("Reloading configuration...")
		pBPDF.pdfApp = pbConfig.params["pdfApplication"]
		if pbConfig.params["pdfFolder"][0] == "/":
			pBPDF.pdfDir = pbConfig.params["pdfFolder"]
		else:
			pBPDF.pdfDir = os.path.join(os.path.split(os.path.abspath(sys.argv[0]))[0], pbConfig.params["pdfFolder"])
		pBView.webApp = pbConfig.params["webApplication"]
		self.bibtexList.reloadColumnContents()

	def showAbout(self):
		"""
		Function to show About Box
		"""
		QMessageBox.about(self, "About PhysBiblio",
			"PhysBiblio is a cross-platform tool for managing a LaTeX/BibTeX database. "+
			"It supports grouping, tagging and various different other functions.")

	def showDBStats(self):
		"""
		Function to show About Box
		"""
		dbStats()
		onlyfiles = len(list(glob.iglob("%s/*/*.pdf"%pBPDF.pdfDir)))
		QMessageBox.about(self, "PhysBiblio database statistics",
			"The PhysBiblio database currently contains the following number of records:\n"+
			"- {bibs} bibtex entries\n- {cats} categories\n- {exps} experiments,\n".format(**pBDB.stats)+
			"- {catBib} bibtex entries to categories connections\n- {catExp} experiment to categories connections\n- {bibExp} bibtex entries to experiment connections.\n\n".format(**pBDB.stats)+
			"The number of currently stored PDF files is %d."%onlyfiles)

	def _runInThread(self, thread_func, title, *args, **kwargs):
		def getDelKwargs(key):
			if key in kwargs.keys():
				tmp = kwargs.get(key)
				del kwargs[key]
				return tmp
			else:
				return None
		totStr = getDelKwargs("totStr")
		progrStr = getDelKwargs("progrStr")
		addMessage = getDelKwargs("addMessage")
		app = printText(title = title, totStr = totStr, progrStr = progrStr)

		outMessage = getDelKwargs("outMessage")
		stopFlag = getDelKwargs("stopFlag")
		minProgress = getDelKwargs("minProgress")
		if minProgress:
			app.progressBarMin(minProgress)
		queue = Queue()
		rec = MyReceiver(queue, self)
		rec.mysignal.connect(app.append_text)
		if addMessage:
			print addMessage
		thr = thread_func(queue, rec, *args, parent = self, **kwargs)

		self.connect(rec, SIGNAL("finished()"), rec.deleteLater)
		self.connect(thr, SIGNAL("finished()"), app.enableClose)
		self.connect(thr, SIGNAL("finished()"), thr.deleteLater)
		if stopFlag:
			self.connect(app, SIGNAL("stopped()"), thr.setStopFlag)

		sys.stdout = WriteStream(queue)
		thr.start()
		app.exec_()
		print("Closing...")
		sys.stdout = sys.__stdout__
		if outMessage:
			self.StatusBarMessage(outMessage)
		else:
			self.done()
		return thr, rec

	def cleanSpare(self):
		self.cS_thr, self.cSReceiver = self._runInThread(thread_cleanSpare, "Clean spare entries")

	def CreateStatusBar(self):
		"""
		Function to create Status Bar
		"""
		self.myStatusBar.showMessage('Ready', 0)
		self.setStatusBar(self.myStatusBar)
		
	def StatusBarMessage(self, message = "abc", time = 2000):
		print("[StatusBar] %s"%message)
		self.myStatusBar.showMessage(message, time)

	def save(self):
		if askYesNo("Do you really want to save?"):
			pBDB.commit()
			self.setWindowTitle("PhysBiblio")
			self.StatusBarMessage("Changes saved")
		else:
			self.StatusBarMessage("Nothing saved")
		
	def export(self):
		filename = askSaveFileName(self, title = "Where do you want to export the entries?", filter = "Bibtex (*.bib)")
		if filename != "":
			pBExport.exportLast(filename)
			self.StatusBarMessage("Last fetched entries exported into %s"%filename)
		else:
			self.StatusBarMessage("Empty filename given!")
	
	def exportSelection(self, entries):
		filename = askSaveFileName(self, title = "Where do you want to export the selected entries?", filter = "Bibtex (*.bib)")
		if filename != "":
			pBExport.exportSelected(filename, entries)
			self.StatusBarMessage("Current selection exported into %s"%filename)
		else:
			self.StatusBarMessage("Empty filename given!")

	def exportFile(self):
		outFName = askSaveFileName(self, title = "Where do you want to export the entries?", filter = "Bibtex (*.bib)")
		if outFName != "":
			texFile = askFileNames(self, title = "Which is/are the *.tex file(s) you want to compile?", filter = "Latex (*.tex)")
			if (type(texFile) is not list and texFile != "") or (type(texFile) is list and len(texFile)>0):
				self.exportTexBib_thr, self.exportTexBibReceiver = self._runInThread(
					thread_exportTexBib, "Exporting...",
					texFile, outFName,
					minProgress=0,  stopFlag = True, outMessage = "All entries saved into %s"%outFName)
			else:
				self.StatusBarMessage("Empty input filename/folder!")
		else:
			self.StatusBarMessage("Empty output filename!")

	def exportUpdate(self):
		filename = askSaveFileName(self, title = "File to update?", filter = "Bibtex (*.bib)")
		if filename != "":
			overwrite = askYesNo("Do you want to overwrite the existing .bib file?", "Overwrite")
			pBExport.updateExportedBib(filename, overwrite = overwrite)
			self.StatusBarMessage("File %s updated"%filename)
		else:
			self.StatusBarMessage("Empty output filename!")

	def exportAll(self):
		filename = askSaveFileName(self, title = "Where do you want to export the entries?", filter = "Bibtex (*.bib)")
		if filename != "":
			pBExport.exportAll(filename)
			self.StatusBarMessage("All entries saved into %s"%filename)
		else:
			self.StatusBarMessage("Empty output filename!")
	
	def categories(self):
		self.StatusBarMessage("categories triggered")
		catListWin = catsWindowList(self)
		catListWin.show()

	def newCategory(self):
		editCategory(self, self)
	
	def experimentList(self):
		self.StatusBarMessage("experiments triggered")
		expListWin = ExpWindowList(self)
		expListWin.show()

	def newExperiment(self):
		editExperiment(self, self)

	def newBibtex(self):
		editBibtex(self, self)

	def searchBiblio(self):
		newSearchWin = searchBibsWindow(self)
		newSearchWin.exec_()
		searchDict = {}
		if newSearchWin.result is True:
			searchDict["catExpOperator"] = newSearchWin.values["catExpOperator"]
			if len(newSearchWin.values["cats"]) > 0:
				searchDict["cats"] = {
					"id": newSearchWin.values["cats"],
					"operator": newSearchWin.values["catsOperator"].lower(),
				}
			if len(newSearchWin.values["exps"]) > 0:
				searchDict["exps"] = {
					"id": newSearchWin.values["exps"],
					"operator": newSearchWin.values["expsOperator"].lower(),
				}
			newSearchWin.getMarksValues()
			if len(newSearchWin.values["marks"]) > 0:
				if "any" in newSearchWin.values["marks"]:
					searchDict["marks"] = {"str": "", "operator": "!=", "connection": newSearchWin.values["marksConn"]}
				else:
					searchDict["marks"] = {"str": ", ".join(newSearchWin.values["marks"]), "operator": "like", "connection": newSearchWin.values["marksConn"]}
			newSearchWin.getTypeValues()
			if len(newSearchWin.values["type"]) > 0:
				for k in newSearchWin.values["type"]:
					searchDict[k] = {"str": "1", "operator": "=", "connection": newSearchWin.values["typeConn"]}
					print searchDict[k]
			for i, dic in enumerate(newSearchWin.textValues):
				k="%s#%d"%(dic["field"].currentText(), i)
				s = "%s"%dic["content"].text()
				op = "like" if "%s"%dic["operator"].currentText() == "contains" else "="
				if s.strip() != "":
					searchDict[k] = {"str": s, "operator": op, "connection": dic["logical"].currentText()}
			try:
				lim = int(newSearchWin.limitValue.text())
			except ValueError:
				lim = 50
			try:
				offs = int(newSearchWin.limitOffs.text())
			except ValueError:
				offs = 0
			noLim = pBDB.bibs.fetchFromDict(searchDict, limitOffset = offs).lastFetched
			lastFetched = pBDB.bibs.fetchFromDict(searchDict,
				limitTo = lim, limitOffset = offs
				).lastFetched
			if len(noLim) > len(lastFetched):
				infoMessage("Warning: more entries match the current search, showing only the first %d of %d.\nChange 'Max number of results' in the search form to see more."%(
					len(lastFetched), len(noLim)))
			self.reloadMainContent(lastFetched)

	def searchAndReplace(self):
		dialog = searchReplaceDialog(self)
		dialog.exec_()
		if dialog.result == True:
			if dialog.searchEdit.text().strip() == "":
				infoMessage("Empty search string!\nDoing nothing.")
				return
			changed = pBDB.bibs.replaceInBibtex(dialog.searchEdit.text(), dialog.replaceEdit.text())
			if len(changed) > 0:
				infoMessage("Elements changed:\n%s"%changed)
			self.reloadMainContent(pBDB.bibs.lastFetched)

	def cli(self):
		self.StatusBarMessage("Activating CLI!")
		infoMessage("Command Line Interface activated: switch to the terminal, please.", "CLI")
		physBiblioCLI()

	def updateAllBibtexsAsk(self):
		force = askYesNo("Do you want to force the update of already existing items?\n(Only regular articles not explicitely excluded will be considered)", "Force update:")
		text = askGenericText("Insert the ordinal number of the bibtex element from which you want to start the updates:", "Where do you want to start searchOAIUpdates from?", self)
		try:
			startFrom = int(text)
		except ValueError:
			if askYesNo("The text you inserted is not an integer. I will start from 0.\nDo you want to continue?", "Invalid entry"):
				startFrom = 0
			else:
				return False
		self.updateAllBibtexs(startFrom, force = force)

	def updateAllBibtexs(self, startFrom = 0, useEntries = None, force = False):
		self.StatusBarMessage("Starting update of bibtexs...")
		self.updateOAI_thr, self.uOAIReceiver = self._runInThread(
			thread_updateAllBibtexs, "Update Bibtexs",
			startFrom, useEntries = useEntries, force = force,
			totStr = "[DB] searchOAIUpdates will process ", progrStr = "%) - looking for update: ",
			minProgress = 0., stopFlag = True)

	def updateInspireInfo(self, bibkey):
		self.StatusBarMessage("Starting generic info update from Inspire...")
		self.updateII_thr, self.uIIReceiver = self._runInThread(
			thread_updateInspireInfo, "Update Info",
			bibkey,
			minProgress = 0., stopFlag = True)

	def authorStats(self):
		authorName = str(askGenericText("Insert the INSPIRE name of the author of which you want the publication and citation statistics:", "Author name?", self))
		if authorName is "":
			pBGUIErrorManager("[authorStats] empty name inserted! cannot proceed.", priority = 0)
			return False
		if "[" in authorName:
			try:
				authorName = ast.literal_eval(authorName.strip())
			except SyntaxError:
				pBGUIErrorManager("[authorStats] cannot recognize the list sintax. Missing quotes in the string?", traceback, priority = 1)
				return False
		self.StatusBarMessage("Starting computing author stats from INSPIRE...")

		self.authorStats_thr, self.aSReceiver = self._runInThread(
			thread_authorStats, "Author Stats",
			authorName,
			totStr = "[inspireStats] authorStats will process ", progrStr = "%) - looking for paper: ",
			minProgress = 0., stopFlag = True)

		if self.lastAuthorStats is None or len(self.lastAuthorStats["paLi"][0]) == 0:
			infoMessage("No results obtained. Maybe there was an error or you interrupted execution.")
			return False
		self.lastAuthorStats["figs"] = pBStats.plotStats(author = True)
		aSP = authorStatsPlots(self.lastAuthorStats["figs"], title = "Statistics for %s"%authorName, parent = self)
		aSP.show()
		self.done()

	def inspireLoadAndInsert(self, doReload = True):
		queryStr = askGenericText("Insert the query string you want to use for importing from InspireHEP:\n(It will be interpreted as a list, if possible)", "Query string?", self)
		if queryStr == "":
			pBGUIErrorManager("[inspireLoadAndInsert] empty string! cannot proceed.", priority = 0)
			return False
		self.loadedAndInserted = []
		self.StatusBarMessage("Starting import from INSPIRE...")
		if "," in queryStr:
			try:
				queryStr = ast.literal_eval("["+queryStr.strip()+"]")
			except SyntaxError:
				pBGUIErrorManager("[inspireLoadAndInsert] cannot recognize the list sintax. Missing quotes in the string?", priority = 1)
				return False

		self.inspireLoadAndInsert_thr, self.iLAIReceiver = self._runInThread(
			thread_loadAndInsert, "Import from Inspire",
			queryStr,
			totStr = "[DB] loadAndInsert will process ", progrStr = "%) - looking for string: ",
			minProgress = 0., stopFlag = True,
			addMessage = "[inspireLoadAndInsert] searching:\n%s"%queryStr)

		if self.loadedAndInserted is []:
			infoMessage("No results obtained. Maybe there was an error or you interrupted execution.")
			return False
		if doReload:
			self.reloadMainContent()
		return True

	def askCatsForEntries(self, entriesList):
		for entry in entriesList:
			selectCats = catsWindowList(parent = self, askCats = True, askForBib = entry)
			selectCats.exec_()
			if selectCats.result in ["Ok", "Exps"]:
				cats = self.selectedCats
				pBDB.catBib.insert(cats, entry)
				self.StatusBarMessage("categories for '%s' successfully inserted"%entry)
			if selectCats.result == "Exps":
				selectExps = ExpWindowList(parent = self, askExps = True, askForBib = entry)
				selectExps.exec_()
				if selectExps.result == "Ok":
					exps = self.selectedExps
					pBDB.bibExp.insert(entry, exps)
					self.StatusBarMessage("experiments for '%s' successfully inserted"%entry)

	def inspireLoadAndInsertWithCats(self):
		if self.inspireLoadAndInsert(doReload = False) and len(self.loadedAndInserted) > 0:
			self.askCatsForEntries(self.loadedAndInserted)
			self.reloadMainContent()

	def advancedImport(self):
		adIm = advImportDialog()
		adIm.exec_()
		method = adIm.comboMethod.currentText().lower()
		string = adIm.searchStr.text().strip()
		if adIm.result == True and string != "":
			cont = physBiblioWeb.webSearch[method].retrieveUrlAll(string)
			elements = bibtexparser.loads(cont).entries
			found = {}
			for el in elements:
				if el["ID"].strip() == "":
					pBErrorManager("[advancedImport] ERROR: impossible to insert an entry with empty bibkey!\n%s\n"%el["ID"])
				else:
					found[el["ID"]] = {"bibpars": el, "exist": len(pBDB.bibs.getByBibkey(el["ID"], saveQuery = False) ) > 0}
			if len(found) == 0:
				infoMessage("No results obtained.")
				return False

			selImpo = advImportSelect(found, self)
			selImpo.exec_()
			if selImpo.result == True:
				for ch in selImpo.checkBoxes:
					if not ch.isChecked():
						found.pop(ch.text())
				db = bibtexparser.bibdatabase.BibDatabase()
				inserted = []
				for key, el in found.items():
					db.entries = [el["bibpars"]]
					entry = pbWriter.write(db)
					data = pBDB.bibs.prepareInsert(entry)
					try:
						pBDB.bibs.insert(data)
					except:
						pBErrorManager("[advancedImport] failed in inserting entry %s\n"%key)
						continue
					try:
						if method == "inspire":
							eid = pBDB.bibs.updateInspireID(key)
							pBDB.bibs.updateInfoFromOAI(eid)
						elif method == "isbn":
							pBDB.bibs.setBook(key)
						print("[advancedImport] element successfully inserted.\n")
						inserted.append(key)
					except:
						pBErrorManager("[advancedImport] failed in completing info for entry %s\n"%key)
				self.StatusBarMessage("[advancedImport] entries successfully imported: %s"%inserted)
				if selImpo.askCats.isChecked():
					self.askCatsForEntries(inserted)
			self.reloadMainContent()
		else:
			return False

	def cleanAllBibtexsAsk(self):
		text = askGenericText("Insert the ordinal number of the bibtex element from which you want to start the cleaning:", "Where do you want to start cleanBibtexs from?", self)
		try:
			startFrom = int(text)
		except ValueError:
			if askYesNo("The text you inserted is not an integer. I will start from 0.\nDo you want to continue?", "Invalid entry"):
				startFrom = 0
			else:
				return False
		self.cleanAllBibtexs(startFrom)

	def cleanAllBibtexs(self, startFrom = 0, useEntries = None):
		self.StatusBarMessage("Starting cleaning of bibtexs...")
		self.cleanBibtexs_thr, self.cleanReceiver = self._runInThread(
			thread_cleanAllBibtexs, "Clean Bibtexs",
			startFrom, useEntries = useEntries,
			totStr = "[DB] cleanBibtexs will process ", progrStr = "%) - cleaning: ",
			minProgress = 0., stopFlag = True)

	def sendMessage(self, message):
		infoMessage(message)

	def done(self):
		self.StatusBarMessage("...done!")

if __name__=='__main__':
	try:
		myApp=QApplication(sys.argv)
		myWindow=MainWindow()
		myWindow.show()
		sys.exit(myApp.exec_())
	except NameError:
		print("NameError:",sys.exc_info()[1])
	except SystemExit:
		print("Closing main window...")
	except Exception:
		print(sys.exc_info()[1])