#!/usr/bin/env python
import sys
from PySide.QtCore import *
from PySide.QtGui  import *
import subprocess

try:
	from physbiblio.database import pBDB
	from physbiblio.config import pbConfig
	from physbiblio.gui.DialogWindows import *
	from physbiblio.gui.CommonClasses import *
	from physbiblio.pdf import pBPDF
	from physbiblio.view import pBView
	from physbiblio.gui.ThreadElements import *
	from physbiblio.gui.CatWindows import *
	from physbiblio.gui.ExpWindows import *
	from physbiblio.gui.marks import *
except ImportError:
	print("Could not find physbiblio and its contents: configure your PYTHONPATH!")
try:
	import physbiblio.gui.Resources_pyside
except ImportError:
	print("Missing Resources_pyside.py: Run script update_resources.sh")

convertType = {
	"review":  "Review",
	"proceeding":  "Proceeding",
	"book": "Book",
	"phd_thesis": "PhD thesis",
	"lecture": "Lecture",
	"exp_paper": "Experimental paper",
}

def writeBibtexInfo(entry):
	infoText = ""
	for t in convertType.keys():
		if entry[t] == 1:
			infoText += "(%s) "%convertType[t]
	infoText += "<u>%s</u>  (use with '<u>\cite{%s}</u>')<br/>"%(entry["bibkey"], entry["bibkey"])
	try:
		infoText += "<b>%s</b><br/>%s<br/>"%(entry["bibtexDict"]["author"], entry["bibtexDict"]["title"])
	except KeyError:
		pass
	try:
		infoText +=  "<i>%s %s (%s) %s</i><br/>"%(
			entry["bibtexDict"]["journal"],
			entry["bibtexDict"]["volume"],
			entry["bibtexDict"]["year"],
			entry["bibtexDict"]["pages"])
	except KeyError:
		pass
	infoText += "<br/>"
	for k in ["isbn", "doi", "arxiv", "ads", "inspire"]:
		try:
			infoText += "%s: <u>%s</u><br/>"%(pBDB.descriptions["entries"][k], entry[k]) if entry[k] is not None else ""
		except KeyError:
			pass
	cats = pBDB.cats.getByEntry(entry["bibkey"])
	infoText += "<br/>Categories: <i>%s</i>"%(", ".join([c["name"] for c in cats]) if len(cats) > 0 else "None")
	exps = pBDB.exps.getByEntry(entry["bibkey"])
	infoText += "<br/>Experiments: <i>%s</i>"%(", ".join([e["name"] for e in exps]) if len(exps) > 0 else "None")
	return infoText

def editBibtex(parent, statusBarObject, editKey = None):
	if editKey is not None:
		edit = pBDB.bibs.getByKey(editKey, saveQuery = False)[0]
	else:
		edit = None
	newBibWin = editBibtexEntry(parent, bib = edit)
	newBibWin.exec_()
	data = {}
	if newBibWin.result is True:
		for k, v in newBibWin.textValues.items():
			try:
				s = "%s"%v.text()
			except AttributeError:
				s = "%s"%v.toPlainText()
			data[k] = s
		for k, v in newBibWin.checkValues.items():
			if v.isChecked():
				data[k] = 1
			else:
				data[k] = 0
		data["marks"] = ""
		for m, ckb in newBibWin.markValues.items():
			if ckb.isChecked():
				data["marks"] += "'%s',"%m
		if data["bibkey"].strip() == "" and data["bibtex"].strip() != "":
			data = pBDB.bibs.prepareInsert(data["bibtex"].strip())
		if data["bibkey"].strip() != "" and data["bibtex"].strip() != "":
			if "bibkey" in data.keys():
				if editKey is not None and data["bibkey"].strip() != editKey:
					print("[GUI] New bibtex key (%s) for element '%s'..."%(data["bibkey"], editKey))
					if editKey not in data["old_keys"]:
						data["old_keys"] += " " + editKey
						data["old_keys"] = data["old_keys"].strip()
					pBDB.bibs.updateBibkey(editKey, data["bibkey"].strip())
				print("[GUI] Updating bibtex '%s'..."%data["bibkey"])
				pBDB.bibs.update(data, data["bibkey"])
			else:
				pBDB.bibs.insert(data)
			message = "Bibtex entry saved"
			statusBarObject.setWindowTitle("PhysBiblio*")
			try:
				parent.reloadMainContent(pBDB.bibs.fetchFromLast().lastFetched)
			except:
				pass
		else:
			infoMessage("ERROR: empty bibtex and/or bibkey!")
	else:
		message = "No modifications to bibtex entry"
	try:
		statusBarObject.StatusBarMessage(message)
	except:
		pass

def deleteBibtex(parent, statusBarObject, bibkey):
	if askYesNo("Do you really want to delete this bibtex entry (bibkey = '%s')?"%(bibkey)):
		pBDB.bibs.delete(bibkey)
		statusBarObject.setWindowTitle("PhysBiblio*")
		message = "Bibtex entry deleted"
		try:
			parent.bibtexList.recreateTable()
		except:
			pass
	else:
		message = "Nothing changed"
	try:
		statusBarObject.StatusBarMessage(message)
	except:
		pass

class bibtexWindow(QFrame):
	def __init__(self, parent = None):
		super(bibtexWindow, self).__init__(parent)
		self.parent = parent

		self.currLayout = QHBoxLayout()
		self.setLayout(self.currLayout)

		self.text = QTextEdit("")
		font = QFont()
		font.setPointSize(pbConfig.params["bibListFontSize"])
		self.text.setFont(font)

		self.currLayout.addWidget(self.text)

