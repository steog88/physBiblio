#!/usr/bin/env python
"""
Test file for the physbiblio.gui.commonClasses module.

This file is part of the physbiblio package.
"""
import sys, traceback
import os
from PySide2.QtCore import Qt
from PySide2.QtTest import QTest
from PySide2.QtWidgets import QInputDialog, QDesktopWidget

if sys.version_info[0] < 3:
	import unittest2 as unittest
	from mock import patch, call
else:
	import unittest
	from unittest.mock import patch, call

try:
	from physbiblio.setuptests import *
	from physbiblio.gui.setuptests import *
	from physbiblio.gui.commonClasses import *
except ImportError:
    print("Could not find physbiblio and its contents: configure your PYTHONPATH!")
    raise
except Exception:
	print(traceback.format_exc())

class emptyTableModel(QAbstractTableModel):
	"""Used to do tests when a table model is needed"""
	def __init__(self, *args):
		QAbstractTableModel.__init__(self, *args)

	def rowCount(self, a = None):
		return 1

	def columnCount(self, a = None):
		return 1

	def data(self, index, role):
		return None

@unittest.skipIf(skipGuiTests, "GUI tests")
class TestLabels(GUITestCase):
	"""
	Test the MyLabelRight and MyLabelCenter classes
	"""
	def test_myLabelRight(self):
		"""Test MyLabelRight"""
		l = MyLabelRight("label")
		self.assertIsInstance(l, QLabel)
		self.assertEqual(l.text(), "label")
		self.assertEqual(l.alignment(), Qt.AlignRight | Qt.AlignVCenter)

	def test_myLabelCenter(self):
		"""Test MyLabelCenter"""
		l = MyLabelCenter("label")
		self.assertIsInstance(l, QLabel)
		self.assertEqual(l.text(), "label")
		self.assertEqual(l.alignment(), Qt.AlignCenter | Qt.AlignVCenter)

