#!/usr/bin/env python
"""
Test file for the physbiblio.gui.dialogWindows module.

This file is part of the physbiblio package.
"""
import sys, traceback
import os
from PySide2.QtCore import Qt
from PySide2.QtTest import QTest
from PySide2.QtWidgets import QWidget

if sys.version_info[0] < 3:
	import unittest2 as unittest
	from mock import patch, call
else:
	import unittest
	from unittest.mock import patch, call

try:
	from physbiblio.setuptests import *
	from physbiblio.database import pBDB
	from physbiblio.config import pbConfig, configuration_params
	from physbiblio.gui.setuptests import *
	from physbiblio.gui.dialogWindows import *
except ImportError:
    print("Could not find physbiblio and its modules!")
    raise
except Exception:
	print(traceback.format_exc())

@unittest.skipIf(skipTestsSettings.gui, "GUI tests")
class TestConfigEditColumns(GUITestCase):
	"""
	Test configEditColumns
	"""
	@classmethod
	def setUpClass(self):
		"""set temporary settings"""
		self.oldColumns = pbConfig.params["bibtexListColumns"]
		self.defCols = [a["default"] for a in configuration_params \
			if a["name"] == "bibtexListColumns"][0]
		pbConfig.params["bibtexListColumns"] = self.defCols

	@classmethod
	def tearDownClass(self):
		"""restore previous settings"""
		pbConfig.params["bibtexListColumns"] = self.oldColumns

	def test_init(self):
		"""Test __init__"""
		p = QWidget()
		with patch("physbiblio.gui.dialogWindows.configEditColumns.initUI") \
				as _u:
			cec = configEditColumns()
			self.assertIsInstance(cec, QDialog)
			self.assertEqual(cec.parent(), None)
			_u.assert_called_once_with()
			cec = configEditColumns(p)
			self.assertIsInstance(cec, QDialog)
			self.assertEqual(cec.parent(), p)
			self.assertEqual(cec.excludeCols, [
				"crossref", "bibtex", "exp_paper", "lecture",
				"phd_thesis", "review", "proceeding", "book", "noUpdate"])
			self.assertEqual(cec.moreCols, [
				"title", "author", "journal", "volume", "pages",
				"primaryclass", "booktitle", "reportnumber"])
			self.assertEqual(cec.previousSelected,
				self.defCols)
			self.assertEqual(cec.selected,
				self.defCols)
			cec = configEditColumns(p, ['bibkey', 'author', 'title'])
			self.assertEqual(cec.previousSelected,
				['bibkey', 'author', 'title'])

	def test_onCancel(self):
		"""test onCancel"""
		cec = configEditColumns()
		with patch("PySide2.QtWidgets.QDialog.close") as _c:
			cec.onCancel()
			self.assertFalse(cec.result)
			_c.assert_called_once()

	def test_onOk(self):
		"""test onOk"""
		p = QWidget()
		cec = configEditColumns(p, ['bibkey', 'author', 'title'])
		with patch("PySide2.QtWidgets.QDialog.close") as _c:
			cec.onOk()
			self.assertTrue(cec.result)
			_c.assert_called_once()
		self.assertEqual(cec.selected,
			['bibkey', 'author', 'title'])
		item = QTableWidgetItem("arxiv")
		cec.listSel.insertRow(3)
		cec.listSel.setItem(3, 0, item)
		with patch("PySide2.QtWidgets.QDialog.close") as _c:
			cec.onOk()
		self.assertEqual(cec.selected,
			['bibkey', 'author', 'title', 'arxiv'])

	def test_initUI(self):
		"""test initUI"""
		p = QWidget()
		cec = configEditColumns(p, ['bibkey', 'author', 'title'])
		self.assertIsInstance(cec.layout(), QGridLayout)
		self.assertEqual(cec.layout(), cec.gridlayout)
		self.assertIsInstance(cec.items, list)
		self.assertIsInstance(cec.allItems, list)
		self.assertIsInstance(cec.selItems, list)
		self.assertIsInstance(cec.listAll, MyDDTableWidget)
		self.assertIsInstance(cec.listSel, MyDDTableWidget)
		self.assertIsInstance(cec.layout().itemAtPosition(0, 0).widget(),
			QLabel)
		self.assertEqual(cec.layout().itemAtPosition(0, 0).widget().text(),
			"Drag and drop items to order visible columns")
		self.assertEqual(cec.layout().itemAtPosition(1, 0).widget(),
			cec.listAll)
		self.assertEqual(cec.layout().itemAtPosition(1, 1).widget(),
			cec.listSel)
		self.assertEqual(cec.allItems,
			pBDB.descriptions["entries"].keys() + cec.moreCols)
		self.assertEqual(cec.selItems, cec.previousSelected)

		self.assertEqual(cec.listSel.rowCount(), 3)
		for ix, col in enumerate(['bibkey', 'author', 'title']):
			item = cec.listSel.item(ix, 0)
			self.assertEqual(item.text(), col)
			self.assertIs(item, cec.items[ix])

		allCols = [i for i in cec.allItems
			if i not in cec.selItems and i not in cec.excludeCols]
		self.assertEqual(cec.listAll.rowCount(), len(allCols))
		for ix, col in enumerate(allCols):
			item = cec.listAll.item(ix, 0)
			self.assertEqual(item.text(), col)
			self.assertIs(item, cec.items[ix + 3])

		self.assertIsInstance(cec.acceptButton, QPushButton)
		self.assertIsInstance(cec.cancelButton, QPushButton)
		self.assertEqual(cec.acceptButton.text(), "OK")
		self.assertEqual(cec.cancelButton.text(), "Cancel")
		self.assertTrue(cec.cancelButton.autoDefault())
		self.assertEqual(cec.layout().itemAtPosition(2, 0).widget(),
			cec.acceptButton)
		self.assertEqual(cec.layout().itemAtPosition(2, 1).widget(),
			cec.cancelButton)
		with patch("physbiblio.gui.dialogWindows.configEditColumns.onOk") \
				as _f:
			QTest.mouseClick(cec.acceptButton, Qt.LeftButton)
			_f.assert_called_once_with()
		with patch("physbiblio.gui.dialogWindows.configEditColumns.onCancel") \
				as _f:
			QTest.mouseClick(cec.cancelButton, Qt.LeftButton)
			_f.assert_called_once_with()