class bibtexInfo(QFrame):
	def __init__(self, parent = None):
		super(bibtexInfo, self).__init__(parent)
		self.parent = parent

		self.currLayout = QHBoxLayout()
		self.setLayout(self.currLayout)

		self.text = QTextEdit("")
		font = QFont()
		font.setPointSize(pbConfig.params["bibListFontSize"])
		self.text.setFont(font)

		self.currLayout.addWidget(self.text)

class MyBibTableModel(MyTableModel):
	def __init__(self, parent, bib_list, header, stdCols = [], addCols = [], askBibs = False, previous = [], *args):
		self.typeClass = "Bibs"
		self.dataList = bib_list
		MyTableModel.__init__(self, parent, header + ["bibtex"], askBibs, previous, *args)
		self.stdCols = stdCols
		self.addCols = addCols + ["bibtex"]
		self.lenStdCols = len(stdCols)
		self.prepareSelected()

	def getIdentifier(self, element):
		return element["bibkey"]

	def addTypeCell(self, data):
		someType = False
		string = ""
		for t in convertType.keys():
			if data[t] == 1:
				if someType:
					string += ", "
				string += convertType[t]
		return string

	def addPdfCell(self, key):
		"""create cell for PDF file"""
		if len(pBPDF.getExisting(key))>0:
			return True, self.addImage(":/images/application-pdf.png", self.parentObj.tablewidget.rowHeight(0)*0.9)
		else:
			return False, "no PDF"

	def addMarksCell(self, marks):
		"""create cell for marks"""
		if marks is not None:
			marks = [ k for k in pBMarks.marks.keys() if k in marks ]
			if len(marks)>1:
				return True, self.addImages([pBMarks.marks[img]["icon"] for img in marks ], self.parentObj.tablewidget.rowHeight(0)*0.9)
			elif len(marks)>0:
				return True, self.addImage(pBMarks.marks[marks[0]]["icon"], self.parentObj.tablewidget.rowHeight(0)*0.9)
			else:
				return False, ("", "")
		else:
			return False, ("", "")

	def data(self, index, role):
		if not index.isValid():
			return None
		img = False
		row = index.row()
		column = index.column()
		try:
			if "marks" in self.stdCols and column == self.stdCols.index("marks"):
				img, value = self.addMarksCell(self.dataList[row]["marks"])
			elif column < self.lenStdCols:
				try:
					value = self.dataList[row][self.stdCols[column]]
				except KeyError:
					value = ""
			else:
				if self.addCols[column - self.lenStdCols] == "Type":
					value = self.addTypeCell(self.dataList[row])
				elif self.addCols[column - self.lenStdCols] == "PDF":
					img, value = self.addPdfCell(self.dataList[row]["bibkey"])
				else:
					value = self.dataList[row]["bibtex"]
		except IndexError:
			pBGUIErrorManager("MyBibTableModel.data(): invalid index", trcbk = traceback)
			return None

		if role == Qt.CheckStateRole and self.ask and column == 0:
			if self.selectedElements[self.dataList[row]["bibkey"]] == True:
				return Qt.Checked
			else:
				return Qt.Unchecked
		if role == Qt.EditRole:
			return value
		if role == Qt.DecorationRole and img:
			return value
		if role == Qt.DisplayRole and not img:
			return value
		return None

	def setData(self, index, value, role):
		if role == Qt.CheckStateRole and index.column() == 0:
			if value == Qt.Checked:
				self.selectedElements[self.dataList[index.row()]["bibkey"]] = True
			else:
				self.selectedElements[self.dataList[index.row()]["bibkey"]] = False

		self.emit(SIGNAL("dataChanged(QModelIndex,QModelIndex)"),index, index)
		return True