@unittest.skipIf(skipGuiTests, "GUI tests")
class TestObjListWindow(GUITestCase):
	"""
	Test the objListWindow class
	"""
	def test_init(self):
		"""test the __init__ function"""
		olw = objListWindow()
		self.assertIsInstance(olw, QDialog)
		self.assertEqual(olw.tableWidth, None)
		self.assertEqual(olw.proxyModel, None)
		self.assertFalse(olw.gridLayout)
		self.assertIsInstance(olw.currLayout, QVBoxLayout)
		self.assertEqual(olw.layout(), olw.currLayout)

		olw = objListWindow(gridLayout = True)
		self.assertTrue(olw.gridLayout)
		self.assertIsInstance(olw.currLayout, QGridLayout)
		self.assertEqual(olw.layout(), olw.currLayout)

	def test_NI(self):
		"""Test the non implemented functions (must be subclassed!)"""
		olw = objListWindow()
		ix = QModelIndex()
		self.assertRaises(NotImplementedError, lambda: olw.createTable())
		self.assertRaises(NotImplementedError, lambda: olw.cellClick(ix))
		self.assertRaises(NotImplementedError, lambda: olw.cellDoubleClick(ix))
		self.assertRaises(NotImplementedError, lambda: olw.handleItemEntered(ix))
		self.assertRaises(NotImplementedError, lambda: olw.triggeredContextMenuEvent(0, 0, ix))

	def test_changeFilter(self):
		"""test changeFilter"""
		olw = objListWindow()
		olw.table_model = emptyTableModel()
		olw.setProxyStuff(1, Qt.AscendingOrder)
		olw.changeFilter("abc")
		self.assertEqual(olw.proxyModel.filterRegExp().pattern(), "abc")
		olw.changeFilter(123)
		self.assertEqual(olw.proxyModel.filterRegExp().pattern(), "123")

	def test_addFilterInput(self):
		"""test addFilterInput"""
		olw = objListWindow()
		olw.addFilterInput("plch")
		self.assertIsInstance(olw.filterInput, QLineEdit)
		self.assertEqual(olw.filterInput.placeholderText(), "plch")
		with patch("physbiblio.gui.commonClasses.objListWindow.changeFilter") as _cf:
			olw.filterInput.textChanged.emit("sss")
			_cf.assert_called_once_with("sss")

		olw = objListWindow(gridLayout = True)
		olw.addFilterInput("plch", gridPos = (4, 1))
		self.assertEqual(olw.layout().itemAtPosition(4, 1).widget(), olw.filterInput)

	def test_setProxyStuff(self):
		"""test setProxyStuff"""
		olw = objListWindow()
		olw.table_model = emptyTableModel()
		with patch("PySide2.QtCore.QSortFilterProxyModel.sort") as _s:
			olw.setProxyStuff(1, Qt.AscendingOrder)
			_s.assert_called_once_with(1, Qt.AscendingOrder)
		self.assertIsInstance(olw.proxyModel, QSortFilterProxyModel)
		self.assertEqual(olw.proxyModel.filterCaseSensitivity(), Qt.CaseInsensitive)
		self.assertEqual(olw.proxyModel.sortCaseSensitivity(), Qt.CaseInsensitive)
		self.assertEqual(olw.proxyModel.filterKeyColumn(), -1)

		self.assertIsInstance(olw.tablewidget, MyTableView)
		self.assertEqual(olw.tablewidget.model(), olw.proxyModel)
		self.assertTrue(olw.tablewidget.isSortingEnabled())
		self.assertTrue(olw.tablewidget.hasMouseTracking())
		self.assertEqual(olw.layout().itemAt(0).widget(), olw.tablewidget)

	def test_finalizeTable(self):
		"""Test finalizeTable"""
		olw = objListWindow()
		olw.table_model = emptyTableModel()
		with patch("PySide2.QtCore.QSortFilterProxyModel.sort") as _s:
			olw.setProxyStuff(1, Qt.AscendingOrder)
		with patch("PySide2.QtWidgets.QTableView.resizeColumnsToContents") as _rc:
			with patch("PySide2.QtWidgets.QTableView.resizeRowsToContents") as _rr:
				olw.finalizeTable()
				_rc.assert_has_calls([call(), call()])
				_rr.assert_called_once()
		self.assertIsInstance(olw.tablewidget, MyTableView)
		maxw = QDesktopWidget().availableGeometry().width()
		self.assertEqual(olw.maximumHeight(), QDesktopWidget().availableGeometry().height())
		self.assertEqual(olw.maximumWidth(), maxw)
		hwidth = olw.tablewidget.horizontalHeader().length()
		swidth = olw.tablewidget.style().pixelMetric(QStyle.PM_ScrollBarExtent)
		fwidth = olw.tablewidget.frameWidth() * 2

		if hwidth > maxw - (swidth + fwidth):
			tW = maxw - (swidth + fwidth)
		else:
			tW = hwidth + swidth + fwidth
		self.assertEqual(olw.tablewidget.width(), tW)
		self.assertEqual(olw.minimumHeight(), 600)
		ix = QModelIndex()
		with patch("physbiblio.gui.commonClasses.objListWindow.handleItemEntered") as _f:
			olw.tablewidget.entered.emit(ix)
			_f.assert_called_once_with(ix)
		with patch("physbiblio.gui.commonClasses.objListWindow.cellClick") as _f:
			olw.tablewidget.clicked.emit(ix)
			_f.assert_called_once_with(ix)
		with patch("physbiblio.gui.commonClasses.objListWindow.cellDoubleClick") as _f:
			olw.tablewidget.doubleClicked.emit(ix)
			_f.assert_called_once_with(ix)
		self.assertEqual(olw.layout().itemAt(0).widget(), olw.tablewidget)

		olw = objListWindow(gridLayout = True)
		olw.table_model = emptyTableModel()
		with patch("PySide2.QtCore.QSortFilterProxyModel.sort") as _s:
			olw.setProxyStuff(1, Qt.AscendingOrder)
		olw.finalizeTable(gridPos = (4, 1))
		self.assertEqual(olw.layout().itemAtPosition(4, 1).widget(), olw.tablewidget)

	def test_cleanLayout(self):
		"""Test cleanLayout"""
		olw = objListWindow()
		olw.layout().addWidget(QLabel("empty"))
		olw.layout().addWidget(QLabel("empty1"))
		self.assertEqual(olw.layout().count(), 2)
		olw.cleanLayout()
		self.assertEqual(olw.layout().count(), 0)

	def test_recreateTable(self):
		"""Test recreateTable"""
		olw = objListWindow()
		with patch("physbiblio.gui.commonClasses.objListWindow.cleanLayout") as _cl:
			with patch("physbiblio.gui.commonClasses.objListWindow.createTable") as _ct:
				olw.recreateTable()
				_cl.assert_called_once()
				_ct.assert_called_once()