@unittest.skipIf(skipTestsSettings.gui, "GUI tests")
class TestConfigWindow(GUITestCase):
	"""
	Test configWindow
	"""
	@classmethod
	def setUpClass(self):
		"""set temporary settings"""
		pass

	@classmethod
	def tearDownClass(self):
		"""restore previous settings"""
		pass

	def test_init(self):
		"""Test __init__"""
		p = QWidget()
		with patch("physbiblio.gui.dialogWindows.configWindow.initUI") as _iu:
			cw = configWindow(p)
			self.assertIsInstance(cw, QDialog)
			self.assertEqual(cw.parent(), p)
			self.assertEqual(cw.textValues, [])
			_iu.assert_called_once_with()

	def test_onCancel(self):
		"""test onCancel"""
		cw = configWindow()
		with patch("PySide2.QtWidgets.QDialog.close") as _c:
			cw.onCancel()
			self.assertFalse(cw.result)
			_c.assert_called_once()

	def test_onOk(self):
		"""test onOk"""
		cw = configWindow()
		with patch("PySide2.QtWidgets.QDialog.close") as _c:
			cw.onOk()
			self.assertTrue(cw.result)
			_c.assert_called_once()

	def test_editFolder(self):
		"""test"""
		pass

	def test_editFile(self):
		"""test"""
		pass

	def test_editColumns(self):
		"""test"""
		pass

	def test_editDefCats(self):
		"""test"""
		pass

	def test_initUI(self):
		"""test"""
		pass

@unittest.skipIf(skipTestsSettings.gui, "GUI tests")
class TestLogFileContentDialog(GUITestCase):
	"""
	Test LogFileContentDialog
	"""
	def test_init(self):
		"""test __init__"""
		p = QWidget()
		with patch("physbiblio.gui.dialogWindows." +
				"LogFileContentDialog.initUI") as _u:
			lf = LogFileContentDialog(p)
			self.assertIsInstance(lf, QDialog)
			self.assertEqual(lf.parent(), p)
			self.assertEqual(lf.title, "Log File Content")
			_u.assert_called_once_with()

	def test_clearLog(self):
		"""test clearLog"""
		p = QWidget()
		with open(pbConfig.params["logFileName"], "w") as _f:
			_f.write("test content")
		lf = LogFileContentDialog(p)
		ayn_str = "physbiblio.gui.dialogWindows.askYesNo"
		with patch(ayn_str, return_value = False) as _ayn:
			lf.clearLog()
			with open(pbConfig.params["logFileName"]) as _f:
				text = _f.read()
			self.assertEqual(text, "test content")
		with patch(ayn_str, return_value = True) as _ayn,\
				patch("physbiblio.gui.dialogWindows.infoMessage") as _in,\
				patch("PySide2.QtWidgets.QDialog.close") as _c:
			lf.clearLog()
			with open(pbConfig.params["logFileName"]) as _f:
				text = _f.read()
			self.assertEqual(text, "")
			_in.assert_called_once_with("Log file cleared.")
			_c.assert_called_once_with()
		if os.path.exists(pbConfig.params["logFileName"]):
			os.remove(pbConfig.params["logFileName"])
		with patch(ayn_str, return_value = True) as _ayn,\
				patch("__builtin__.open", side_effect = IOError("fake")) as _op,\
				patch("logging.Logger.exception") as _ex,\
				patch("PySide2.QtWidgets.QDialog.close") as _c:
			lf.clearLog()
			_ex.assert_called_once_with("Impossible to clear log file!")
			_c.assert_not_called()

	def test_initUI(self):
		"""test initUI"""
		p = QWidget()
		if os.path.exists(pbConfig.params["logFileName"]):
			os.remove(pbConfig.params["logFileName"])
		with patch("logging.Logger.exception") as _ex:
			lf = LogFileContentDialog(p)
			_ex.assert_called_once_with("Impossible to read log file!")
			self.assertIsInstance(lf.textEdit, QPlainTextEdit)
			self.assertEqual(lf.textEdit.toPlainText(),
				"Impossible to read log file!")
		with open(pbConfig.params["logFileName"], "w") as _f:
			_f.write("test content")
		lf = LogFileContentDialog(p)
		self.assertEqual(lf.windowTitle(), lf.title)
		self.assertIsInstance(lf.layout(), QVBoxLayout)
		self.assertEqual(lf.layout().spacing(), 1)
		self.assertIsInstance(lf.layout().itemAt(0).widget(), QLabel)
		self.assertEqual(lf.layout().itemAt(0).widget().text(),
			"Reading %s"%pbConfig.params["logFileName"])
		self.assertIsInstance(lf.textEdit, QPlainTextEdit)
		self.assertTrue(lf.textEdit.isReadOnly())
		self.assertEqual(lf.textEdit.toPlainText(), "test content")
		self.assertIsInstance(lf.layout().itemAt(1).widget(), QPlainTextEdit)
		self.assertEqual(lf.textEdit, lf.layout().itemAt(1).widget())
		self.assertIsInstance(lf.layout().itemAt(2).widget(), QPushButton)
		self.assertEqual(lf.layout().itemAt(2).widget(), lf.closeButton)
		self.assertTrue(lf.closeButton.autoDefault())
		self.assertEqual(lf.closeButton.text(), "Close")
		self.assertIsInstance(lf.layout().itemAt(3).widget(), QPushButton)
		self.assertEqual(lf.layout().itemAt(3).widget(), lf.clearButton)
		self.assertEqual(lf.clearButton.text(), "Clear log file")