class bibtexList(QFrame, objListWindow):
	def __init__(self, parent = None, bibs = None, askBibs = False, previous = []):
		#table dimensions
		self.columns = pbConfig.params["bibtexListColumns"]
		self.colcnt = len(self.columns)
		self.colContents = []
		self.previous = previous
		self.parent = parent
		self.askBibs = askBibs
		self.additionalCols = ["Type", "PDF"]
		for j in range(self.colcnt):
			self.colContents.append(self.columns[j])
		self.colContents += [a.lower() for a in self.additionalCols]

		QFrame.__init__(self, parent)
		objListWindow.__init__(self, parent)

		self.selAct = QAction(QIcon(":/images/edit-node.png"),
						"&Select entries", self,
						#shortcut="Ctrl+S",
						statusTip="Select entries from the list",
						triggered=self.enableSelection)
		self.okAct = QAction(QIcon(":/images/dialog-ok-apply.png"),
						"Selection &completed", self,
						#shortcut="Ctrl+S",
						statusTip="Selection of elements completed",
						triggered=self.onOk)
		self.clearAct = QAction(QIcon(":/images/edit-clear.png"),
						"&Clear selection", self,
						#shortcut="Ctrl+S",
						statusTip="Discard the current selection and hide checkboxes",
						triggered=self.clearSelection)
		self.selAllAct = QAction(QIcon(":/images/edit-select-all.png"),
						"&Select all", self,
						#shortcut="Ctrl+S",
						statusTip="Select all the elements",
						triggered=self.selectAll)
		self.unselAllAct = QAction(QIcon(":/images/edit-unselect-all.png"),
						"&Unselect all", self,
						#shortcut="Ctrl+S",
						statusTip="Unselect all the elements",
						triggered=self.unselectAll)

		if bibs is not None:
			self.bibs = bibs
		else:
			self.bibs = None
		self.createTable()

	def reloadColumnContents(self):
		self.columns = pbConfig.params["bibtexListColumns"]
		self.colcnt = len(self.columns)
		self.colContents = []
		for j in range(self.colcnt):
			self.colContents.append(self.columns[j])
		self.colContents += [a.lower() for a in self.additionalCols]

	def changeEnableActions(self):
		status = self.table_model.ask
		self.clearAct.setEnabled(status)
		self.selAllAct.setEnabled(status)
		self.unselAllAct.setEnabled(status)
		self.okAct.setEnabled(status)

	def enableSelection(self):
		self.table_model.changeAsk()
		self.changeEnableActions()

	def clearSelection(self):
		self.table_model.previous = []
		self.table_model.prepareSelected()
		self.table_model.changeAsk(False)
		self.changeEnableActions()

	def selectAll(self):
		self.table_model.selectAll()

	def unselectAll(self):
		self.table_model.unselectAll()

	def onOk(self):
		self.parent.selectedBibs = [key for key in self.table_model.selectedElements.keys() if self.table_model.selectedElements[key] == True]
		ask = askSelBibAction(self.parent, self.parent.selectedBibs)
		ask.exec_()
		if ask.result == "done":
			self.clearSelection()

	def createTable(self):
		if self.bibs is None:
			self.bibs = pBDB.bibs.getAll(orderType = "DESC", limitTo = pbConfig.params["defaultLimitBibtexs"])
		rowcnt = len(self.bibs)

		commentStr = "Last query to bibtex database: \t%s\t\t"%(pBDB.bibs.lastQuery)
		if len(pBDB.bibs.lastVals)>0 :
			commentStr += " - arguments:\t%s"%(pBDB.bibs.lastVals,)
		self.currLayout.addWidget(QLabel(commentStr))

		self.selectToolBar = QToolBar('Bibs toolbar')
		self.selectToolBar.addAction(self.selAct)
		self.selectToolBar.addAction(self.clearAct)
		self.selectToolBar.addSeparator()
		self.selectToolBar.addAction(self.selAllAct)
		self.selectToolBar.addAction(self.unselAllAct)
		self.selectToolBar.addAction(self.okAct)
		self.selectToolBar.addSeparator()

		self.filterInput = QLineEdit("",  self)
		self.filterInput.setPlaceholderText("Filter bibliography")
		self.filterInput.textChanged.connect(self.changeFilter)
		self.selectToolBar.addWidget(self.filterInput)
		self.filterInput.setFocus()

		self.currLayout.addWidget(self.selectToolBar)

		self.table_model = MyBibTableModel(self,
			self.bibs, self.columns + self.additionalCols,
			self.columns, self.additionalCols,
			askBibs = self.askBibs,
			previous = self.previous)

		self.changeEnableActions()
		self.setProxyStuff(self.columns.index("firstdate"), Qt.DescendingOrder)
		self.tablewidget.hideColumn(len(self.columns) + len(self.additionalCols))

		self.finalizeTable()

	def triggeredContextMenuEvent(self, row, col, event):
		def deletePdfFile(bibkey, ftype, fdesc, custom = None):
			if askYesNo("Do you really want to delete the %s file for entry %s?"%(fdesc, bibkey)):
				self.parent.StatusBarMessage("deleting %s file..."%fdesc)
				if custom is not None:
					pBPDF.removeFile(bibkey, "", fname = custom)
				else:
					pBPDF.removeFile(bibkey, ftype)
				self.parent.reloadMainContent(pBDB.bibs.fetchFromLast().lastFetched)

		def copyPdfFile(bibkey, ftype, custom = None):
			pdfName = osp.join(pBPDF.getFileDir(bibkey), custom) if custom is not None else pBPDF.getFilePath(bibkey, ftype)
			outFolder = askDirName(self, title = "Where do you want to save the PDF %s?"%pdfName)
			if outFolder.strip() != "":
				pBPDF.copyToDir(outFolder, bibkey, ftype = ftype, customName = custom)

		index = self.tablewidget.model().index(row, col)
		try:
			bibkey = str(self.proxyModel.sibling(row, self.columns.index("bibkey"), index).data())
		except AttributeError:
			return
		menu = QMenu()
		titAct = menu.addAction("--Entry: %s--"%bibkey).setDisabled(True)
		menu.addSeparator()
		delAction = menu.addAction("Delete")
		modAction = menu.addAction("Modify")
		cleAction = menu.addAction("Clean")
		menu.addSeparator()

		pdfMenu = menu.addMenu("PDF")
		arxiv = pBDB.bibs.getField(bibkey, "arxiv")
		doi = pBDB.bibs.getField(bibkey, "doi")
		files = pBPDF.getExisting(bibkey, fullPath = True)
		arxivFile = pBPDF.getFilePath(bibkey, "arxiv")
		pdfDir = pBPDF.getFileDir(bibkey)
		pdfActs={}
		pdfActs["addPdf"] = pdfMenu.addAction("Add generic PDF")
		pdfMenu.addSeparator()
		if arxivFile in files:
			files.remove(arxivFile)
			pdfActs["openArx"] = pdfMenu.addAction("Open arXiv PDF")
			pdfActs["delArx"] = pdfMenu.addAction("Delete arXiv PDF")
			pdfActs["copyArx"] = pdfMenu.addAction("Copy arXiv PDF")
		elif arxiv is not None and arxiv != "":
			pdfActs["downArx"] = pdfMenu.addAction("Download arXiv PDF")
		pdfMenu.addSeparator()
		doiFile = pBPDF.getFilePath(bibkey, "doi")
		if doiFile in files:
			files.remove(doiFile)
			pdfActs["openDoi"] = pdfMenu.addAction("Open DOI PDF")
			pdfActs["delDoi"] = pdfMenu.addAction("Delete DOI PDF")
			pdfActs["copyDoi"] = pdfMenu.addAction("Copy DOI PDF")
		elif doi is not None and doi != "":
			pdfActs["addDoi"] = pdfMenu.addAction("Assign DOI PDF")
		pdfMenu.addSeparator()
		pdfActs["openOtherPDF"] = [None for i in xrange(len(files))]
		pdfActs["delOtherPDF"] = [None for i in xrange(len(files))]
		pdfActs["copyOtherPDF"] = [None for i in xrange(len(files))]
		for i,f in enumerate(files):
			pdfActs["openOtherPDF"][i] = pdfMenu.addAction("Open %s"%f.replace(pdfDir+"/", ""))
			pdfActs["delOtherPDF"][i] = pdfMenu.addAction("Delete %s"%f.replace(pdfDir+"/", ""))
			pdfActs["copyOtherPDF"][i] = pdfMenu.addAction("Copy %s"%f.replace(pdfDir+"/", ""))
		
		menu.addSeparator()
		catAction = menu.addAction("Manage categories")
		expAction = menu.addAction("Manage experiments")
		menu.addSeparator()
		opArxAct = menu.addAction("Open into arXiv")
		opDoiAct = menu.addAction("Open DOI link")
		opInsAct = menu.addAction("Open into InspireHEP")
		menu.addSeparator()
		insAction = menu.addAction("Complete info (from Inspire)")
		updAction = menu.addAction("Update (search Inspire)")
		menu.addSeparator()
		
		action = menu.exec_(event.globalPos())
		if action == delAction:
			deleteBibtex(self.parent, self.parent, bibkey)
		elif action == modAction:
			editBibtex(self.parent, self.parent, bibkey)
		elif action == catAction:
			previous = [a[0] for a in pBDB.cats.getByEntry(bibkey)]
			selectCats = catsWindowList(parent = self.parent, askCats = True, askForBib = bibkey, expButton = False, previous = previous)
			selectCats.exec_()
			if selectCats.result == "Ok":
				cats = self.parent.selectedCats
				for p in previous:
					if p not in cats:
						pBDB.catBib.delete(p, bibkey)
				for c in cats:
					if c not in previous:
						pBDB.catBib.insert(c, bibkey)
				self.parent.StatusBarMessage("categories for '%s' successfully inserted"%bibkey)
		elif action == expAction:
			previous = [a[0] for a in pBDB.exps.getByEntry(bibkey)]
			selectExps = ExpWindowList(parent = self.parent, askExps = True, askForBib = bibkey, previous = previous)
			selectExps.exec_()
			if selectExps.result == "Ok":
				exps = self.parent.selectedExps
				for p in previous:
					if p not in exps:
						pBDB.bibExp.delete(bibkey, p)
				for e in exps:
					if e not in previous:
						pBDB.bibExp.insert(bibkey, e)
				self.parent.StatusBarMessage("experiments for '%s' successfully inserted"%bibkey)
		elif action == opArxAct:
			pBView.openLink(bibkey, "arxiv")
		elif action == opDoiAct:
			pBView.openLink(bibkey, "doi")
		elif action == opInsAct:
			pBView.openLink(bibkey, "inspire")
		elif action == cleAction:
			self.parent.cleanAllBibtexs(useEntries = pBDB.bibs.getByBibkey(bibkey))
		elif action == insAction:
			self.parent.updateInspireInfo(bibkey)
		elif action == updAction:
			self.parent.updateAllBibtexs(useEntries = pBDB.bibs.getByBibkey(bibkey), force = True)
		#actions for PDF
		elif "openArx" in pdfActs.keys() and action == pdfActs["openArx"]:
			self.parent.StatusBarMessage("opening arxiv PDF...")
			pBPDF.openFile(bibkey, "arxiv")
		elif "openDoi" in pdfActs.keys() and action == pdfActs["openDoi"]:
			self.parent.StatusBarMessage("opening doi PDF...")
			pBPDF.openFile(bibkey, "doi")
		elif "downArx" in pdfActs.keys() and action == pdfActs["downArx"]:
			self.parent.StatusBarMessage("downloading PDF from arxiv...")
			self.downArxiv_thr = thread_downloadArxiv(bibkey)
			self.connect(self.downArxiv_thr, SIGNAL("finished()"), self.downloadArxivDone)
			self.downArxiv_thr.start()
		elif "delArx" in pdfActs.keys() and action == pdfActs["delArx"]:
			deletePdfFile(bibkey, "arxiv", "arxiv PDF")
		elif "delDoi" in pdfActs.keys() and action == pdfActs["delDoi"]:
			deletePdfFile(bibkey, "doi", "DOI PDF")
		elif "copyArx" in pdfActs.keys() and action == pdfActs["copyArx"]:
			copyPdfFile(bibkey, "arxiv")
		elif "copyDoi" in pdfActs.keys() and action == pdfActs["copyDoi"]:
			copyPdfFile(bibkey, "doi")
		elif "addDoi" in pdfActs.keys() and action == pdfActs["addDoi"]:
			newpdf = askFileName(self, "Where is the published PDF located?", filter = "PDF (*.pdf)")
			if newpdf != "" and os.path.isfile(newpdf):
				if pBPDF.copyNewFile(bibkey, newpdf, "doi"):
					infoMessage("PDF successfully copied!")
		elif "addPdf" in pdfActs.keys() and action == pdfActs["addPdf"]:
			newPdf = askFileName(self, "Where is the published PDF located?", filter = "PDF (*.pdf)")
			newName = newPdf.split("/")[-1]
			if newPdf != "" and os.path.isfile(newPdf):
				if pBPDF.copyNewFile(bibkey, newPdf, customName = newName):
					infoMessage("PDF successfully copied!")
		#warning: this elif must be the last one!
		elif len(pdfActs["openOtherPDF"]) > 0:
			for i, act in enumerate(pdfActs["openOtherPDF"]):
				if action == act:
					fn = files[i].replace(pdfDir+"/", "")
					self.parent.StatusBarMessage("opening %s..."%fn)
					pBPDF.openFile(bibkey, fileName = fn)
			for i, act in enumerate(pdfActs["delOtherPDF"]):
				if action == act:
					fn = files[i].replace(pdfDir+"/", "")
					deletePdfFile(bibkey, fn, fn, custom = files[i])
			for i, act in enumerate(pdfActs["copyOtherPDF"]):
				if action == act:
					fn = files[i].replace(pdfDir+"/", "")
					copyPdfFile(bibkey, fn, custom = files[i])

	def cellClick(self, index):
		row = index.row()
		col = index.column()
		try:
			bibkey = str(self.proxyModel.sibling(row, self.columns.index("bibkey"), index).data())
		except AttributeError:
			return
		entry = pBDB.bibs.getByBibkey(bibkey, saveQuery = False)[0]
		self.parent.bottomLeft.text.setText(entry["bibtex"])
		self.parent.bottomRight.text.setText(writeBibtexInfo(entry))
		if self.colContents[col] == "modify":
			editBibtex(self.parent, self.parent, bibkey)
		elif self.colContents[col] == "delete":
			deleteBibtex(self.parent, self.parent, bibkey)

	def cellDoubleClick(self, index):
		row = index.row()
		col = index.column()
		try:
			bibkey = str(self.proxyModel.sibling(row, self.columns.index("bibkey"), index).data())
		except AttributeError:
			return
		entry = pBDB.bibs.getByBibkey(bibkey, saveQuery = False)[0]
		self.parent.bottomLeft.text.setText(entry["bibtex"])
		self.parent.bottomRight.text.setText(writeBibtexInfo(entry))
		if self.colContents[col] == "doi" and entry["doi"] is not None and entry["doi"] != "":
			pBView.openLink(bibkey, "doi")
		elif self.colContents[col] == "arxiv" and entry["arxiv"] is not None and entry["arxiv"] != "":
			pBView.openLink(bibkey, "arxiv")
		elif self.colContents[col] == "inspire" and entry["inspire"] is not None and entry["inspire"] != "":
			pBView.openLink(bibkey, "inspire")
		elif self.colContents[col] == "pdf":
			pdfFiles = pBPDF.getExisting(bibkey)
			if len(pdfFiles) == 1:
				self.parent.StatusBarMessage("opening PDF...")
				pBPDF.openFile(bibkey, fileName = pdfFiles[0])
			elif len(pdfFiles) > 1:
				ask = askPdfAction(self, bibkey, entry["arxiv"], entry["doi"])
				ask.exec_()
				if ask.result == "openArxiv":
					self.parent.StatusBarMessage("opening arxiv PDF...")
					pBPDF.openFile(bibkey, "arxiv")
				elif ask.result == "openDoi":
					self.parent.StatusBarMessage("opening doi PDF...")
					pBPDF.openFile(bibkey, "doi")

	def downloadArxivDone(self):
		self.parent.sendMessage("Arxiv download execution completed! Please check that it worked...")
		self.parent.done()
		self.parent.reloadMainContent(pBDB.bibs.fetchFromLast().lastFetched)

	def finalizeTable(self):
		"""resize the table to fit the contents, connect click and doubleclick functions, add layout"""
		font = QFont()
		font.setPointSize(pbConfig.params["bibListFontSize"])
		self.tablewidget.setFont(font)

		self.tablewidget.resizeColumnsToContents()
		self.tablewidget.resizeRowsToContents()

		self.tablewidget.clicked.connect(self.cellClick)
		self.tablewidget.doubleClicked.connect(self.cellDoubleClick)

		self.currLayout.addWidget(self.tablewidget)

	def recreateTable(self, bibs = None):
		"""delete previous table widget and create a new one"""
		if bibs is not None:
			self.bibs = bibs
		else:
			self.bibs = pBDB.bibs.getAll(orderType = "DESC", limitTo = pbConfig.params["defaultLimitBibtexs"])
		self.cleanLayout()
		self.createTable()