@unittest.skipIf(skipGuiTests, "GUI tests")
class TestEditObjectWindow(GUITestCase):
	"""
	Test the editObjectWindow class
	"""
	def test_init(self):
		pass
	def test_keyPressEvent(self):
		pass
	def test_onCancel(self):
		pass
	def test_onOk(self):
		pass
	def test_initUI(self):
		pass
	def test_centerWindow(self):
		pass

@unittest.skipIf(skipGuiTests, "GUI tests")
class TestMyThread(GUITestCase):
	"""
	Test the MyThread class
	"""
	def test_init(self):
		pass

@unittest.skipIf(skipGuiTests, "GUI tests")
class TestWriteStream(GUITestCase):
	"""
	Test the WriteStream class
	"""
	def test_init(self):
		pass

@unittest.skipIf(skipGuiTests, "GUI tests")
class TestMyComboBox(GUITestCase):
	"""
	Test the MyComboBox class
	"""
	def test_init(self):
		pass

@unittest.skipIf(skipGuiTests, "GUI tests")
class TestMyAndOrCombo(GUITestCase):
	"""
	Test the  class
	"""
	def test_init(self):
		pass

@unittest.skipIf(skipGuiTests, "GUI tests")
class TestMyTrueFalseCombo(GUITestCase):
	"""
	Test the  class
	"""
	def test_init(self):
		pass

@unittest.skipIf(skipGuiTests, "GUI tests")
class TestMyTableWidget(GUITestCase):
	"""
	Test the  class
	"""
	def test_init(self):
		pass

@unittest.skipIf(skipGuiTests, "GUI tests")
class TestMyTableView(GUITestCase):
	"""
	Test the  class
	"""
	def test_init(self):
		pass

@unittest.skipIf(skipGuiTests, "GUI tests")
class TestMyTableModel(GUITestCase):
	"""
	Test the  class
	"""
	def test_init(self):
		pass

@unittest.skipIf(skipGuiTests, "GUI tests")
class TestTreeNode(GUITestCase):
	"""
	Test the  class
	"""
	def test_init(self):
		pass

@unittest.skipIf(skipGuiTests, "GUI tests")
class TestTreeModel(GUITestCase):
	"""
	Test the  class
	"""
	def test_init(self):
		pass

@unittest.skipIf(skipGuiTests, "GUI tests")
class TestNamedElement(GUITestCase):
	"""
	Test the  class
	"""
	def test_init(self):
		pass

@unittest.skipIf(skipGuiTests, "GUI tests")
class TestNamedNode(GUITestCase):
	"""
	Test the  class
	"""
	def test_init(self):
		pass

@unittest.skipIf(skipGuiTests, "GUI tests")
class TestLeafFilterProxyModel(GUITestCase):
	"""
	Test the  class
	"""
	def test_init(self):
		pass

@unittest.skipIf(skipGuiTests, "GUI tests")
class TestMyDDTableWidget(GUITestCase):
	"""
	Test the  class
	"""
	def test_init(self):
		pass

@unittest.skipIf(skipGuiTests, "GUI tests")
class TestMyMenu(GUITestCase):
	"""
	Test the  class
	"""
	def test_init(self):
		pass

@unittest.skipIf(skipGuiTests, "GUI tests")
class TestGuiViewEntry(GUITestCase):
	"""
	Test the  class
	"""
	def test_init(self):
		pass

@unittest.skipIf(skipGuiTests, "GUI tests")
class TestMyImportedTableModel(GUITestCase):
	"""
	Test the  class
	"""
	def test_init(self):
		pass

if __name__=='__main__':
	unittest.main()