@unittest.skipIf(skipTestsSettings.gui, "GUI tests")
class TestPrintText(GUITestCase):
	"""
	Test printText
	"""
	def test_init(self):
		"""test"""
		pass

	def test_closeEvent(self):
		"""test"""
		pass

	def test_initUI(self):
		"""test"""
		pass

	def test_append_text(self):
		"""test"""
		pass

	def test_progressBarMin(self):
		"""test"""
		pass

	def test_progressBarMax(self):
		"""test"""
		pass

	def test_stopExec(self):
		"""test"""
		pass

	def test_enableClose(self):
		"""test"""
		pass

@unittest.skipIf(skipTestsSettings.gui, "GUI tests")
class TestSearchReplaceDialog(GUITestCase):
	"""
	Test searchReplaceDialog
	"""
	def test_init(self):
		"""test"""
		pass

	def test_onCancel(self):
		"""test"""
		pass

	def test_onOk(self):
		"""test"""
		pass

	def test_initUI(self):
		"""test"""
		pass

@unittest.skipIf(skipTestsSettings.gui, "GUI tests")
class TestAdvImportDialog(GUITestCase):
	"""
	Test advImportDialog
	"""
	def test_init(self):
		"""test"""
		pass

	def test_onCancel(self):
		"""test"""
		pass

	def test_onOK(self):
		"""test"""
		pass

	def test_initUI(self):
		"""test"""
		pass

@unittest.skipIf(skipTestsSettings.gui, "GUI tests")
class TestAdvImportSelect(GUITestCase):
	"""
	Test advImportSelect
	"""
	def test_init(self):
		"""test"""
		pass

	def test_onCancel(self):
		"""test"""
		pass

	def test_onOk(self):
		"""test"""
		pass

	def test_keyPressEvent(self):
		"""test"""
		pass

	def test_changeFilter(self):
		"""test"""
		pass

	def test_initUI(self):
		"""test"""
		pass

	def test_triggeredContextMenuEvent(self):
		"""test"""
		pass

	def test_handleItemEntered(self):
		"""test"""
		pass

	def test_cellClick(self):
		"""test"""
		pass

	def test_cellDoubleClick(self):
		"""test"""
		pass

@unittest.skipIf(skipTestsSettings.gui, "GUI tests")
class TestDailyArxivDialog(GUITestCase):
	"""
	Test dailyArxivDialog
	"""
	def test_init(self):
		"""test"""
		pass

	def test_onCancel(self):
		"""test"""
		pass

	def test_onOk(self):
		"""test"""
		pass

	def test_updateCat(self):
		"""test"""
		pass

	def test_initUI(self):
		"""test"""
		pass

@unittest.skipIf(skipTestsSettings.gui, "GUI tests")
class TestDailyArxivSelect(GUITestCase):
	"""
	Test dailyArxivSelect
	"""
	def test_initUI(self):
		"""test"""
		pass

	def test_cellClick(self):
		"""test"""
		pass

if __name__=='__main__':
	unittest.main()