class editBibtexEntry(editObjectWindow):
	"""create a window for editing or creating a bibtex entry"""
	def __init__(self, parent = None, bib = None):
		super(editBibtexEntry, self).__init__(parent)
		self.bibtexEditLines = 8
		if bib is None:
			self.data = {}
			for k in pBDB.tableCols["entries"]:
				self.data[k] = ""
		else:
			self.data = bib
		self.checkValues = {}
		self.markValues = {}
		self.checkboxes = ["exp_paper", "lecture", "phd_thesis", "review", "proceeding", "book", "noUpdate"]
		self.createForm()

	def onOk(self):
		if self.textValues["bibtex"].toPlainText() == "":
			pBGUIErrorManager("Invalid form contents: empty bibtex!", priority = 2)
			return False
		elif not self.textValues["bibkey"].isReadOnly() and self.textValues["bibkey"].text() != "" and self.textValues["bibtex"].toPlainText() != "":
			pBGUIErrorManager("Invalid form contents: bibtex key will be taken from bibtex!", priority = 1)
			return False
		self.result	= True
		self.close()

	def updateBibkey(self):
		bibtex = self.textValues["bibtex"].toPlainText()
		try:
			element = bibtexparser.loads(bibtex).entries[0]
			bibkey = element["ID"]
		except (ValueError, IndexError):
			bibkey = "not valid bibtex!"
		self.textValues["bibkey"].setText(bibkey)

	def createForm(self):
		self.setWindowTitle('Edit bibtex entry')

		i = 0
		for k in pBDB.tableCols["entries"]:
			val = self.data[k] if self.data[k] is not None else ""
			if k != "bibtex" and k != "marks" and k not in self.checkboxes:
				i += 1
				self.currGrid.addWidget(QLabel(k), int((i+1-(i+i)%2)/2)*2-1, ((1+i)%2)*2)
				self.currGrid.addWidget(QLabel("(%s)"%pBDB.descriptions["entries"][k]),  int((i+1-(i+i)%2)/2)*2-1, ((1+i)%2)*2+1)
				self.textValues[k] = QLineEdit(str(val))
				if k == "bibkey" and val != "":
					self.textValues[k].setReadOnly(True)
				self.currGrid.addWidget(self.textValues[k], int((i+1-(i+i)%2)/2)*2, ((1+i)%2)*2, 1, 2)
			elif k == "marks":
				i += 1
				groupBox, markValues = pBMarks.getGroupbox(self.data["marks"], description = pBDB.descriptions["entries"]["marks"])
				self.markValues = markValues
				if ((1+i)%2)*2 != 0:
					i += 1
				self.currGrid.addWidget(groupBox, int((i+1-(i+i)%2)/2)*2, ((1+i)%2)*2, 1, 4)

		self.textValues["bibkey"].setReadOnly(True)

		#bibtex text editor
		i += 1 + i%2
		k = "bibtex"
		self.currGrid.addWidget(QLabel(k), int((i+1-(i+i)%2)/2)*2-1, ((1+i)%2)*2)
		self.currGrid.addWidget(QLabel("(%s)"%pBDB.descriptions["entries"][k]),  int((i+1-(i+i)%2)/2)*2-1, ((1+i)%2)*2+1)
		self.textValues[k] = QPlainTextEdit(self.data[k])
		self.textValues["bibtex"].textChanged.connect(self.updateBibkey)
		self.currGrid.addWidget(self.textValues[k], int((i+1-(i+i)%2)/2)*2, 0, self.bibtexEditLines, 2)

		j = 0
		for k in pBDB.tableCols["entries"]:
			val = self.data[k]
			if k in self.checkboxes:
				j += 2
				self.currGrid.addWidget(QLabel(k), int((i+1-(i+i)%2)/2)*2 + j - 2, 2)
				self.currGrid.addWidget(QLabel("(%s)"%pBDB.descriptions["entries"][k]),  int((i+1-(i+i)%2)/2)*2 + j - 1, 2, 1, 2)
				self.checkValues[k] = QCheckBox("", self)
				if val == 1:
					self.checkValues[k].toggle()
				self.currGrid.addWidget(self.checkValues[k], int((i+1-(i+i)%2)/2)*2 + j - 2, 3)

		self.currGrid.addWidget(self.textValues["bibtex"], int((i+1-(i+i)%2)/2)*2, 0, j, 2)

		# OK button
		i += j
		self.acceptButton = QPushButton('OK', self)
		self.acceptButton.clicked.connect(self.onOk)
		self.currGrid.addWidget(self.acceptButton, i*2+1, 0,1,2)

		# cancel button
		self.cancelButton = QPushButton('Cancel', self)
		self.cancelButton.clicked.connect(self.onCancel)
		self.cancelButton.setAutoDefault(True)
		self.currGrid.addWidget(self.cancelButton, i*2+1, 2,1,2)

		self.setGeometry(100,100,400, 25*i)
		self.centerWindow()

class askPdfAction(askAction):
	def __init__(self, parent = None, key = "", arxiv = None, doi = None):
		super(askPdfAction, self).__init__(parent)
		self.message = "What PDF of this entry (%s) do you want to open?"%(key)
		self.possibleActions = []
		files = pBPDF.getExisting(key, fullPath = True)
		if pBPDF.getFilePath(key, "arxiv") in files:
			self.possibleActions.append(["Open arxiv PDF", self.onOpenArxiv])
		if pBPDF.getFilePath(key, "doi") in files:
			self.possibleActions.append(["Open DOI PDF", self.onOpenDoi])
		self.initUI()

	def onOpenArxiv(self):
		self.result	= "openArxiv"
		self.close()

	def onOpenDoi(self):
		self.result	= "openDoi"
		self.close()

class askSelBibAction(askAction):
	def __init__(self, parent = None, keys = ""):
		super(askSelBibAction, self).__init__(parent)
		self.keys = keys
		self.entries = []
		for k in keys:
			self.entries.append(pBDB.bibs.getByBibkey(k)[0])
		self.parent = parent
		self.message = "What to do with the selected entries?"
		self.possibleActions = []
		self.result = "done"
		self.possibleActions.append(["Clean entries", self.onClean])
		self.possibleActions.append(["Update entries", self.onUpdate])
		self.possibleActions.append(["Export entries in a .bib file", self.onExport])
		self.possibleActions.append(["Copy all the (existing) PDF", self.copyAllPdf])
		self.possibleActions.append(["Select categories", self.onCat])
		self.possibleActions.append(["Select experiments", self.onExp])
		self.initUI()

	def onClean(self):
		self.parent.cleanAllBibtexs(self, useEntries = self.entries)
		self.close()

	def onUpdate(self):
		self.parent.updateAllBibtexs(self, useEntries = self.entries)
		self.close()

	def onExport(self):
		self.parent.exportSelection(self.entries)
		self.close()

	def copyAllPdf(self):
		outFolder = askDirName(self, title = "Where do you want to save the PDF files?")
		if outFolder.strip() != "":
			for entryDict in self.entries:
				entry = entryDict["bibkey"]
				if pBPDF.checkFile(entry, "doi"):
					pBPDF.copyToDir(outFolder, entry, ftype = "doi")
				elif pBPDF.checkFile(entry, "arxiv"):
					pBPDF.copyToDir(outFolder, entry, ftype = "arxiv")
				else:
					existing = pBPDF.getExisting(entry)
					if len(existing) > 0:
						for ex in existing:
							pBPDF.copyToDir(outFolder, entry, "", custom = ex)
		self.close()

	def onCat(self):
		infoMessage("Warning: you can just add categories to the selected entries, not delete!")
		selectCats = catsWindowList(parent = self.parent, askCats = True, expButton = False, previous = [])
		selectCats.exec_()
		if selectCats.result == "Ok":
			pBDB.catBib.insert(self.parent.selectedCats, self.keys)
			self.parent.StatusBarMessage("categories successfully inserted")
		self.close()

	def onExp(self):
		infoMessage("Warning: you can just add experiments to the selected entries, not delete!")
		selectExps = ExpWindowList(parent = self.parent, askExps = True, previous = [])
		selectExps.exec_()
		if selectExps.result == "Ok":
			pBDB.bibExp.insert(self.keys, self.parent.selectedExps)
			self.parent.StatusBarMessage("experiments successfully inserted")
		self.close()

class searchBibsWindow(editObjectWindow):
	"""create a window for editing or creating a bibtex entry"""
	def __init__(self, parent = None, bib = None):
		super(searchBibsWindow, self).__init__(parent)
		self.textValues = []
		self.result = False
		self.possibleTypes = {
			"exp_paper": {"desc": "Experimental"},
			"lecture": {"desc": "Lecture"},
			"phd_thesis": {"desc": "PhD thesis"},
			"review": {"desc": "Review"},
			"proceeding": {"desc": "Proceeding"},
			"book": {"desc": "Book"}
			}
		self.values = {}
		self.values["cats"] = []
		self.values["exps"] = []
		self.values["catsOperator"] = "AND"
		self.values["expsOperator"] = "AND"
		self.values["catExpOperator"] = "AND"
		self.values["marks"] = []
		self.values["marksConn"] = "AND"
		self.values["type"] = []
		self.values["typeConn"] = "AND"
		self.numberOfRows = 1
		self.createForm()

	def onAskCats(self):
		selectCats = catsWindowList(parent = self, askCats = True, expButton = False, previous = self.values["cats"])
		selectCats.exec_()
		if selectCats.result == "Ok":
			self.values["cats"] = self.selectedCats

	def onAskExps(self):
		selectExps = ExpWindowList(parent = self.parent, askExps = True, previous = self.values["exps"])
		selectExps.exec_()
		if selectExps.result == "Ok":
			self.values["exps"] = self.parent.selectedExps

	def onComboCatsChange(self, text):
		self.values["catsOperator"] = text

	def onComboExpsChange(self, text):
		self.values["expsOperator"] = text

	def onComboCEChange(self, text):
		self.values["CatExpOperator"] = text

	def getMarksValues(self):
		self.values["marksConn"] = self.marksConn.currentText()
		self.values["marks"] = []
		for m in self.markValues.keys():
			if self.markValues[m].isChecked():
				self.values["marks"].append(m)

	def getTypeValues(self):
		self.values["typeConn"] = self.typeConn.currentText()
		self.values["type"] = []
		for m in self.typeValues.keys():
			if self.typeValues[m].isChecked():
				self.values["type"].append(m)

	def onAddField(self):
		self.numberOfRows = self.numberOfRows + 1
		self.getMarksValues()
		while True:
			o = self.layout().takeAt(0)
			if o is None: break
			o.widget().deleteLater()
		self.createForm()

	def keyPressEvent(self, e):
		if e.key() == Qt.Key_Escape:
			self.onCancel()

	def eventFilter(self, widget, event):
		if (event.type() == QEvent.KeyPress and
				widget in [a["content"] for a in self.textValues]):
			key = event.key()
			if key == Qt.Key_Return or key == Qt.Key_Enter:
				self.acceptButton.setFocus()
				return True
		return QWidget.eventFilter(self, widget, event)

	def createForm(self, spaceRowHeight = 25):
		self.setWindowTitle('Search bibtex entries')

		self.currGrid.addWidget(MyLabelRight("Filter by categories, using the following operator:"), 0, 0, 1, 3)
		self.catsButton = QPushButton('Categories', self)
		self.catsButton.clicked.connect(self.onAskCats)
		self.currGrid.addWidget(self.catsButton, 0, 3, 1, 2)
		self.comboCats = MyAndOrCombo(self)
		self.comboCats.activated[str].connect(self.onComboCatsChange)
		self.currGrid.addWidget(self.comboCats, 0, 5)

		self.currGrid.addWidget(MyLabelRight("Filter by experiments, using the following operator:"), 1, 0, 1, 3)
		self.expsButton = QPushButton('Experiments', self)
		self.expsButton.clicked.connect(self.onAskExps)
		self.currGrid.addWidget(self.expsButton, 1, 3, 1, 2)
		self.comboExps = MyAndOrCombo(self)
		self.comboExps.activated[str].connect(self.onComboExpsChange)
		self.currGrid.addWidget(self.comboExps, 1, 5)

		self.currGrid.addWidget(MyLabelRight("If using both categories and experiments, which operator between them?"), 2, 0, 1, 4)
		self.comboCE = MyAndOrCombo(self)
		self.comboCE.activated[str].connect(self.onComboCEChange)
		self.currGrid.addWidget(self.comboCE, 2, 5)

		self.currGrid.setRowMinimumHeight(3, spaceRowHeight)

		self.marksConn = MyAndOrCombo(self, current = self.values["marksConn"])
		self.currGrid.addWidget(self.marksConn, 4, 0)
		self.currGrid.addWidget(MyLabelRight("Filter by marks:"), 4, 1)
		groupBox, markValues = pBMarks.getGroupbox(self.values["marks"], description = "", radio = True, addAny = True)
		self.markValues = markValues
		self.currGrid.addWidget(groupBox, 4, 2, 1, 5)

		self.typeConn = MyAndOrCombo(self, current = self.values["typeConn"])
		self.currGrid.addWidget(self.typeConn, 5, 0)
		self.currGrid.addWidget(MyLabelRight("Entry type:"), 5, 1)
		groupBox = QGroupBox()
		self.typeValues = {}
		groupBox.setFlat(True)
		vbox = QHBoxLayout()
		for m, cont in self.possibleTypes.items():
			self.typeValues[m] = QRadioButton(cont["desc"])
			if m in self.values["type"]:
				self.typeValues[m].setChecked(True)
			vbox.addWidget(self.typeValues[m])
		vbox.addStretch(1)
		groupBox.setLayout(vbox)
		self.currGrid.addWidget(groupBox, 5, 2, 1, 5)

		self.currGrid.addWidget(QLabel("Select more: the operator to use, the field to match, (exact match vs contains) and the content to match"), 7, 0, 1, 7)
		firstFields = 8
		self.currGrid.setRowMinimumHeight(6, spaceRowHeight)

		for i in range(self.numberOfRows):
			try:
				previous = {
					"logical": "%s"%self.textValues[i]["logical"].currentText(),
					"field": "%s"%self.textValues[i]["field"].currentText(),
					"operator": "%s"%self.textValues[i]["operator"].currentText(),
					"content": "%s"%self.textValues[i]["content"].text()
				}
			except IndexError:
				previous = {"logical": None, "field": None, "operator": None, "content": ""}
				self.textValues.append({})

			self.textValues[i]["logical"] = MyAndOrCombo(self, current = previous["logical"])
			self.currGrid.addWidget(self.textValues[i]["logical"], i + firstFields, 0)

			self.textValues[i]["field"] = MyComboBox(self, ["bibtex", "bibkey", "arxiv", "doi", "year", "firstdate", "pubdate", "comment"], current = previous["field"])
			self.currGrid.addWidget(self.textValues[i]["field"], i + firstFields, 1)

			self.textValues[i]["operator"] = MyComboBox(self, ["contains", "exact match"], current = previous["operator"])
			self.currGrid.addWidget(self.textValues[i]["operator"], i + firstFields, 2)

			self.textValues[i]["content"] = QLineEdit(previous["content"])
			self.currGrid.addWidget(self.textValues[i]["content"], i + firstFields, 3, 1, 4)
			self.textValues[i]["content"].installEventFilter(self)

		self.textValues[-1]["content"].setFocus()

		i = self.numberOfRows + firstFields + 1
		self.currGrid.addWidget(MyLabelRight("Click here if you want more fields:"), i-1, 0, 1, 2)
		self.addFieldButton = QPushButton("Add another line", self)
		self.addFieldButton.clicked.connect(self.onAddField)
		self.currGrid.addWidget(self.addFieldButton, i-1, 2, 1, 2)

		self.currGrid.setRowMinimumHeight(i, spaceRowHeight)

		#limit to, limit offset
		i += 2
		try:
			lim = self.limitValue.text()
			offs = self.limitOffs.text()
		except AttributeError:
			lim = str(pbConfig.params["defaultLimitBibtexs"])
			offs = "0"
		self.currGrid.addWidget(MyLabelRight("Max number of results:"), i - 1, 0, 1, 2)
		self.limitValue = QLineEdit(lim)
		self.limitValue.setMaxLength(6)
		self.limitValue.setFixedWidth(75)
		self.currGrid.addWidget(self.limitValue, i - 1, 2)
		self.currGrid.addWidget(MyLabelRight("Start from:"), i - 1, 3, 1, 2)
		self.limitOffs = QLineEdit(offs)
		self.limitOffs.setMaxLength(6)
		self.limitOffs.setFixedWidth(75)
		self.currGrid.addWidget(self.limitOffs, i - 1, 5)

		self.currGrid.setRowMinimumHeight(i, spaceRowHeight)
		i += 1

		# OK button
		self.acceptButton = QPushButton('OK', self)
		self.acceptButton.clicked.connect(self.onOk)
		self.currGrid.addWidget(self.acceptButton, i, 2)
		self.acceptButton.setFixedWidth(80)

		# cancel button
		self.cancelButton = QPushButton('Cancel', self)
		self.cancelButton.clicked.connect(self.onCancel)
		self.cancelButton.setAutoDefault(True)
		self.currGrid.addWidget(self.cancelButton, i, 3)
		self.cancelButton.setFixedWidth(80)

		self.currGrid.setColumnStretch(6, 1)