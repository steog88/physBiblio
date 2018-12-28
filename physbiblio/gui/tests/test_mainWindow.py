#!/usr/bin/env python
"""Test file for the physbiblio.gui.mainWindow module.

This file is part of the physbiblio package.
"""
import sys
import traceback
import os
from PySide2.QtCore import Qt, QEvent
from PySide2.QtGui import QImage
from PySide2.QtTest import QTest
from PySide2.QtWidgets import QMenu, QToolBar

if sys.version_info[0] < 3:
	import unittest2 as unittest
	from mock import patch, call, MagicMock
else:
	import unittest
	from unittest.mock import patch, call, MagicMock

try:
	from physbiblio.setuptests import *
	from physbiblio.gui.setuptests import *
	from physbiblio.gui.mainWindow import *
except ImportError:
	print("Could not find physbiblio and its modules!")
	raise
except Exception:
	print(traceback.format_exc())


@unittest.skipIf(skipTestsSettings.gui, "GUI tests")
class TestMainWindow(GUITestCase):
	"""test the MainWindow class"""

	@classmethod
	def setUpClass(self):
		"""define common parameters for test use"""
		super(TestMainWindow, self).setUpClass()
		self.qmwName = "PySide2.QtWidgets.QMainWindow"
		self.modName = "physbiblio.gui.mainWindow"
		self.clsName = self.modName + ".MainWindow"
		self.mainW = MainWindow()

	def test_init(self):
		"""test __init__"""
		tcu = Thread_checkUpdated()
		tcu.start = MagicMock()
		pBDB.onIsLocked = None
		with patch(self.clsName + ".createActions") as _ca,\
				patch(self.clsName + ".createMenusAndToolBar") as _mt,\
				patch(self.clsName + ".createMainLayout") as _ml,\
				patch(self.clsName + ".setIcon") as _si,\
				patch(self.clsName + ".createStatusBar") as _sb,\
				patch(self.modName + ".Thread_checkUpdated",
					return_value=tcu) as _cu:
			mw = MainWindow()
			_ca.assert_called_once_with()
			_mt.assert_called_once_with()
			_ml.assert_called_once_with()
			_si.assert_called_once_with()
			_sb.assert_called_once_with()
			_cu.assert_called_once_with(mw)
			tcu.start.assert_called_once_with()
			mw1 = MainWindow(testing=True)
			_ca.assert_called_once_with()
		with patch(self.clsName + ".printNewVersion") as _pnw:
			mw.checkUpdated.result.emit(True, "0.0.0")
			_pnw.assert_called_once_with(True, "0.0.0")
		self.assertIsInstance(mw, QMainWindow)
		self.assertEqual(mw.minimumWidth(), 600)
		self.assertEqual(mw.minimumHeight(), 400)
		self.assertIsInstance(mw.mainStatusBar, QStatusBar)
		self.assertEqual(mw.lastAuthorStats, None)
		self.assertEqual(mw.lastPaperStats, None)
		self.assertIsInstance(mw1, QMainWindow)
		self.assertEqual(mw1.lastPaperStats, None)
		self.assertGeometry(mw, 0, 0,
			QDesktopWidget().availableGeometry().width(),
			QDesktopWidget().availableGeometry().height())
		self.assertTrue(hasattr(mw, "onIsLockedClass"))
		self.assertIsInstance(mw.onIsLockedClass, ObjectWithSignal)
		self.assertEqual(pBDB.onIsLocked, mw.onIsLockedClass.customSignal)
		with patch(self.clsName + ".lockedDatabase") as _ld:
			pBDB.onIsLocked.emit()
			_ld.assert_called_once_with()

	def test_closeEvent(self):
		"""test closeEvent"""
		e = QEvent(QEvent.Close)
		with patch("physbiblio.databaseCore.PhysBiblioDBCore."
					+ "checkUncommitted", return_value=True) as _c,\
				patch(self.modName + ".askYesNo",
					side_effect=[True, False]) as _a,\
				patch("PySide2.QtCore.QEvent.accept") as _ea,\
				patch("PySide2.QtCore.QEvent.ignore") as _ei:
			self.mainW.closeEvent(e)
			_c.assert_called_once_with()
			_a.assert_called_once_with(
				"There may be unsaved changes to the database.\n"
				+ "Do you really want to exit?")
			_ea.assert_called_once_with()
			self.mainW.closeEvent(e)
			_ei.assert_called_once_with()
		oldcfg = pbConfig.params["askBeforeExit"]
		pbConfig.params["askBeforeExit"] = False
		with patch("physbiblio.databaseCore.PhysBiblioDBCore."
					+ "checkUncommitted", return_value=False) as _c,\
				patch(self.modName + ".askYesNo",
					side_effect=[True, False]) as _a,\
				patch("PySide2.QtCore.QEvent.accept") as _ea,\
				patch("PySide2.QtCore.QEvent.ignore") as _ei:
			self.mainW.closeEvent(e)
			_c.assert_called_once_with()
			_ea.assert_called_once_with()
			_ea.reset_mock()
			pbConfig.params["askBeforeExit"] = True
			self.mainW.closeEvent(e)
			_a.assert_called_once_with(
				"Do you really want to exit?")
			_ea.assert_called_once_with()
			self.mainW.closeEvent(e)
			_ei.assert_called_once_with()
		pbConfig.params["askBeforeExit"] = oldcfg

	def test_mainWindowTitle(self):
		"""test mainWindowTitle"""
		with patch(self.qmwName + ".setWindowTitle") as _t:
			self.mainW.mainWindowTitle("mytitle")
			_t.assert_called_once_with("mytitle")

	def test_printNewVersion(self):
		"""test printNewVersion"""
		with patch("logging.Logger.info") as _i:
			self.mainW.printNewVersion(False, "")
			_i.assert_called_once_with("No new versions available!")
		with patch("logging.Logger.warning") as _w:
			self.mainW.printNewVersion(True, "0.0.0")
			_w.assert_called_once_with("New version available (0.0.0)!\n"
				+ "You can upgrade with `pip install -U physbiblio` "
				+ "(with `sudo`, eventually).")

	def test_lockedDatabase(self):
		"""test lockedDatabase"""
		with patch(self.modName + ".askYesNo",
				side_effect=[True, False]) as _a:
			with self.assertRaises(SystemExit):
				self.mainW.lockedDatabase()
			_a.assert_called_once_with("The database is locked.\n"
				+ "Probably another instance of the program is"
				+ " currently open and you cannot save your changes.\n"
				+ "For this reason, the current instance "
				+ "may not work properly.\n"
				+ "Do you want to close this instance of PhysBiblio?",
				title="Attention!")
			try:
				self.mainW.lockedDatabase()
			except SystemExit:
				self.fail("Unexpected raise")

	def test_setIcon(self):
		"""test setIcon"""
		qi = QIcon(':/images/icon.png')
		with patch(self.modName + ".QIcon", return_value=qi) as _qi,\
				patch(self.qmwName + ".setWindowIcon") as _swi:
			self.mainW.setIcon()
			_qi.assert_called_once_with(':/images/icon.png')
			_swi.assert_called_once_with(qi)

	def test_createActions(self):
		"""test createActions"""
		def assertAction(act, t, tip, trig, s=None, i=None, p=None):
			"""test the properties of a single action

			Parameters:
				act: the QAction to be tested
				t: the title/text
				tip: the status tip
				trig: the name of the triggered function
					(must be a MainWindow method)
				s (default None): the shortcut, if any, or None
				i (default None): the icon filename, if any, or None
				p (default None): the mocked triggered function or None
			"""
			self.assertIsInstance(act, QAction)
			self.assertEqual(act.text(), t)
			if s is not None:
				self.assertEqual(act.shortcut(), s)
			if i is not None:
				img = QImage(i).convertToFormat(
					QImage.Format_ARGB32_Premultiplied)
				self.assertEqual(img,
					act.icon().pixmap(img.size()).toImage())
			self.assertEqual(act.statusTip(), tip)
			if p is None:
				with patch("%s.%s"%(self.clsName, trig)) as _f:
					act.trigger()
					_f.assert_called_once_with()
			else:
				act.trigger()
				p.assert_called_once_with()

		with patch("PySide2.QtWidgets.QMainWindow.close") as _f:
			mw = MainWindow(testing=True)
			mw.createActions()
			assertAction(mw.exitAct,
				"E&xit",
				"Exit application",
				"close",
				s="Ctrl+Q",
				i=":/images/application-exit.png",
				p=_f)

		assertAction(self.mainW.profilesAct,
			"&Profiles",
			"Manage profiles",
			"manageProfiles",
			s="Ctrl+P",
			i=":/images/profiles.png")

		assertAction(self.mainW.editProfileWindowsAct,
			"&Edit profiles",
			"Edit profiles",
			"editProfile",
			s="Ctrl+Alt+P")

		assertAction(self.mainW.undoAct,
			"&Undo",
			"Rollback to last saved database state",
			"undoDB",
			s="Ctrl+Z",
			i=":/images/edit-undo.png")

		assertAction(self.mainW.saveAct,
			"&Save database",
			"Save the modifications",
			"save",
			s="Ctrl+S",
			i=":/images/file-save.png")

		assertAction(self.mainW.importBibAct,
			"&Import from *.bib",
			"Import the entries from a *.bib file",
			"importFromBib",
			s="Ctrl+B")

		assertAction(self.mainW.exportAct,
			"Ex&port last as *.bib",
			"Export last query as *.bib",
			"export",
			i=":/images/export.png")

		assertAction(self.mainW.exportAllAct,
			"Export &all as *.bib",
			"Export complete bibliography as *.bib",
			"exportAll",
			s="Ctrl+A",
			i=":/images/export-table.png")

		assertAction(self.mainW.exportFileAct,
			"Export for a *.&tex",
			"Export as *.bib the bibliography needed "
				+ "to compile a .tex file",
			"exportFile",
			s="Ctrl+X")

		assertAction(self.mainW.exportUpdateAct,
			"Update an existing *.&bib file",
			"Read a *.bib file and update "
				+ "the existing elements inside it",
			"exportUpdate",
			s="Ctrl+Shift+X")

		assertAction(self.mainW.catAct,
			"&Categories",
			"Manage Categories",
			"categories",
			s="Ctrl+T")

		assertAction(self.mainW.newCatAct,
			"Ne&w Category",
			"New Category",
			"newCategory",
			s="Ctrl+Shift+T")

		assertAction(self.mainW.expAct,
			"&Experiments",
			"List of Experiments",
			"experiments",
			s="Ctrl+E")

		assertAction(self.mainW.newExpAct,
			"&New Experiment",
			"New Experiment",
			"newExperiment",
			s="Ctrl+Shift+E")

		assertAction(self.mainW.searchBibAct,
			"&Find Bibtex entries",
			"Open the search dialog to filter the bibtex list",
			"searchBiblio",
			s="Ctrl+F",
			i=":/images/find.png")

		assertAction(self.mainW.searchReplaceAct,
			"&Search and replace bibtexs",
			"Open the search&replace dialog",
			"searchAndReplace",
			s="Ctrl+H")

		assertAction(self.mainW.newBibAct,
			"New &Bib item",
			"New bibliographic item",
			"newBibtex",
			s="Ctrl+N",
			i=":/images/file-add.png")

		assertAction(self.mainW.inspireLoadAndInsertAct,
			"&Load from INSPIRE-HEP",
			"Use INSPIRE-HEP to load and insert bibtex entries",
			"inspireLoadAndInsert",
			s="Ctrl+Shift+I")

		assertAction(self.mainW.inspireLoadAndInsertWithCatsAct,
			"&Load from INSPIRE-HEP (ask categories)",
			"Use INSPIRE-HEP to load and insert bibtex entries, "
				+ "then ask the categories for each",
			"inspireLoadAndInsertWithCats",
			s="Ctrl+I")

		assertAction(self.mainW.advImportAct,
			"&Advanced Import",
			"Open the advanced import window",
			"advancedImport",
			s="Ctrl+Alt+I")

		assertAction(self.mainW.updateAllBibtexsAct,
			"&Update bibtexs",
			"Update all the journal info of bibtexs",
			"updateAllBibtexs",
			s="Ctrl+U")

		assertAction(self.mainW.updateAllBibtexsAskAct,
			"Update bibtexs (&personalized)",
			"Update all the journal info of bibtexs, "
				+ "but with non-standard options (start from, force, ...)",
			"updateAllBibtexsAsk",
			s="Ctrl+Shift+U")

		assertAction(self.mainW.cleanAllBibtexsAct,
			"&Clean bibtexs",
			"Clean all the bibtexs",
			"cleanAllBibtexs",
			s="Ctrl+L")

		assertAction(self.mainW.findBadBibtexsAct,
			"&Find corrupted bibtexs",
			"Find all the bibtexs which contain syntax errors "
				+ "and are not readable",
			"findBadBibtexs",
			s="Ctrl+Shift+B")

		assertAction(self.mainW.infoFromArxivAct,
			"Info from ar&Xiv",
			"Get info from arXiv",
			"infoFromArxiv",
			s="Ctrl+V")

		assertAction(self.mainW.dailyArxivAct,
			"Browse last ar&Xiv listings",
			"Browse most recent arXiv listings",
			"browseDailyArxiv",
			s="Ctrl+D")

		assertAction(self.mainW.cleanAllBibtexsAskAct,
			"C&lean bibtexs (from ...)",
			"Clean all the bibtexs, starting from a given one",
			"cleanAllBibtexsAsk",
			s="Ctrl+Shift+L")

		assertAction(self.mainW.authorStatsAct,
			"&AuthorStats",
			"Search publication and citation stats "
				+ "of an author from INSPIRES",
			"authorStats",
			s="Ctrl+Shift+A")

		assertAction(self.mainW.configAct,
			"Settin&gs",
			"Save the settings",
			"config",
			s="Ctrl+Shift+S",
			i=":/images/settings.png")

		assertAction(self.mainW.refreshAct,
			"&Refresh current entries list",
			"Refresh the current list of entries",
			"refreshMainContent",
			s="F5",
			i=":/images/refresh2.png")

		assertAction(self.mainW.reloadAct,
			"&Reload (reset) main table",
			"Reload the list of bibtex entries",
			"reloadMainContent",
			s="Shift+F5",
			i=":/images/refresh.png")

		assertAction(self.mainW.aboutAct,
			"&About",
			"Show About box",
			"showAbout",
			i=":/images/help-about.png")

		assertAction(self.mainW.logfileAct,
			"Log file",
			"Show the content of the logfile",
			"logfile",
			s="Ctrl+G")

		assertAction(self.mainW.dbstatsAct,
			"&Database info",
			"Show some statistics about the current database",
			"showDBStats",
			i=":/images/stats.png")

		assertAction(self.mainW.cleanSpareAct,
			"&Clean spare entries",
			"Remove spare entries from the connection tables.",
			"cleanSpare")

		assertAction(self.mainW.cleanSparePDFAct,
			"&Clean spare PDF folders",
			"Remove spare PDF folders.",
			"cleanSparePDF")

	def test_createMenusAndToolBar(self):
		"""test createMenusAndToolBar"""
		def assertMenu(menu, title, acts):
			self.assertIsInstance(menu, QMenu)
			self.assertEqual(menu.title(), title)
			macts = menu.actions()
			self.assertEqual(len(macts), len(acts))
			for i, a in enumerate(acts):
				if a is None:
					self.assertTrue(macts[i].isSeparator())
				else:
					self.assertEqual(macts[i], a)

		assertMenu(self.mainW.fileMenu, "&File",
			[self.mainW.undoAct,
			self.mainW.saveAct,
			None,
			self.mainW.exportAct,
			self.mainW.exportFileAct,
			self.mainW.exportAllAct,
			self.mainW.exportUpdateAct,
			None,
			self.mainW.profilesAct,
			self.mainW.editProfileWindowsAct,
			self.mainW.configAct,
			None,
			self.mainW.exitAct])

		assertMenu(self.mainW.bibMenu, "&Bibliography",
			[self.mainW.newBibAct,
			self.mainW.importBibAct,
			self.mainW.inspireLoadAndInsertWithCatsAct,
			self.mainW.inspireLoadAndInsertAct,
			self.mainW.advImportAct,
			None,
			self.mainW.cleanAllBibtexsAct,
			self.mainW.cleanAllBibtexsAskAct,
			self.mainW.findBadBibtexsAct,
			None,
			self.mainW.infoFromArxivAct,
			self.mainW.updateAllBibtexsAct,
			self.mainW.updateAllBibtexsAskAct,
			None,
			self.mainW.searchBibAct,
			self.mainW.searchReplaceAct,
			None,
			self.mainW.refreshAct,
			self.mainW.reloadAct])

		assertMenu(self.mainW.catMenu, "&Categories",
			[self.mainW.catAct,
			self.mainW.newCatAct])

		assertMenu(self.mainW.expMenu, "&Experiments",
			[self.mainW.expAct,
			self.mainW.newExpAct])

		assertMenu(self.mainW.toolMenu, "&Tools",
			[self.mainW.dailyArxivAct,
			None,
			self.mainW.cleanSpareAct,
			self.mainW.cleanSparePDFAct,
			None,
			self.mainW.authorStatsAct])

		assertMenu(self.mainW.helpMenu, "&Help",
			[self.mainW.dbstatsAct,
			self.mainW.logfileAct,
			None,
			self.mainW.aboutAct])

		tb = self.mainW.mainToolBar
		self.assertIsInstance(tb, QToolBar)
		macts = tb.actions()
		acts = [self.mainW.undoAct,
			self.mainW.saveAct,
			None,
			self.mainW.newBibAct,
			self.mainW.searchBibAct,
			self.mainW.searchReplaceAct,
			self.mainW.exportAct,
			self.mainW.exportAllAct,
			None,
			self.mainW.refreshAct,
			self.mainW.reloadAct,
			None,
			self.mainW.configAct,
			self.mainW.dbstatsAct,
			self.mainW.aboutAct,
			None,
			self.mainW.exitAct]
		self.assertEqual(len(macts), len(acts))
		for i, a in enumerate(acts):
			if a is None:
				self.assertTrue(macts[i].isSeparator())
			else:
				self.assertEqual(macts[i], a)
		self.assertEqual(tb.windowTitle(), "Toolbar")

		#test empty search/replace menu
		with patch("physbiblio.config.GlobalDB.getSearchList",
				side_effect=[[], []]) as _gs,\
				patch(self.clsName + ".convertSearchFormat") as _csf:
			self.mainW.createMenusAndToolBar()
			_csf.assert_called_once_with()
			self.assertEqual(self.mainW.searchMenu, None)
			self.assertEqual(self.mainW.replaceMenu, None)
		#test order of menus
		self.assertEqual([a.menu() for a in self.mainW.menuBar().actions()],
			[self.mainW.fileMenu,
			self.mainW.bibMenu,
			self.mainW.catMenu,
			self.mainW.expMenu,
			self.mainW.toolMenu,
			self.mainW.helpMenu])

		#create with mock getSearchList for searches and replaces
		with patch("physbiblio.config.GlobalDB.getSearchList",
				side_effect=[
					[{"idS": 0, "name": "s1", "searchDict": "{'n': 'abc'}",
						"limitNum": 101, "offsetNum": 99},
					{"idS": 1, "name": "s2", "searchDict": "{'n': 'def'}",
						"limitNum": 102, "offsetNum": 100}],
					[{"idS": 2, "name": "s3", "searchDict": "{'n': 'ghi'}",
						"replaceFields": "['a', 'b']", "offsetNum": 1},
					{"idS": 3, "name": "s4", "searchDict": "{'n': 'jkl'}",
						"replaceFields": "['c', 'd']", "offsetNum": 2}]
					]) as _gs:
			self.mainW.createMenusAndToolBar()
			self.assertIsInstance(self.mainW.searchMenu, QMenu)
			self.assertEqual(self.mainW.searchMenu.title(),
				"Frequent &searches")
			macts = self.mainW.searchMenu.actions()
			acts = [
				["s1", self.clsName + ".runSearchBiblio",
					[{'n': 'abc'}, 101, 99]],
				["s2", self.clsName + ".runSearchBiblio",
					[{'n': 'def'}, 102, 100]],
				None,
				["Manage 's1'", [
					["Edit 's1'", self.clsName + ".editSearchBiblio",
						[0, "s1"]],
					["Delete 's1'", self.clsName + ".delSearchBiblio",
						[0, "s1"]]
					]
				],
				["Manage 's2'", [
					["Edit 's2'", self.clsName + ".editSearchBiblio",
						[1, "s2"]],
					["Delete 's2'", self.clsName + ".delSearchBiblio",
						[1, "s2"]]
					],
				]]
			for i, a in enumerate(acts):
				if a is None:
					self.assertTrue(macts[i].isSeparator())
				elif isinstance(a[1], list):
					self.assertEqual(macts[i].text(), a[0])
					mas = macts[i].menu().actions()
					for j, b in enumerate(a[1]):
						self.assertEqual(mas[j].text(), b[0])
						with patch(b[1]) as _f:
							mas[j].trigger()
							_f.assert_called_once_with(*b[2])
				else:
					self.assertEqual(macts[i].text(), a[0])
					with patch(a[1]) as _f:
						macts[i].trigger()
						_f.assert_called_once_with(*a[2])
			self.assertIsInstance(self.mainW.replaceMenu, QMenu)
			self.assertEqual(self.mainW.replaceMenu.title(),
				"Frequent &replaces")
			macts = self.mainW.replaceMenu.actions()
			acts = [
				["s3", self.clsName + ".runSearchReplaceBiblio",
					[{'n': 'ghi'}, ['a', 'b'], 1]],
				["s4", self.clsName + ".runSearchReplaceBiblio",
					[{'n': 'jkl'}, ['c', 'd'], 2]],
				None,
				["Manage 's3'", [
					["Edit 's3'", self.clsName + ".editSearchBiblio",
						[2, "s3"]],
					["Delete 's3'", self.clsName + ".delSearchBiblio",
						[2, "s3"]]
					]
				],
				["Manage 's4'", [
					["Edit 's4'", self.clsName + ".editSearchBiblio",
						[3, "s4"]],
					["Delete 's4'", self.clsName + ".delSearchBiblio",
						[3, "s4"]]
					],
				]]
			for i, a in enumerate(acts):
				if a is None:
					self.assertTrue(macts[i].isSeparator())
				elif isinstance(a[1], list):
					self.assertEqual(macts[i].text(), a[0])
					mas = macts[i].menu().actions()
					for j, b in enumerate(a[1]):
						self.assertEqual(mas[j].text(), b[0])
						with patch(b[1]) as _f:
							mas[j].trigger()
							_f.assert_called_once_with(*b[2])
				else:
					self.assertEqual(macts[i].text(), a[0])
					with patch(a[1]) as _f:
						macts[i].trigger()
						_f.assert_called_once_with(*a[2])
		#test order of menus with and without s&r
		self.assertEqual([a.menu() for a in self.mainW.menuBar().actions()],
			[self.mainW.fileMenu,
			self.mainW.bibMenu,
			self.mainW.catMenu,
			self.mainW.expMenu,
			self.mainW.toolMenu,
			self.mainW.searchMenu,
			self.mainW.replaceMenu,
			self.mainW.helpMenu])

	def test_createMainLayout(self):
		"""test createMainLayout"""
		self.assertIsInstance(self.mainW.bibtexListWindow, BibtexListWindow)
		self.assertEqual(self.mainW.bibtexListWindow.frameShape(),
			QFrame.StyledPanel)
		self.assertIsInstance(self.mainW.bottomLeft, BibtexInfo)
		self.assertEqual(self.mainW.bottomLeft.frameShape(),
			QFrame.StyledPanel)
		self.assertIsInstance(self.mainW.bottomCenter, BibtexInfo)
		self.assertEqual(self.mainW.bottomCenter.frameShape(),
			QFrame.StyledPanel)
		self.assertIsInstance(self.mainW.bottomRight, BibtexInfo)
		self.assertEqual(self.mainW.bottomRight.frameShape(),
			QFrame.StyledPanel)

		spl = self.mainW.centralWidget()
		self.assertIsInstance(spl, QSplitter)
		self.assertEqual(spl.orientation(), Qt.Vertical)
		self.assertEqual(spl.widget(0), self.mainW.bibtexListWindow)
		self.assertEqual(spl.widget(0).sizePolicy().verticalStretch(), 3)
		self.assertIsInstance(spl.widget(1), QSplitter)
		self.assertEqual(spl.widget(1).sizePolicy().verticalStretch(), 1)
		spl1 = spl.widget(1)
		self.assertEqual(spl1.orientation(), Qt.Horizontal)
		self.assertEqual(spl1.widget(0), self.mainW.bottomLeft)
		self.assertEqual(spl1.widget(1), self.mainW.bottomCenter)
		self.assertEqual(spl1.widget(2), self.mainW.bottomRight)
		self.assertGeometry(spl, 0, 0,
			QDesktopWidget().availableGeometry().width(),
			QDesktopWidget().availableGeometry().height())

	def test_undoDB(self):
		"""test undoDB"""
		with patch("physbiblio.databaseCore.PhysBiblioDBCore.undo") as _u,\
				patch(self.qmwName + ".setWindowTitle") as _swt,\
				patch(self.clsName + ".reloadMainContent") as _rmc:
			self.mainW.undoDB()
			_u.assert_called_once_with()
			_swt.assert_called_once_with('PhysBiblio')
			_rmc.assert_called_once_with()

	def test_refreshMainContent(self):
		"""test refreshMainContent"""
		pBDB.bibs.lastFetched = []
		with patch(self.clsName + ".done") as _d,\
				patch("physbiblio.gui.bibWindows.BibtexListWindow."
					+ "recreateTable") as _rt,\
				patch(self.clsName + ".statusBarMessage") as _sbm,\
				patch("physbiblio.database.Entries.fetchFromLast",
					return_value=pBDB.bibs) as _fl:
			self.mainW.refreshMainContent()
			_d.assert_called_once_with()
			_sbm.assert_called_once_with("Reloading main table...")
			_fl.assert_called_once_with()
			_rt.assert_called_once_with([])

	def test_reloadMainContent(self):
		"""test reloadMainContent"""
		with patch(self.clsName + ".done") as _d,\
				patch("physbiblio.gui.bibWindows.BibtexListWindow."
					+ "recreateTable") as _rt,\
				patch(self.clsName + ".statusBarMessage") as _sbm:
			self.mainW.reloadMainContent(bibs="fake")
			_d.assert_called_once_with()
			_sbm.assert_called_once_with("Reloading main table...")
			_rt.assert_called_once_with("fake")
			_rt.reset_mock()
			self.mainW.reloadMainContent()
			_rt.assert_called_once_with(None)

	def test_manageProfiles(self):
		"""test manageProfiles"""
		sp = SelectProfiles(self.mainW)
		sp.exec_ = MagicMock()
		with patch(self.modName + ".SelectProfiles",
				return_value=sp) as _i:
			self.mainW.manageProfiles()
			_i.assert_called_once_with(self.mainW)
			sp.exec_.assert_called_once_with()

	def test_editProfile(self):
		"""test editProfile"""
		with patch(self.modName + ".editProfile") as _e:
			self.mainW.editProfile()
			_e.assert_called_once_with(self.mainW)

	def test_config(self):
		"""test config"""
		cw = ConfigWindow(self.mainW)
		cw.exec_ = MagicMock()
		cw.result = False
		with patch(self.clsName + ".statusBarMessage") as _sbm,\
				patch(self.modName + ".ConfigWindow",
					return_value=cw) as _cw:
			self.mainW.config()
			_cw.assert_called_once_with(self.mainW)
			cw.exec_.assert_called_once()
			_sbm.assert_called_once_with("Changes discarded")
		cw.result = True
		with patch(self.clsName + ".statusBarMessage") as _sbm,\
				patch(self.modName + ".ConfigWindow",
					return_value=cw) as _cw,\
				patch("logging.Logger.info") as _in,\
				patch("logging.Logger.debug") as _de,\
				patch("physbiblio.config.ConfigurationDB.update") as _cup,\
				patch("physbiblio.config.ConfigVars.readConfig") as _rdc,\
				patch(self.clsName + ".reloadConfig") as _rlc,\
				patch(self.clsName + ".refreshMainContent") as _rmc,\
				patch("physbiblio.database.PhysBiblioDB.commit") as _com:
			self.mainW.config()
			_sbm.assert_called_once_with("No changes requested")
			_in.assert_not_called()
			_cup.assert_not_called()
			_rdc.assert_not_called()
			_rlc.assert_not_called()
			_rmc.assert_not_called()
			_com.assert_not_called()
		old = {}
		new = {}
		for k, v in cw.textValues:
			if k == "maxAuthorSave":
				new[k] = "12314"
				v.setText(new[k])
				old[k] = pbConfig.params[k]
			elif k == "askBeforeExit":
				old[k] = pbConfig.params[k]
				if pbConfig.params[k] != "True":
					v.setCurrentText("True")
					new[k] = "True"
				else:
					v.setCurrentText("False")
					new[k] = "False"
			elif k == "loggingLevel":
				old[k] = pbConfig.params[k]
				if pbConfig.params[k] != 3:
					v.setCurrentText("3 - all")
					new[k] = "3"
				else:
					v.setCurrentText("2 - info")
					new[k] = "2"
		with patch(self.clsName + ".statusBarMessage") as _sbm,\
				patch(self.modName + ".ConfigWindow",
					return_value=cw) as _cw,\
				patch("logging.Logger.info") as _in,\
				patch("logging.Logger.debug") as _de,\
				patch("physbiblio.config.ConfigurationDB.update") as _cup,\
				patch("physbiblio.config.ConfigVars.readConfig") as _rdc,\
				patch(self.clsName + ".reloadConfig") as _rlc,\
				patch(self.clsName + ".refreshMainContent") as _rmc,\
				patch("physbiblio.database.PhysBiblioDB.commit") as _com:
			self.mainW.config()
			_sbm.assert_called_once_with('Configuration saved')
			self.assertEqual(_de.call_count+1, len(pbConfig.params.keys()))
			for k in old.keys():
				_in.assert_has_calls([call(u"New value for param "
					"%s = %s (old: '%s')"%(k, new[k], old[k]))])
				_cup.assert_has_calls([call(k, new[k])])
			_rdc.assert_called_once_with()
			_rlc.assert_called_once_with()
			_rmc.assert_called_once_with()
			_com.assert_called_once_with()

	def test_logfile(self):
		"""test logfile"""
		with patch("logging.Logger.exception") as _e:
			ld = LogFileContentDialog(self.mainW)
		ld.exec_ = MagicMock()
		with patch(self.modName + ".LogFileContentDialog",
				return_value=ld) as _i:
			self.mainW.logfile()
			_i.assert_called_once_with(self.mainW)
			ld.exec_.assert_called_once_with()

	def test_reloadConfig(self):
		"""test reloadConfig"""
		oldWebA = pbConfig.params["webApplication"]
		oldPdfA = pbConfig.params["pdfApplication"]
		oldPdfF = pbConfig.params["pdfFolder"]
		oldPdfD = pBPDF.pdfDir
		pbConfig.params["webApplication"] = "webApp"
		pbConfig.params["pdfApplication"] = "pdfApp"
		pbConfig.params["pdfFolder"] = "pdf/folder"
		with patch(self.clsName + ".statusBarMessage") as _sbm,\
				patch("physbiblio.gui.bibWindows.BibtexListWindow."
					+ "reloadColumnContents") as _rcc:
			self.mainW.reloadConfig()
			_sbm.assert_called_once_with("Reloading configuration...")
			_rcc.assert_called_once_with()
			self.assertEqual(pBView.webApp, "webApp")
			self.assertEqual(pBPDF.pdfApp, "pdfApp")
			self.assertEqual(pBPDF.pdfDir,
				os.path.join(os.path.split(
				os.path.abspath(sys.argv[0]))[0],
				"pdf/folder"))
		pbConfig.params["webApplication"] = "webApp"
		pbConfig.params["pdfApplication"] = "pdfApp"
		pbConfig.params["pdfFolder"] = "/pdf/folder"
		with patch(self.clsName + ".statusBarMessage") as _sbm,\
				patch("physbiblio.gui.bibWindows.BibtexListWindow."
					+ "reloadColumnContents") as _rcc:
			self.mainW.reloadConfig()
			_sbm.assert_called_once_with("Reloading configuration...")
			_rcc.assert_called_once_with()
			self.assertEqual(pBView.webApp, "webApp")
			self.assertEqual(pBPDF.pdfApp, "pdfApp")
			self.assertEqual(pBPDF.pdfDir, "/pdf/folder")
		pbConfig.params["webApplication"] = oldWebA
		pbConfig.params["pdfApplication"] = oldPdfA
		pbConfig.params["pdfFolder"] = oldPdfF
		with patch(self.clsName + ".statusBarMessage") as _sbm,\
				patch("physbiblio.gui.bibWindows.BibtexListWindow."
					+ "reloadColumnContents") as _rcc:
			self.mainW.reloadConfig()
		pBPDF.pdfDir = oldPdfD

	def test_showAbout(self):
		"""test showAbout"""
		mbox = self.mainW.showAbout(testing=True)
		self.assertEqual(mbox.windowTitle(), "About PhysBiblio")
		self.assertEqual(mbox.text(),
			"PhysBiblio (<a href='https://github.com/steog88/physBiblio'>"
			+ "https://github.com/steog88/physBiblio</a>) is "
			+ "a cross-platform tool for managing a LaTeX/BibTeX database. "
			+ "It is written in <code>python</code>, "
			+ "using <code>sqlite3</code> for the database management "
			+ "and <code>PySide</code> for the graphical part."
			+ "<br>"
			+ "It supports grouping, tagging, import/export, "
			+ "automatic update and various different other functions."
			+ "<br><br>"
			+ "<b>Paths:</b><br>"
			+ "<i>Configuration:</i> %s<br>"%pbConfig.configPath
			+ "<i>Data:</i> %s<br>"%pbConfig.dataPath
			+ "<br>"
			+ "<b>Author:</b> Stefano Gariazzo "
			+ "<i>&lt;stefano.gariazzo@gmail.com&gt;</i><br>"
			+ "<b>Version:</b> %s (%s)<br>"%(
				physbiblio.__version__, physbiblio.__version_date__)
			+ "<b>Python version</b>: %s"%sys.version)
		self.assertEqual(mbox.textFormat(), Qt.RichText)
		img = QImage(":/images/icon.png").convertToFormat(
			QImage.Format_ARGB32_Premultiplied)
		self.assertEqual(img, mbox.iconPixmap().toImage())

		mb = QMessageBox(QMessageBox.Information, "title", "PhysBiblio")
		mb.exec_ = MagicMock()
		with patch(self.modName + ".QMessageBox", return_value=mb) as _mb:
			self.mainW.showAbout()
			mb.exec_.assert_called_once_with()

	def test_showDBStats(self):
		"""test showDBStats"""
		dbStats(pBDB)
		with patch(self.modName + ".dbStats") as _dbs,\
				patch("physbiblio.pdf.LocalPDF.dirSize",
					return_value=4096**2) as _ds,\
				patch("glob.iglob", return_value=["a", "b"]) as _ig:
			mbox = self.mainW.showDBStats(testing=True)
			_dbs.assert_called_once_with(pBDB)
			_ig.assert_called_once_with("%s/*/*.pdf"%pBPDF.pdfDir)
			_ds.assert_called_once_with(pBPDF.pdfDir)
		self.assertEqual(mbox.windowTitle(), "PhysBiblio database statistics")
		self.assertEqual(mbox.text(),
			"The PhysBiblio database currently contains "
			+ "the following number of records:\n"
			+ "- %d bibtex entries\n"%(pBDB.stats["bibs"])
			+ "- %d categories\n"%(pBDB.stats["cats"])
			+ "- %d experiments,\n"%(pBDB.stats["exps"])
			+ "- %d bibtex entries to categories connections\n"%(
				pBDB.stats["catBib"])
			+ "- %d experiment to categories connections\n"%(
				pBDB.stats["catExp"])
			+ "- %d bibtex entries to experiment connections.\n\n"%(
				pBDB.stats["bibExp"])
			+ "The number of currently stored PDF files is 2.\n"
			+ "The size of the PDF folder is 16.00MB.")
		img = QImage(":/images/icon.png").convertToFormat(
			QImage.Format_ARGB32_Premultiplied)
		self.assertEqual(img, mbox.iconPixmap().toImage())
		self.assertEqual(mbox.parent(), self.mainW)

		mb = QMessageBox(QMessageBox.Information, "title", "PhysBiblio")
		mb.show = MagicMock()
		with patch(self.modName + ".QMessageBox", return_value=mb) as _mb:
			self.mainW.showDBStats()
			mb.show.assert_called_once_with()

	def test_runInThread(self):
		"""test _runInThread"""
		app = PrintText()
		app.exec_ = MagicMock()
		self.assertTrue(hasattr(app, "stopped"))
		app.stopped = MagicMock()
		app.stopped.connect = MagicMock()
		q = Queue()
		ws = WriteStream(q)
		self.assertTrue(hasattr(ws, "newText"))
		self.assertTrue(hasattr(ws, "finished"))
		ws.newText = MagicMock()
		ws.finished = MagicMock()
		ws.newText.connect = MagicMock()
		ws.finished.connect = MagicMock()
		thr = Thread_cleanSpare(ws, parent=self.mainW)#just use one
		thr.start = MagicMock()
		thr.finished = MagicMock()
		thr.finished.connect = MagicMock()
		func = MagicMock(return_value=thr)
		with patch(self.modName + ".PrintText",
				return_value=app) as _pt,\
				patch("physbiblio.gui.dialogWindows.PrintText"
					+ ".progressBarMin") as _pbm,\
				patch(self.modName + ".Queue", return_value=q) as _qu,\
				patch(self.modName + ".WriteStream", return_value=ws) as _ws,\
				patch("physbiblio.errors.PBErrorManagerClass"
					+ ".tempHandler") as _th,\
				patch("physbiblio.errors.PBErrorManagerClass"
					+ ".rmTempHandler") as _rth,\
				patch("logging.Logger.info") as _info,\
				patch(self.clsName + ".statusBarMessage") as _sbm,\
				patch(self.clsName + ".done") as _done:
			self.mainW._runInThread(func, "title")
			_pt.assert_called_once_with(noStopButton=False,
				progrStr=None, title='title', totStr=None)
			_pbm.assert_not_called()
			ws.newText.connect.assert_called_once_with(app.appendText)
			func.assert_called_once_with(ws, parent=self.mainW)
			ws.finished.connect.assert_called_once_with(ws.deleteLater)
			thr.finished.connect.assert_has_calls([
				call(app.enableClose),
				call(thr.deleteLater)])
			app.stopped.connect.assert_not_called()
			_th.assert_called_once_with(ws, format='%(message)s')
			thr.start.assert_called_once_with()
			app.exec_.assert_called_once_with()
			_info.assert_called_once_with('Closing...')
			_rth.assert_called_once_with()
			_sbm.assert_not_called()
			_done.assert_called_once_with()
		ws.newText.connect.reset_mock()
		func.reset_mock()
		ws.finished.connect.reset_mock()
		thr.finished.connect.reset_mock()
		app.stopped.connect.reset_mock()
		thr.start.reset_mock()
		app.exec_.reset_mock()
		with patch(self.modName + ".PrintText",
				return_value=app) as _pt,\
				patch("physbiblio.gui.dialogWindows.PrintText"
					+ ".progressBarMin") as _pbm,\
				patch(self.modName + ".Queue", return_value=q) as _qu,\
				patch(self.modName + ".WriteStream", return_value=ws) as _ws,\
				patch("physbiblio.errors.PBErrorManagerClass"
					+ ".tempHandler") as _th,\
				patch("physbiblio.errors.PBErrorManagerClass"
					+ ".rmTempHandler") as _rth,\
				patch("logging.Logger.info") as _info,\
				patch(self.clsName + ".statusBarMessage") as _sbm,\
				patch(self.clsName + ".done") as _done:
			self.mainW._runInThread(func, "title", "abc",
				totStr="tot", progrStr="progr",
				addMessage="add", stopFlag=True,
				outMessage="out", minProgress=12)
			_pt.assert_called_once_with(noStopButton=False,
				progrStr="progr", title='title', totStr="tot")
			_pbm.assert_called_once_with(12)
			ws.newText.connect.assert_called_once_with(app.appendText)
			func.assert_called_once_with(ws, "abc", parent=self.mainW)
			ws.finished.connect.assert_called_once_with(ws.deleteLater)
			thr.finished.connect.assert_has_calls([
				call(app.enableClose),
				call(thr.deleteLater)])
			app.stopped.connect.assert_called_once_with(thr.setStopFlag)
			_th.assert_called_once_with(ws, format='%(message)s')
			thr.start.assert_called_once_with()
			app.exec_.assert_called_once_with()
			_info.assert_has_calls([call("add"), call('Closing...')])
			_rth.assert_called_once_with()
			_sbm.assert_called_once_with("out")
			_done.assert_not_called()

	def test_cleanSpare(self):
		"""test cleanSpare"""
		with patch(self.clsName + "._runInThread") as _rit:
			self.mainW.cleanSpare()
			_rit.assert_called_once_with(
				Thread_cleanSpare, "Clean spare entries")

	def test_cleanSparePDF(self):
		"""test cleanSparePDF"""
		with patch(self.clsName + "._runInThread") as _rit,\
				patch(self.modName + ".askYesNo",
					return_value=True):
			self.mainW.cleanSparePDF()
			_rit.assert_called_once_with(
				Thread_cleanSparePDF, "Clean spare PDF folders")
		with patch(self.clsName + "._runInThread") as _rit,\
				patch(self.modName + ".askYesNo",
					return_value=False):
			self.mainW.cleanSparePDF()
			_rit.assert_not_called()

	def test_createStatusBar(self):
		"""test createStatusBar"""
		with patch(self.modName + ".QStatusBar.showMessage") as _sm:
			self.mainW.createStatusBar()
			_sm.assert_called_once_with('Ready', 0)
			self.assertEqual(self.mainW.statusBar(), self.mainW.mainStatusBar)

	def test_statusBarMessage(self):
		"""test statusBarMessage"""
		with patch(self.modName + ".QStatusBar.showMessage") as _sm,\
				patch("logging.Logger.info") as _i:
			self.mainW.statusBarMessage("abc")
			_i.assert_called_once_with("abc")
			_sm.assert_called_once_with("abc", 4000)
			_sm.reset_mock()
			self.mainW.statusBarMessage("abc", time=2000)
			_sm.assert_called_once_with("abc", 2000)

	def test_save(self):
		"""test save"""
		with patch(self.modName + ".askYesNo",
				side_effect=[True, False]) as _ayn,\
				patch(self.clsName + ".statusBarMessage") as _sbm,\
				patch(self.clsName + ".mainWindowTitle") as _mwt,\
				patch("physbiblio.database.PhysBiblioDBCore.commit") as _c:
			self.mainW.save()
			_ayn.assert_called_once_with("Do you really want to save?")
			_sbm.assert_called_once_with("Changes saved")
			_mwt.assert_called_once_with("PhysBiblio")
			_c.assert_called_once_with()
			_ayn.reset_mock()
			_sbm.reset_mock()
			_mwt.reset_mock()
			_c.reset_mock()
			self.mainW.save()
			_ayn.assert_called_once_with("Do you really want to save?")
			_sbm.assert_called_once_with("Nothing saved")
			_mwt.assert_not_called()
			_c.assert_not_called()

	def test_importFromBib(self):
		"""test importFromBib"""
		with patch(self.modName + ".askFileName",
				side_effect=["a.bib", ""]) as _afn,\
				patch(self.modName + ".askYesNo", return_value=True) as _ayn,\
				patch(self.clsName + "._runInThread") as _rit,\
				patch(self.clsName + ".statusBarMessage") as _sbm,\
				patch(self.clsName + ".reloadMainContent") as _rmc:
			self.mainW.importFromBib()
			_afn.assert_called_once_with(self.mainW,
				title="From where do you want to import?",
				filter="Bibtex (*.bib)")
			_rit.assert_called_once_with(
				Thread_importFromBib,
				"Importing...", "a.bib", True,
				totStr="Entries to be processed: ",
				progrStr="%), processing entry ",
				minProgress=0, stopFlag=True,
				outMessage="All entries into 'a.bib' have been imported")
			_ayn.assert_called_once_with("Do you want to use INSPIRE "
				+ "to find more information about the imported entries?")
			_sbm.assert_called_once_with("File 'a.bib' imported!")
			_rmc.assert_called_once_with()
			_rit.reset_mock()
			_sbm.reset_mock()
			self.mainW.importFromBib()
			_rit.assert_not_called()
			_sbm.assert_called_once_with("Empty filename given!")

	def test_export(self):
		"""test export"""
		with patch(self.modName + ".askSaveFileName",
				side_effect=["a.bib", ""]) as _afn,\
				patch("physbiblio.export.PBExport.exportLast") as _ex,\
				patch(self.clsName + ".statusBarMessage") as _sbm:
			self.mainW.export()
			_afn.assert_called_once_with(self.mainW,
				title="Where do you want to export the entries?",
				filter="Bibtex (*.bib)")
			_ex.assert_called_once_with("a.bib")
			_sbm.assert_called_once_with(
				"Last fetched entries exported into 'a.bib'")
			_ex.reset_mock()
			_sbm.reset_mock()
			self.mainW.export()
			_ex.assert_not_called()
			_sbm.assert_called_once_with("Empty filename given!")

	def test_exportSelection(self):
		"""test exportSelection"""
		with patch(self.modName + ".askSaveFileName",
				side_effect=["a.bib", ""]) as _afn,\
				patch("physbiblio.export.PBExport.exportSelected") as _ex,\
				patch(self.clsName + ".statusBarMessage") as _sbm:
			self.mainW.exportSelection([{"bibkey": "k"}])
			_afn.assert_called_once_with(self.mainW,
				title="Where do you want to export the selected entries?",
				filter="Bibtex (*.bib)")
			_ex.assert_called_once_with("a.bib", [{"bibkey": "k"}])
			_sbm.assert_called_once_with(
				"Current selection exported into 'a.bib'")
			_ex.reset_mock()
			_sbm.reset_mock()
			self.mainW.exportSelection([{"bibkey": "k"}])
			_ex.assert_not_called()
			_sbm.assert_called_once_with("Empty filename given!")

	def test_exportFile(self):
		"""test exportFile"""
		with patch(self.modName + ".askSaveFileName",
				side_effect=["a.bib", "a.bib", ""]) as _asn,\
				patch(self.modName + ".askFileNames",
					side_effect=[["a.tex", "b.tex"], ""]) as _afn,\
				patch(self.clsName + "._runInThread") as _ex,\
				patch(self.clsName + ".statusBarMessage") as _sbm:
			self.mainW.exportFile()
			_asn.assert_called_once_with(self.mainW,
				title="Where do you want to export the entries?",
				filter="Bibtex (*.bib)"),
			_afn.assert_called_once_with(self.mainW,
				title="Which is/are the *.tex file(s) you want to compile?",
				filter="Latex (*.tex)")
			_ex.assert_called_once_with(
					Thread_exportTexBib, "Exporting...",
					["a.tex", "b.tex"], "a.bib",
					minProgress=0, stopFlag=True,
					outMessage="All entries saved into 'a.bib'")
			_ex.reset_mock()
			self.mainW.exportFile()
			_ex.assert_not_called()
			_sbm.assert_called_once_with("Empty input filename/folder!")
			_ex.reset_mock()
			_sbm.reset_mock()
			self.mainW.exportFile()
			_ex.assert_not_called()
			_sbm.assert_called_once_with("Empty output filename!")

	def test_exportUpdate(self):
		"""test exportUpdate"""
		with patch(self.modName + ".askSaveFileName",
				side_effect=["a.bib", ""]) as _afn,\
				patch(self.modName + ".askYesNo", return_value="a") as _ayn,\
				patch("physbiblio.export.PBExport.updateExportedBib") as _ex,\
				patch(self.clsName + ".statusBarMessage") as _sbm:
			self.mainW.exportUpdate()
			_afn.assert_called_once_with(self.mainW,
				 title="File to update?",
				filter="Bibtex (*.bib)")
			_ayn.assert_called_once_with(
				"Do you want to overwrite the existing .bib file?",
				"Overwrite")
			_ex.assert_called_once_with("a.bib", overwrite="a")
			_sbm.assert_called_once_with(
				"File 'a.bib' updated")
			_ex.reset_mock()
			_sbm.reset_mock()
			self.mainW.exportUpdate()
			_ex.assert_not_called()
			_sbm.assert_called_once_with("Empty output filename!")

	def test_exportAll(self):
		"""test exportAll"""
		with patch(self.modName + ".askSaveFileName",
				side_effect=["a.bib", ""]) as _afn,\
				patch("physbiblio.export.PBExport.exportAll") as _ex,\
				patch(self.clsName + ".statusBarMessage") as _sbm:
			self.mainW.exportAll()
			_afn.assert_called_once_with(self.mainW,
				title="Where do you want to export the entries?",
				filter="Bibtex (*.bib)")
			_ex.assert_called_once_with("a.bib")
			_sbm.assert_called_once_with(
				"All entries saved into 'a.bib'")
			_ex.reset_mock()
			_sbm.reset_mock()
			self.mainW.exportAll()
			_ex.assert_not_called()
			_sbm.assert_called_once_with("Empty output filename!")

	def test_categories(self):
		"""test categories"""
		ca = CatsTreeWindow(self.mainW)
		ca.show = MagicMock()
		with patch(self.clsName + ".statusBarMessage") as _sm,\
				patch(self.modName + ".CatsTreeWindow",
					return_value=ca) as _i:
			self.mainW.categories()
			_sm.assert_called_once_with("categories triggered")
			_i.assert_called_once_with(self.mainW)
			ca.show.assert_called_once_with()

	def test_newCategory(self):
		"""test newCategory"""
		with patch(self.modName + ".editCategory") as _f:
			self.mainW.newCategory()
			_f.assert_called_once_with(self.mainW, self.mainW)

	def test_experiments(self):
		"""test experiments"""
		ex = ExpsListWindow(self.mainW)
		ex.show = MagicMock()
		with patch(self.clsName + ".statusBarMessage") as _sm,\
				patch(self.modName + ".ExpsListWindow",
					return_value=ex) as _i:
			self.mainW.experiments()
			_sm.assert_called_once_with("experiments triggered")
			_i.assert_called_once_with(self.mainW)
			ex.show.assert_called_once_with()

	def test_newExperiment(self):
		"""test newExperiment"""
		with patch(self.modName + ".editExperiment") as _f:
			self.mainW.newExperiment()
			_f.assert_called_once_with(self.mainW, self.mainW)

	def test_newBibtex(self):
		"""test newBibtex"""
		with patch(self.modName + ".editBibtex") as _f:
			self.mainW.newBibtex()
			_f.assert_called_once_with(self.mainW)

	def test_searchBiblio(self):
		"""test searchBiblio"""
		sbw = SearchBibsWindow(self.mainW)
		sbw.exec_ = MagicMock()
		self.assertFalse(sbw.result)
		with patch(self.modName + ".SearchBibsWindow", return_value=sbw
				) as _sbw:
			self.assertEqual(self.mainW.searchBiblio(), None)
			_sbw.assert_called_once_with(self.mainW, replace=False)
			sbw.exec_.assert_called_once_with()
		sbw.onOk()
		self.assertFalse(sbw.save)
		with patch(self.modName + ".SearchBibsWindow", return_value=sbw
				) as _sbw,\
				patch("physbiblio.config.GlobalDB.updateSearchOrder") as _us,\
				patch("physbiblio.config.GlobalDB.insertSearch") as _is,\
				patch(self.clsName + ".runSearchBiblio") as _rsb:
			self.assertEqual(self.mainW.searchBiblio(), None)
			_rsb.assert_called_once_with(
				[{'type': 'Text', 'logical': None, 'field': 'bibtex',
					'operator': 'contains', 'content': ''}],
				100, 0)
			_is.assert_called_once_with(count=0, manual=False,
				limit=100, offset=0, replacement=False,
				searchFields=[{'type': 'Text', 'logical': None,
				'field': 'bibtex', 'operator': 'contains', 'content': ''}])
			_us.assert_called_once_with()
		sbw.textValues[0]["type"].setCurrentText("Categories")
		sbw.limitValue.setText("444")
		sbw.limitOffs.setText("123")
		sbw.onSave()
		self.assertTrue(sbw.save)
		with patch(self.modName + ".SearchBibsWindow", return_value=sbw
				) as _sbw,\
				patch(self.clsName + ".runSearchBiblio") as _rsb,\
				patch("physbiblio.config.GlobalDB.updateSearchOrder") as _us,\
				patch("physbiblio.config.GlobalDB.insertSearch") as _is,\
				patch(self.clsName + ".createMenusAndToolBar") as _cm,\
				patch(self.modName + ".askGenericText",
					side_effect=[["abc", False], ["", True], ["def", True]]
					) as _agt:
			self.assertEqual(self.mainW.searchBiblio(), None)
			_rsb.assert_called_once_with(
				[{'type': 'Categories', 'logical': None, 'field': '',
					'operator': 'all the following', 'content': []}],
				444, 123)
			_is.assert_not_called()
			_cm.assert_not_called()
			_agt.assert_called_once_with(
				'Insert a name / short description to be able to '
				+ 'recognise this search in the future:',
				'Search name', parent=self.mainW)
			_rsb.reset_mock()
			self.assertEqual(self.mainW.searchBiblio(), None)
			self.assertEqual(_agt.call_count, 3)
			_is.assert_called_once_with(
				count=0, manual=True, name='def',
				limit=444, offset=123, replacement=False,
				searchFields=[{'type': 'Categories', 'logical': None,
				'field': '', 'operator': 'all the following', 'content': []}])
			_cm.assert_called_once_with()
			_rsb.assert_called_once_with(
				[{'type': 'Categories', 'logical': None, 'field': '',
					'operator': 'all the following', 'content': []}],
				444, 123)
			_us.assert_not_called()

		# replace=True
		sbw = SearchBibsWindow(self.mainW, replace=True)
		sbw.exec_ = MagicMock()
		self.assertFalse(sbw.result)
		with patch(self.modName + ".SearchBibsWindow", return_value=sbw
				) as _sbw:
			self.assertFalse(self.mainW.searchBiblio(replace=True))
			_sbw.assert_called_once_with(self.mainW, replace=True)
			sbw.exec_.assert_called_once_with()
		sbw.onOk()
		self.assertFalse(sbw.save)
		with patch(self.modName + ".SearchBibsWindow", return_value=sbw
				) as _sbw,\
				patch(self.clsName + ".runSearchBiblio") as _rsb,\
				patch("physbiblio.config.GlobalDB.updateSearchOrder") as _us,\
				patch("physbiblio.config.GlobalDB.insertSearch") as _is,\
				patch(self.clsName + ".createMenusAndToolBar") as _cm,\
				patch("physbiblio.database.Entries.fetchFromDict") as _fd,\
				patch(self.modName + ".askGenericText",
					side_effect=[["abc", False], ["", True], ["def", True]]
					) as _agt:
			self.assertEqual(self.mainW.searchBiblio(replace=True),
				{'double': False,
				'fieNew': 'author',
				'fieNew1': 'author',
				'fieOld': 'author',
				'new': '',
				'new1': '',
				'old': '',
				'regex': False})
			_rsb.assert_not_called()
			_agt.assert_not_called()
			_cm.assert_not_called()
			_us.assert_called_once_with(replacement=True)
			_is.assert_called_once_with(
				count=0, manual=False, limit=100000, offset=0,
				replacement=True,
				replaceFields={'regex': False, 'double': False,
					'fieOld': 'author', 'old': '', 'fieNew': 'author',
					'new': '', 'fieNew1': 'author', 'new1': ''},
				searchFields=[{'type': 'Text', 'logical': None,
					'field': 'bibtex', 'operator': 'contains', 'content': ''}])
			_fd.assert_called_once_with(
				[{'type': 'Text', 'logical': None, 'field': 'bibtex',
				'operator': 'contains', 'content': ''}],
				doFetch=False, limitOffset=0)
			sbw.replOld.setText("asfa")
			sbw.replNew.setText("afsa")
			sbw.onSave()
			_us.reset_mock()
			_is.reset_mock()
			_fd.reset_mock()
			self.assertEqual(self.mainW.searchBiblio(replace=True),
				{'double': False,
				'fieNew': 'author',
				'fieNew1': 'author',
				'fieOld': 'author',
				'new': 'afsa',
				'new1': '',
				'old': 'asfa',
				'regex': False})
			_agt.assert_called_once_with(
				'Insert a name / short description to be able to recognise'
				+ ' this replace in the future:',
				'Replace name', parent=self.mainW)
			_rsb.assert_not_called()
			_cm.assert_not_called()
			_us.assert_not_called()
			_is.assert_not_called()
			_fd.assert_called_once_with(
				[{'type': 'Text', 'logical': None, 'field': 'bibtex',
				'operator': 'contains', 'content': ''}],
				doFetch=False, limitOffset=0)
			_fd.reset_mock()
			self.assertEqual(self.mainW.searchBiblio(replace=True),
				{'double': False,
				'fieNew': 'author',
				'fieNew1': 'author',
				'fieOld': 'author',
				'new': 'afsa',
				'new1': '',
				'old': 'asfa',
				'regex': False})
			_us.assert_not_called()
			_is.assert_called_once_with(
				count=0, manual=True, name='def', limit=100000, offset=0,
				replacement=True,
				replaceFields={'regex': False, 'double': False,
					'fieOld': 'author', 'old': 'asfa', 'fieNew': 'author',
					'new': 'afsa', 'fieNew1': 'author', 'new1': ''},
				searchFields=[{'type': 'Text', 'logical': None,
					'field': 'bibtex', 'operator': 'contains', 'content': ''}])
			_fd.assert_called_once_with(
				[{'type': 'Text', 'logical': None, 'field': 'bibtex',
				'operator': 'contains', 'content': ''}],
				doFetch=False, limitOffset=0)

	def test_runSearchBiblio(self):
		"""test runSearchBiblio"""
		pBDB.lastFetched = []
		with patch("PySide2.QtWidgets.QApplication."
				+ "setOverrideCursor") as _soc,\
				patch("PySide2.QtWidgets.QApplication."
					+ "restoreOverrideCursor") as _roc,\
				patch("physbiblio.database.Entries.fetchFromDict",
					return_value=pBDB) as _ffd,\
				patch(self.clsName + ".reloadMainContent") as _rmc:
			self.mainW.runSearchBiblio({"s": "a"}, 12, 34)
			_soc.assert_called_once_with(Qt.WaitCursor)
			_roc.assert_called_once_with()
			_ffd.assert_has_calls([
				call({"s": "a"}, limitOffset=34),
				call({"s": "a"}, limitOffset=34, limitTo=12)])
			_rmc.assert_called_once_with([])

		pBDB.lastFetched = ["a"]
		self.lastFetched = ["a", "b"]
		with patch("PySide2.QtWidgets.QApplication."
				+ "setOverrideCursor") as _soc,\
				patch("PySide2.QtWidgets.QApplication."
					+ "restoreOverrideCursor") as _roc,\
				patch("physbiblio.database.Entries.fetchFromDict",
					side_effect=[self, pBDB]) as _ffd,\
				patch(self.clsName + ".reloadMainContent") as _rmc,\
				patch(self.modName + ".infoMessage") as _im:
			self.mainW.runSearchBiblio({"s": "a"}, 12, 34)
			_soc.assert_called_once_with(Qt.WaitCursor)
			_roc.assert_called_once_with()
			_ffd.assert_has_calls([
				call({"s": "a"}, limitOffset=34),
				call({"s": "a"}, limitOffset=34, limitTo=12)])
			_rmc.assert_called_once_with(["a"])
			_im.assert_called_once_with(
				"Warning: more entries match the current search, "
				+ "showing only the first 1 of 2.\nChange "
				+ "'Max number of results' in the search form to see more.")

	def test_runSearchReplaceBiblio(self):
		"""test runSearchReplaceBiblio"""
		pBDB.lastFetched = ["a"]
		with patch("physbiblio.database.Entries.fetchFromDict",
					return_value=pBDB) as _ffd,\
				patch(self.clsName + ".runReplace") as _rr:
			self.mainW.runSearchReplaceBiblio({"s": "a"}, ["b"], 12)
			_ffd.assert_called_once_with({'s': 'a'}, limitOffset=12)
			_rr.assert_called_once_with(["b"])

	def test_editSearchBiblio(self):
		"""test editSearchBiblio"""
		raise NotImplementedError
		pBDB.lastFetched = ["a"]
		with patch("physbiblio.config.GlobalDB.deleteSearch") as _ds,\
				patch(self.clsName + ".createMenusAndToolBar") as _cm,\
				patch(self.modName + ".askYesNo") as _ay:
			self.mainW.delSearchBiblio(999, "search")
			_ay.assert_called_once_with("Are you sure you want to delete "
				+ "the saved search 'search'?")
			_cm.assert_called_once_with()
			_ds.assert_called_once_with(999)

	def test_delSearchBiblio(self):
		"""test delSearchBiblio"""
		pBDB.lastFetched = ["a"]
		with patch("physbiblio.config.GlobalDB.deleteSearch") as _ds,\
				patch(self.clsName + ".createMenusAndToolBar") as _cm,\
				patch(self.modName + ".askYesNo") as _ay:
			self.mainW.delSearchBiblio(999, "search")
			_ay.assert_called_once_with("Are you sure you want to delete "
				+ "the saved search 'search'?")
			_cm.assert_called_once_with()
			_ds.assert_called_once_with(999)

	def test_searchAndReplace(self):
		"""test searchAndReplace"""
		with patch(self.clsName + ".searchBiblio",
				side_effect=[False, "a"]) as _sb,\
				patch(self.clsName + ".runReplace") as _rr:
			self.mainW.searchAndReplace()
			_sb.assert_called_once_with(replace=True)
			_rr.assert_not_called()
			self.mainW.searchAndReplace()
			_rr.assert_called_once_with("a")

	def test_runReplace(self):
		"""test runReplace"""
		pBDB.lastFetched = ["z"]
		self.mainW.replaceResults = (["d"], ["e", "f"], ["g", "h", "i"])
		with patch("PySide2.QtWidgets.QApplication."
				+ "setOverrideCursor") as _soc,\
				patch("PySide2.QtWidgets.QApplication."
					+ "restoreOverrideCursor") as _roc,\
				patch("physbiblio.database.Entries.fetchFromLast",
					return_value=pBDB) as _ffl,\
				patch(self.clsName + "._runInThread") as _rit,\
				patch(self.clsName + ".reloadMainContent") as _rmc,\
				patch(self.modName + ".infoMessage") as _im,\
				patch(self.modName + ".LongInfoMessage") as _lim,\
				patch(self.modName + ".askYesNo",
					side_effect=[False, True]) as _ay:
			self.mainW.runReplace(
				{"fieOld": "bibtex", "fieNew": "bibkey", "old": "",
				"new": "a", "regex": "r", "double": False,
				"fieNew1": "", "new1": ""})
			_soc.assert_not_called()
			_rit.assert_not_called()
			_im.assert_called_once_with("The string to substitute is empty!")
			_im.reset_mock()

			self.mainW.runReplace(
				{"fieOld": "bibtex", "fieNew": "bibkey", "old": "o",
				"new": "a", "regex": "r", "double": True,
				"fieNew1": "", "new1": ""})
			_soc.assert_not_called()
			_rit.assert_not_called()
			_ay.assert_called_once_with("Empty new string. "
				+ "Are you sure you want to continue?")
			_ay.reset_mock()

			self.mainW.runReplace(
				{"fieOld": "bibtex", "fieNew": "bibkey", "old": "o",
				"new": "a", "regex": "r", "double": True,
				"fieNew1": "volume", "new1": ""})
			_soc.assert_called_once_with(Qt.WaitCursor)
			_roc.assert_called_once_with()
			_ay.assert_called_once_with("Empty new string. "
				+ "Are you sure you want to continue?")
			_rmc.assert_called_once_with(["z"])
			_im.assert_not_called()
			_ay.assert_called_once_with("Empty new string. "
				+ "Are you sure you want to continue?")
			_rit.assert_called_once_with(
				Thread_replace, 'Replace',
				'bibtex', ['bibkey', 'volume'], 'o', ['a', ''],
				minProgress=0.0, progrStr='%): entry ',
				regex='r', stopFlag=True, totStr='Replace will process ')
			_ffl.assert_called_once_with()
			_lim.assert_called_once_with(
				"Replace completed.<br><br>"
				+ "1 elements successfully processed"
				+ " (of which 2 changed), "
				+ "3 failures (see below).<br><br>"
				+ "<b>Changed</b>: ['e', 'f']<br><br>"
				+ "<b>Failed</b>: ['g', 'h', 'i']")

	def test_convertSearchFormat(self):
		"""test convertSearchFormat"""
		raise NotImplementedError

	def test_updateAllBibtexsAsk(self):
		"""test updateAllBibtexsAsk"""
		with patch(self.modName + ".askYesNo", return_value=False) as _ay,\
				patch(self.modName + ".askGenericText",
					return_value=["a", False]) as _agt,\
				patch(self.clsName + ".updateAllBibtexs") as _uab:
			self.assertEqual(self.mainW.updateAllBibtexsAsk(), None)
			_uab.assert_not_called()

		with patch(self.modName + ".askYesNo", return_value=False) as _ay,\
				patch(self.modName + ".askGenericText",
					return_value=["a", True]) as _agt,\
				patch(self.clsName + ".updateAllBibtexs") as _uab:
			self.assertEqual(self.mainW.updateAllBibtexsAsk(), None)
			_uab.assert_not_called()

		with patch(self.modName + ".askYesNo", return_value=True) as _ay,\
				patch(self.modName + ".askGenericText",
					return_value=["a", True]) as _agt,\
				patch(self.clsName + ".updateAllBibtexs") as _uab:
			self.assertEqual(self.mainW.updateAllBibtexsAsk(), None)
			_ay.assert_any_call("The text you inserted is not an integer. "
				+ "I will start from 0.\nDo you want to continue?",
				"Invalid entry")
			_uab.assert_called_once_with(0, force=True)

		with patch(self.modName + ".askYesNo", return_value=False) as _ay,\
				patch(self.modName + ".askGenericText",
					return_value=["12", True]) as _agt,\
				patch(self.clsName + ".updateAllBibtexs") as _uab:
			self.assertEqual(self.mainW.updateAllBibtexsAsk(), None)
			_ay.assert_called_once_with(
				"Do you want to force the update of already existing "
				+ "items?\n(Only regular articles not explicitely "
				+ "excluded will be considered)", 'Force update:')
			_agt.assert_called_once_with(
				"Insert the ordinal number of the bibtex element from "
				+ "which you want to start the updates:",
				'Where do you want to start searchOAIUpdates from?',
				self.mainW)
			_uab.assert_called_once_with(12, force=False)

	def test_updateAllBibtexs(self):
		"""test updateAllBibtexs"""
		with patch(self.clsName + ".statusBarMessage") as _sbm,\
				patch(self.clsName + "._runInThread") as _rit,\
				patch(self.clsName + ".refreshMainContent") as _rmc:
			self.mainW.updateAllBibtexs()
			_sbm.assert_called_once_with(
				"Starting update of bibtexs from %s..."%(
					pbConfig.params["defaultUpdateFrom"]))
			_rit.assert_called_once_with(Thread_updateAllBibtexs,
				'Update Bibtexs', pbConfig.params["defaultUpdateFrom"],
				force=False, minProgress=0.0,
				progrStr='%) - looking for update: ', reloadAll=False,
				stopFlag=True, totStr='SearchOAIUpdates will process ',
				useEntries=None)
			_rmc.assert_called_once_with()
		with patch(self.clsName + ".statusBarMessage") as _sbm,\
				patch(self.clsName + "._runInThread") as _rit,\
				patch(self.clsName + ".refreshMainContent") as _rmc:
			self.mainW.updateAllBibtexs(startFrom=12,
				useEntries="abc",
				force=True,
				reloadAll=True)
			_sbm.assert_called_once_with(
				"Starting update of bibtexs from 12...")
			_rit.assert_called_once_with(Thread_updateAllBibtexs,
				'Update Bibtexs', 12, force=True, minProgress=0.0,
				progrStr='%) - looking for update: ', reloadAll=True,
				stopFlag=True, totStr='SearchOAIUpdates will process ',
				useEntries="abc")
			_rmc.assert_called_once_with()

	def test_updateInspireInfo(self):
		"""test updateInspireInfo"""
		with patch(self.clsName + ".statusBarMessage") as _sbm,\
				patch(self.clsName + "._runInThread") as _rit,\
				patch(self.clsName + ".refreshMainContent") as _rmc:
			self.mainW.updateInspireInfo("key")
			_sbm.assert_called_once_with(
				"Starting generic info update from INSPIRE-HEP...")
			_rit.assert_called_once_with(Thread_updateInspireInfo,
				"Update Info", "key", None, minProgress=0., stopFlag=False)
			_rmc.assert_called_once_with()
		with patch(self.clsName + ".statusBarMessage") as _sbm,\
				patch(self.clsName + "._runInThread") as _rit,\
				patch(self.clsName + ".refreshMainContent") as _rmc:
			self.mainW.updateInspireInfo("key", inspireID="1234")
			_sbm.assert_called_once_with(
				"Starting generic info update from INSPIRE-HEP...")
			_rit.assert_called_once_with(Thread_updateInspireInfo,
				"Update Info", "key", "1234", minProgress=0., stopFlag=False)
			_rmc.assert_called_once_with()

	def test_authorStats(self):
		"""test authorStats"""
		with patch(self.modName + ".askGenericText",
				return_value=("", False)) as _at:
			self.assertFalse(self.mainW.authorStats())
			_at.assert_called_once_with(
				"Insert the INSPIRE name of the author of which you want "
				+ "the publication and citation statistics:",
				"Author name?", self.mainW)
		with patch(self.modName + ".askGenericText",
				return_value=("", True)) as _at,\
				patch("logging.Logger.warning") as _w:
			self.assertFalse(self.mainW.authorStats())
			_w.assert_called_once_with(
				"Empty name inserted! cannot proceed.")
		with patch(self.modName + ".askGenericText",
				return_value=("[author]", True)) as _at,\
				patch(self.clsName + ".statusBarMessage") as _sbm,\
				patch("logging.Logger.exception") as _exc:
			self.assertFalse(self.mainW.authorStats())
			_exc.assert_called_once_with(
				"Cannot recognize the list sintax. "
				+ "Missing quotes in the string?")

		self.mainW.lastAuthorStats = None
		with patch(self.modName + ".askGenericText",
				return_value=("['a1','a2']", True)) as _at,\
				patch(self.modName + ".infoMessage") as _im,\
				patch(self.clsName + ".statusBarMessage") as _sbm,\
				patch(self.clsName + "._runInThread") as _rit,\
				patch("logging.Logger.exception") as _exc,\
				patch("logging.Logger.warning") as _w:
			self.assertFalse(self.mainW.authorStats())
			_sbm.assert_called_once_with(
				'Starting computing author stats from INSPIRE...')
			_rit.assert_called_once_with(
				Thread_authorStats, "Author Stats",
				['a1','a2'],
				totStr="AuthorStats will process ",
				progrStr="%) - looking for paper: ",
				minProgress=0., stopFlag=True)
			_im.assert_called_once_with("No results obtained. "
				+ "Maybe there was an error or you interrupted execution.")

		self.mainW.lastAuthorStats = {"paLi": [[]]}
		with patch(self.modName + ".askGenericText",
				return_value=("author", True)) as _at,\
				patch(self.modName + ".infoMessage") as _im,\
				patch(self.clsName + ".statusBarMessage") as _sbm,\
				patch(self.clsName + "._runInThread") as _rit,\
				patch("logging.Logger.exception") as _exc,\
				patch("logging.Logger.warning") as _w:
			self.assertFalse(self.mainW.authorStats())
			_sbm.assert_called_once_with(
				'Starting computing author stats from INSPIRE...')
			_rit.assert_called_once_with(
				Thread_authorStats, "Author Stats",
				"author",
				totStr="AuthorStats will process ",
				progrStr="%) - looking for paper: ",
				minProgress=0., stopFlag=True)
			_im.assert_called_once_with("No results obtained. "
				+ "Maybe there was an error or you interrupted execution.")

		self.mainW.lastAuthorStats = {"paLi": [["a"]]}
		aSP = MagicMock()
		aSP.show = MagicMock()
		with patch(self.modName + ".askGenericText",
				return_value=("author", True)) as _at,\
				patch(self.modName + ".infoMessage") as _im,\
				patch(self.clsName + ".statusBarMessage") as _sbm,\
				patch(self.clsName + "._runInThread") as _rit,\
				patch(self.clsName + ".done") as _d,\
				patch(self.modName + ".AuthorStatsPlots",
					return_value=aSP) as _asp,\
				patch("physbiblio.inspireStats.InspireStatsLoader.plotStats",
					return_value="figs") as _ps,\
				patch("logging.Logger.exception") as _exc,\
				patch("logging.Logger.warning") as _w:
			self.assertTrue(self.mainW.authorStats())
			_ps.assert_called_once_with(author=True)
			_asp.assert_called_once_with(
				"figs",
				title="Statistics for 'author'",
				parent=self.mainW)
			aSP.show.assert_called_once_with()
			_d.assert_called_once_with()

	def test_getInspireStats(self):
		"""test getInspireStats"""
		self.mainW.lastPaperStats = None
		with patch(self.clsName + "._runInThread") as _rit,\
				patch(self.modName + ".infoMessage") as _im,\
				patch("physbiblio.inspireStats.InspireStatsLoader.plotStats"
					) as _ps:
			self.assertFalse(self.mainW.getInspireStats("1234"))
			_rit.assert_called_once_with(Thread_paperStats,
				'Paper Stats', '1234',
				minProgress=0.0, progrStr='%) - looking for paper: ',
				stopFlag=False, totStr='PaperStats will process ')
			_im.assert_called_once_with(
				"No results obtained. Maybe there was an error.")
			_ps.assert_not_called()
		self.mainW.lastPaperStats = {"id": "1234"}
		psp = MagicMock()
		psp.show = MagicMock()
		with patch(self.clsName + "._runInThread") as _rit,\
				patch(self.clsName + ".done") as _d,\
				patch(self.modName + ".PaperStatsPlots",
					return_value=psp) as _psp,\
				patch(self.modName + ".infoMessage") as _im,\
				patch("physbiblio.inspireStats.InspireStatsLoader.plotStats",
					return_value="something") as _ps:
			self.assertEqual(self.mainW.getInspireStats("1234"), None)
			_im.assert_not_called()
			_rit.assert_called_once_with(Thread_paperStats,
				'Paper Stats', '1234',
				minProgress=0.0, progrStr='%) - looking for paper: ',
				stopFlag=False, totStr='PaperStats will process ')
			_ps.assert_called_once_with(paper=True)
			_psp.assert_called_once_with('something', parent=self.mainW,
				title='Statistics for recid:1234')
			psp.show.assert_called_once_with()
			_d.assert_called_once_with()
			self.assertEqual(self.mainW.lastPaperStats["fig"], "something")

	def test_inspireLoadAndInsert(self):
		"""test inspireLoadAndInsert"""
		with patch(self.modName + ".askGenericText",
				return_value=("", False)) as _gt:
			self.assertFalse(self.mainW.inspireLoadAndInsert())
			_gt.assert_called_once_with(
				"Insert the query string you want to use for importing "
				+ "from INSPIRE-HEP:\n(It will be interpreted as a list, "
				+ "if possible)", "Query string?", self.mainW)
		with patch(self.modName + ".askGenericText",
				return_value=("", True)) as _gt,\
				patch("logging.Logger.warning") as _w:
			self.assertFalse(self.mainW.inspireLoadAndInsert())
			_gt.assert_called_once_with(
				"Insert the query string you want to use for importing "
				+ "from INSPIRE-HEP:\n(It will be interpreted as a list, "
				+ "if possible)", "Query string?", self.mainW)
			_w.assert_called_once_with("Empty string! cannot proceed.")
		with patch(self.modName + ".askGenericText",
				return_value=("ab,c", True)) as _gt,\
				patch(self.clsName + ".statusBarMessage") as _sbm,\
				patch("logging.Logger.exception") as _ex,\
				patch(self.clsName + "._runInThread") as _rit:
			self.assertFalse(self.mainW.inspireLoadAndInsert())
			_sbm.assert_called_once_with("Starting import from INSPIRE...")
			_ex.assert_called_once_with(
				"Cannot recognize the list sintax. "
				+ "Missing quotes in the string?")
			_rit.assert_not_called()

		self.mainW.loadedAndInserted = []
		with patch(self.modName + ".askGenericText",
				return_value=("'ab','cd'", True)) as _gt,\
				patch(self.clsName + ".statusBarMessage") as _sbm,\
				patch(self.modName + ".infoMessage") as _im,\
				patch(self.clsName + "._runInThread") as _rit:
			self.assertFalse(self.mainW.inspireLoadAndInsert())
			_im.assert_called_once_with(
				'No results obtained. Maybe there was an error'
				+ ' or you interrupted execution.')
			_rit.assert_called_once_with(
				Thread_loadAndInsert, "Import from INSPIRE-HEP",
				['ab', 'cd'],
				totStr="LoadAndInsert will process ",
				progrStr="%) - looking for string: ",
				minProgress=0., stopFlag=True,
				addMessage="Searching:\n['ab', 'cd']")

		self.mainW.loadedAndInserted = []
		with patch(self.modName + ".askGenericText",
				return_value=("abcd", True)) as _gt,\
				patch(self.clsName + ".statusBarMessage") as _sbm,\
				patch(self.modName + ".infoMessage") as _im,\
				patch(self.clsName + "._runInThread") as _rit:
			self.assertFalse(self.mainW.inspireLoadAndInsert())
			_im.assert_called_once_with(
				'No results obtained. Maybe there was an error'
				+ ' or you interrupted execution.')
			_rit.assert_called_once_with(
				Thread_loadAndInsert, "Import from INSPIRE-HEP",
				'abcd',
				totStr="LoadAndInsert will process ",
				progrStr="%) - looking for string: ",
				minProgress=0., stopFlag=True,
				addMessage="Searching:\nabcd")

		mainW = MainWindow(testing=True)
		def fake_loadAndInsert(*args, **kwargs):
			mainW.loadedAndInserted = ["a"]

		mainW._runInThread = fake_loadAndInsert
		with patch(self.modName + ".askGenericText",
				return_value=("'ab','cd'", True)) as _gt,\
				patch(self.clsName + ".statusBarMessage") as _sbm,\
				patch(self.clsName + ".reloadMainContent") as _rmc,\
				patch(self.modName + ".infoMessage") as _im:
			self.assertTrue(mainW.inspireLoadAndInsert())
			_im.assert_not_called()
			_rmc.assert_called_once_with()

		with patch(self.modName + ".askGenericText",
				return_value=("'ab','cd'", True)) as _gt,\
				patch(self.clsName + ".statusBarMessage") as _sbm,\
				patch(self.clsName + ".reloadMainContent") as _rmc:
			self.assertTrue(mainW.inspireLoadAndInsert(doReload=False))
			_rmc.assert_not_called()

	def test_askCatsForEntries(self):
		"""test askCatsForEntries"""
		sc1 = CatsTreeWindow(parent=self.mainW)
		sc1.exec_ = MagicMock()
		sc1.result = "Ok"
		sc2 = CatsTreeWindow(parent=self.mainW)
		sc2.exec_ = MagicMock()
		sc2.result = False
		sc3 = CatsTreeWindow(parent=self.mainW)
		sc3.exec_ = MagicMock()
		sc3.result = "Exps"
		se1 = ExpsListWindow(parent=self.mainW)
		se1.exec_ = MagicMock()
		se1.result = "Ok"
		se2 = ExpsListWindow(parent=self.mainW)
		se2.exec_ = MagicMock()
		se2.result = False
		self.mainW.selectedCats = [0, 1, 2]
		self.mainW.selectedExps = [0, 1]
		with patch("physbiblio.database.Categories.getByEntry",
				return_value=[[0]]) as _gbe,\
				patch(self.modName + ".CatsTreeWindow",
					side_effect=[sc1, sc2, sc3, sc3]) as _ctw,\
				patch("physbiblio.database.CatsEntries.insert") as _cbi,\
				patch(self.clsName + ".statusBarMessage") as _sbm,\
				patch(self.modName + ".ExpsListWindow",
					side_effect=[se1, se2]) as _elw,\
				patch("physbiblio.database.EntryExps.insert") as _bei:
			self.mainW.askCatsForEntries(["a", "b", "c", "d"])
			_gbe.assert_has_calls([call("a"), call("b"), call("c"), call("d")])
			_ctw.assert_has_calls([
				call(askCats=True, askForBib='a', parent=self.mainW,
					previous=[0]),
				call(askCats=True, askForBib='b', parent=self.mainW,
					previous=[0]),
				call(askCats=True, askForBib='c', parent=self.mainW,
					previous=[0]),
				call(askCats=True, askForBib='d', parent=self.mainW,
					previous=[0])])
			sc1.exec_.assert_called_once_with()
			sc2.exec_.assert_called_once_with()
			self.assertEqual(sc3.exec_.call_count, 2)
			_cbi.assert_has_calls([
				call([0, 1, 2], 'a'),
				call([0, 1, 2], 'c'),
				call([0, 1, 2], 'd')])
			_elw.assert_has_calls([
				call(askExps=True, askForBib='c', parent=self.mainW),
				call(askExps=True, askForBib='d', parent=self.mainW)])
			se1.exec_.assert_called_once_with()
			se2.exec_.assert_called_once_with()
			_bei.assert_called_once_with('c', [0, 1])
			_sbm.assert_has_calls([
				call("categories for 'a' successfully inserted"),
				call("categories for 'c' successfully inserted"),
				call("experiments for 'c' successfully inserted"),
				call("categories for 'd' successfully inserted")])

	def test_inspireLoadAndInsertWithCats(self):
		"""test inspireLoadAndInsertWithCats"""
		self.mainW.loadedAndInserted = []
		with patch(self.clsName + ".inspireLoadAndInsert",
				return_value=False) as _ili,\
				patch(self.clsName + ".askCatsForEntries") as _ace,\
				patch(self.clsName + ".reloadMainContent") as _rmc,\
				patch("physbiblio.database.CatsEntries.delete") as _d:
			self.mainW.inspireLoadAndInsertWithCats()
			_ili.assert_called_once_with(doReload=False)
			_d.assert_not_called()
			_ace.assert_not_called()
			_rmc.assert_not_called()
		with patch(self.clsName + ".inspireLoadAndInsert",
				return_value=True) as _ili,\
				patch(self.clsName + ".askCatsForEntries") as _ace,\
				patch(self.clsName + ".reloadMainContent") as _rmc,\
				patch("physbiblio.database.CatsEntries.delete") as _d:
			self.mainW.inspireLoadAndInsertWithCats()
			_ili.assert_called_once_with(doReload=False)
			_d.assert_not_called()
			_ace.assert_not_called()
			_rmc.assert_not_called()

		self.mainW.loadedAndInserted = ["a", "b"]
		with patch(self.clsName + ".inspireLoadAndInsert",
				return_value=True) as _ili,\
				patch(self.clsName + ".askCatsForEntries") as _ace,\
				patch(self.clsName + ".reloadMainContent") as _rmc,\
				patch("physbiblio.database.CatsEntries.delete") as _d:
			self.mainW.inspireLoadAndInsertWithCats()
			_ili.assert_called_once_with(doReload=False)
			_d.assert_has_calls([
				call(pbConfig.params["defaultCategories"], "a"),
				call(pbConfig.params["defaultCategories"], "b")])
			_ace.assert_called_once_with(["a", "b"])
			_rmc.assert_called_once_with()

	def test_advancedImport(self):
		"""test advancedImport"""
		aid = AdvancedImportDialog()
		aid.exec_ = MagicMock()
		aid.result = False
		aid.comboMethod.setCurrentText("INSPIRE-HEP")
		aid.searchStr.setText("")
		with patch(self.modName + ".AdvancedImportDialog",
				return_value=aid) as _aid:
			self.assertFalse(self.mainW.advancedImport())
			_aid.assert_called_once_with()
			aid.exec_.assert_called_once_with()

		aid.exec_ = MagicMock()
		aid.result = True
		with patch(self.modName + ".AdvancedImportDialog",
				return_value=aid) as _aid:
			self.assertFalse(self.mainW.advancedImport())
			_aid.assert_called_once_with()
			aid.exec_.assert_called_once_with()

		aid.searchStr.setText("test")
		aid.exec_ = MagicMock()
		aid.result = True
		with patch(self.modName + ".AdvancedImportDialog",
				return_value=aid) as _aid,\
				patch(self.modName + ".infoMessage") as _im,\
				patch("physbiblio.webimport.inspire.WebSearch.retrieveUrlAll",
					return_value="") as _ru:
			self.assertFalse(self.mainW.advancedImport())
			_aid.assert_called_once_with()
			aid.exec_.assert_called_once_with()
			_im.assert_called_once_with("No results obtained.")
			_ru.assert_called_once_with("test")

		aid.comboMethod.setCurrentText("DOI")
		with patch("logging.Logger.warning") as _w:
			ais = AdvancedImportSelect(
				{u'a': {'exist': True, 'bibpars':
					{'ID': u'a', u'title': u'T',
					'ENTRYTYPE': u'article', u'author': u'gs'}},
				u'b': {'exist': True, 'bibpars':
					{u'doi': u'2', u'author': u'sg', u'title': u'tit',
					u'arxiv': u'1', 'ID': u'b', 'ENTRYTYPE': u'article'}},
				u'c': {'exist': False, 'bibpars':
					{u'doi': u'4', u'title': u'title', u'author': u'io',
					'ENTRYTYPE': u'article', 'arxiv': u'3',
					u'eprint': u'3', 'ID': u'c'}},
				u'd': {'exist': False, 'bibpars':
					{'ID': u'd', u'title': u't', 'ENTRYTYPE': u'article',
					u'author': u'yo'}}}, self.mainW)
		ais.exec_ = MagicMock()
		ais.askCats.setCheckState(Qt.Checked)
		ais.selected = {"a": True, "b": True, "c": False}
		ais.result = False
		aid.exec_.reset_mock()
		with patch(self.modName + ".AdvancedImportDialog",
				return_value=aid) as _aid,\
				patch(self.modName + ".AdvancedImportSelect",
					return_value=ais) as _ais,\
				patch("PySide2.QtWidgets.QApplication.setOverrideCursor"
					) as _sc,\
				patch("PySide2.QtWidgets.QApplication.restoreOverrideCursor"
					) as _rc,\
				patch(self.modName + ".infoMessage") as _im,\
				patch(self.clsName + ".reloadMainContent") as _rmc,\
				patch("physbiblio.webimport.doi.WebSearch.retrieveUrlAll",
					return_value='@article{ ,\nauthor="me",\ntitle="titl"\n}\n'
						+ '@article{a,\nauthor="gs",\ntitle="T"\n}\n'
						+ '@article{b,\nauthor="sg",\ntitle="tit"\n,'
						+ 'arxiv="1",\ndoi="2"\n}\n'
						+ '@article{c,\nauthor="io",\ntitle="title"\n,'
						+ 'eprint="3",\ndoi="4"\n}\n'
						+ '@article{d,\nauthor="yo",\ntitle="t"\n}\n'
						) as _ru,\
				patch(self.clsName + ".askCatsForEntries") as _ace,\
				patch("logging.Logger.warning") as _wa,\
				patch("logging.Logger.debug") as _deb,\
				patch("physbiblio.database.Entries.getByBibkey",
					side_effect=[["a"], [], [], []]) as _gbb,\
				patch("physbiblio.database.Entries.getAll",
					side_effect=[["b"], [], []]) as _ga,\
				patch("physbiblio.database.CatsEntries.delete") as _cd:
			self.assertFalse(self.mainW.advancedImport())
			_aid.assert_called_once_with()
			aid.exec_.assert_called_once_with()
			_im.assert_not_called()
			_ru.assert_called_once_with("test")
			self.assertEqual(_sc.call_count, 1)
			self.assertEqual(_rc.call_count, 1)
			_rmc.assert_called_once_with()
			_gbb.assert_has_calls([call(u'a', saveQuery=False),
				 call(u'b', saveQuery=False),
				 call(u'c', saveQuery=False)])
			_ga.assert_has_calls([
				call(params={'arxiv': u'1'}, saveQuery=False),
				call(params={'arxiv': u'3'}, saveQuery=False),
				call(params={'doi': u'4'}, saveQuery=False)])
			_deb.assert_has_calls([
				call(u"KeyError 'arxiv', entry: d"),
				call(u"KeyError 'doi', entry: d")])
			_wa.assert_called_once_with(
				"Impossible to insert an entry with empty bibkey!"
				+ '\n@Article{,\n        author = "me",\n         '
				+ 'title = "{titl}",\n}\n\n\n')

		aid.exec_.reset_mock()
		ais.exec_.reset_mock()
		ais.result = True
		with patch(self.modName + ".AdvancedImportDialog",
				return_value=aid) as _aid,\
				patch(self.modName + ".AdvancedImportSelect",
					return_value=ais) as _ais,\
				patch("PySide2.QtWidgets.QApplication.setOverrideCursor"
					) as _sc,\
				patch("PySide2.QtWidgets.QApplication.restoreOverrideCursor"
					) as _rc,\
				patch(self.modName + ".infoMessage") as _im,\
				patch(self.clsName + ".reloadMainContent") as _rmc,\
				patch(self.clsName + ".statusBarMessage") as _sbm,\
				patch("physbiblio.webimport.doi.WebSearch.retrieveUrlAll",
					return_value='@article{ ,\nauthor="me",\ntitle="titl"\n}\n'
						+ '@article{a,\nauthor="gs",\ntitle="T"\n}\n'
						+ '@article{b,\nauthor="sg",\ntitle="tit"\n,'
						+ 'arxiv="1",\ndoi="2"\n}\n'
						+ '@article{c,\nauthor="io",\ntitle="title"\n,'
						+ 'eprint="3",\ndoi="4"\n}\n'
						+ '@article{d,\nauthor="yo",\ntitle="t"\n}\n'
						) as _ru,\
				patch(self.clsName + ".askCatsForEntries") as _ace,\
				patch("logging.Logger.warning") as _wa,\
				patch("logging.Logger.info") as _in,\
				patch("logging.Logger.debug") as _deb,\
				patch("physbiblio.database.Entries.getByBibkey",
					side_effect=[["a"], [], [], []]) as _gbb,\
				patch("physbiblio.database.Entries.getAll",
					side_effect=[["b"], [], []]) as _ga,\
				patch("physbiblio.database.Entries.prepareInsert",
					side_effect=["data1", "data2", "data3", "data4"]) as _pi,\
				patch("physbiblio.database.Entries.insert",
					side_effect=[True, False, True, True]) as _bi,\
				patch("physbiblio.database.CatsEntries.delete") as _cd:
			self.assertFalse(self.mainW.advancedImport())
			_aid.assert_called_once_with()
			aid.exec_.assert_called_once_with()
			_im.assert_not_called()
			_ru.assert_called_once_with("test")
			self.assertEqual(_sc.call_count, 1)
			self.assertEqual(_rc.call_count, 1)
			_rmc.assert_called_once_with()
			_gbb.assert_has_calls([call(u'a', saveQuery=False),
				 call(u'b', saveQuery=False),
				 call(u'c', saveQuery=False)])
			_ga.assert_has_calls([
				call(params={'arxiv': u'1'}, saveQuery=False),
				call(params={'arxiv': u'3'}, saveQuery=False),
				call(params={'doi': u'4'}, saveQuery=False)])
			_deb.assert_has_calls([
				call(u"KeyError 'arxiv', entry: d"),
				call(u"KeyError 'doi', entry: d")])
			_pi.assert_has_calls([
				call(u'@Article{a,\n        author = "gs",'
					+ '\n         title = "{T}",\n}\n\n'),
				call(u'@Article{b,\n        author = "sg",'
					+ '\n         title = "{tit}",\n           '
					+ 'doi = "2",\n         arxiv = "1",\n}\n\n')])
			_bi.assert_has_calls([call("data1"), call("data2")])
			_wa.assert_has_calls([call("Failed in inserting entry 'b'\n")])
			_sbm.assert_called_once_with(
				"Entries successfully imported: ['a']")
			_ace.assert_called_once_with(["a"])
			_in.assert_called_once_with("Element 'a' successfully inserted.\n")
			_cd.assert_called_once_with(
				pbConfig.params["defaultCategories"], "a")

		aid.comboMethod.setCurrentText("ISBN")
		aid.exec_.reset_mock()
		with patch("logging.Logger.warning") as _w:
			ais = AdvancedImportSelect(
				{u'a': {'exist': True, 'bibpars':
					{'ID': u'a', u'title': u'T',
					'ENTRYTYPE': u'article', u'author': u'gs'}},
				u'b': {'exist': True, 'bibpars':
					{u'doi': u'2', u'author': u'sg', u'title': u'tit',
					u'arxiv': u'1', 'ID': u'b', 'ENTRYTYPE': u'article'}}
				}, self.mainW)
		ais.exec_ = MagicMock()
		ais.askCats.setCheckState(Qt.Unchecked)
		ais.selected = {"a": True, "b": True}
		ais.result = True
		with patch(self.modName + ".AdvancedImportDialog",
				return_value=aid) as _aid,\
				patch(self.modName + ".AdvancedImportSelect",
					return_value=ais) as _ais,\
				patch("PySide2.QtWidgets.QApplication.setOverrideCursor"
					) as _sc,\
				patch("PySide2.QtWidgets.QApplication.restoreOverrideCursor"
					) as _rc,\
				patch(self.modName + ".infoMessage") as _im,\
				patch(self.clsName + ".reloadMainContent") as _rmc,\
				patch(self.clsName + ".statusBarMessage") as _sbm,\
				patch("physbiblio.webimport.isbn.WebSearch.retrieveUrlAll",
					return_value='@article{a,\nauthor="gs",\ntitle="T"\n}\n'
						+ '@article{b,\nauthor="sg",\ntitle="tit"\n,'
						+ 'arxiv="1",\ndoi="2"\n}\n'
						) as _ru,\
				patch(self.clsName + ".askCatsForEntries") as _ace,\
				patch("logging.Logger.warning") as _wa,\
				patch("logging.Logger.info") as _in,\
				patch("logging.Logger.debug") as _deb,\
				patch("physbiblio.database.Entries.getByBibkey",
					side_effect=[["a"], ["b"]]) as _gbb,\
				patch("physbiblio.database.Entries.getAll",
					side_effect=[["b"], [], []]) as _ga,\
				patch("physbiblio.database.Entries.prepareInsert",
					side_effect=["data1", "data2"]) as _pi,\
				patch("physbiblio.database.Entries.insert",
					side_effect=[True, True]) as _bi,\
				patch("physbiblio.database.Entries.setBook") as _sb,\
				patch("physbiblio.database.Entries.updateInspireID") as _ui,\
				patch("physbiblio.database.Entries.updateInfoFromOAI") as _ii,\
				patch("physbiblio.database.CatsEntries.delete") as _cd:
			self.assertFalse(self.mainW.advancedImport())
			_aid.assert_called_once_with()
			aid.exec_.assert_called_once_with()
			_im.assert_not_called()
			_ru.assert_called_once_with("test")
			self.assertEqual(_sc.call_count, 1)
			self.assertEqual(_rc.call_count, 1)
			_rmc.assert_called_once_with()
			_gbb.assert_has_calls([call(u'a', saveQuery=False),
				 call(u'b', saveQuery=False)])
			_ga.assert_not_called()
			_pi.assert_has_calls([
				call(u'@Article{a,\n        author = "gs",'
					+ '\n         title = "{T}",\n}\n\n'),
				call(u'@Article{b,\n        author = "sg",'
					+ '\n         title = "{tit}",\n           '
					+ 'doi = "2",\n         arxiv = "1",\n}\n\n')])
			_bi.assert_has_calls([call("data1"), call("data2")])
			_wa.assert_not_called()
			_sbm.assert_called_once_with(
				"Entries successfully imported: ['a', 'b']")
			_in.assert_has_calls([
				call("Element 'a' successfully inserted.\n"),
				call("Element 'b' successfully inserted.\n")])
			_sb.assert_has_calls([call("a"), call("b")])
			_cd.assert_not_called()
			_ace.assert_not_called()
			_ui.assert_not_called()
			_ii.assert_not_called()

		aid.comboMethod.setCurrentText("INSPIRE-HEP")
		aid.exec_.reset_mock()
		ais.exec_.reset_mock()
		with patch(self.modName + ".AdvancedImportDialog",
				return_value=aid) as _aid,\
				patch(self.modName + ".AdvancedImportSelect",
					return_value=ais) as _ais,\
				patch("PySide2.QtWidgets.QApplication.setOverrideCursor"
					) as _sc,\
				patch("PySide2.QtWidgets.QApplication.restoreOverrideCursor"
					) as _rc,\
				patch(self.modName + ".infoMessage") as _im,\
				patch(self.clsName + ".reloadMainContent") as _rmc,\
				patch(self.clsName + ".statusBarMessage") as _sbm,\
				patch("physbiblio.webimport.inspire.WebSearch.retrieveUrlAll",
					return_value='@article{a,\nauthor="gs",\ntitle="T"\n}\n'
						+ '@article{b,\nauthor="sg",\ntitle="tit"\n,'
						+ 'arxiv="1",\ndoi="2"\n}\n'
						) as _ru,\
				patch(self.clsName + ".askCatsForEntries") as _ace,\
				patch("logging.Logger.warning") as _wa,\
				patch("logging.Logger.info") as _in,\
				patch("logging.Logger.debug") as _deb,\
				patch("physbiblio.database.Entries.getByBibkey",
					side_effect=[["a"], ["b"]]) as _gbb,\
				patch("physbiblio.database.Entries.getAll",
					side_effect=[["b"], [], []]) as _ga,\
				patch("physbiblio.database.Entries.prepareInsert",
					side_effect=["data1", "data2"]) as _pi,\
				patch("physbiblio.database.Entries.insert",
					side_effect=[True, True]) as _bi,\
				patch("physbiblio.database.Entries.setBook") as _sb,\
				patch("physbiblio.database.Entries.updateInspireID",
					side_effect=["123", KeyError]) as _ui,\
				patch("physbiblio.database.Entries.updateInfoFromOAI") as _ii,\
				patch("physbiblio.database.CatsEntries.delete") as _cd:
			self.assertFalse(self.mainW.advancedImport())
			_aid.assert_called_once_with()
			aid.exec_.assert_called_once_with()
			_im.assert_not_called()
			_ru.assert_called_once_with("test")
			self.assertEqual(_sc.call_count, 1)
			self.assertEqual(_rc.call_count, 1)
			_rmc.assert_called_once_with()
			_gbb.assert_has_calls([call(u'a', saveQuery=False),
				 call(u'b', saveQuery=False)])
			_ga.assert_not_called()
			_pi.assert_has_calls([
				call(u'@Article{a,\n        author = "gs",'
					+ '\n         title = "{T}",\n}\n\n'),
				call(u'@Article{b,\n        author = "sg",'
					+ '\n         title = "{tit}",\n           '
					+ 'doi = "2",\n         arxiv = "1",\n}\n\n')])
			_bi.assert_has_calls([call("data1"), call("data2")])
			_wa.assert_called_once_with(
				"Failed in completing info for entry 'b'\n")
			_sbm.assert_called_once_with(
				"Entries successfully imported: ['a']")
			_in.assert_has_calls([
				call("Element 'a' successfully inserted.\n")])
			_sb.assert_not_called()
			_cd.assert_not_called()
			_ace.assert_not_called()
			_ui.assert_has_calls([call("a"), call("b")])
			_ii.assert_called_once_with("123")

	def test_cleanAllBibtexsAsk(self):
		"""test cleanAllBibtexsAsk"""
		with patch(self.modName + ".askGenericText",
					return_value=["a", False]) as _agt,\
				patch(self.clsName + ".cleanAllBibtexs") as _cab:
			self.assertEqual(self.mainW.cleanAllBibtexsAsk(), None)
			_agt.assert_called_once_with(
				"Insert the ordinal number of "
				+ "the bibtex element from which you want to start "
				+ "the cleaning:",
				"Where do you want to start cleanBibtexs from?",
				self.mainW)
			_cab.assert_not_called()

		with patch(self.modName + ".askYesNo", return_value=False) as _ay,\
				patch(self.modName + ".askGenericText",
					return_value=["a", True]) as _agt,\
				patch(self.clsName + ".cleanAllBibtexs") as _cab:
			self.assertEqual(self.mainW.cleanAllBibtexsAsk(), None)
			_agt.assert_called_once_with(
				"Insert the ordinal number of "
				+ "the bibtex element from which you want to start "
				+ "the cleaning:",
				"Where do you want to start cleanBibtexs from?",
				self.mainW)
			_ay.assert_called_once_with(
				"The text you inserted is not an integer. "
				+ "I will start from 0.\nDo you want to continue?",
				"Invalid entry")
			_cab.assert_not_called()

		with patch(self.modName + ".askYesNo", return_value=True) as _ay,\
				patch(self.modName + ".askGenericText",
					return_value=["a", True]) as _agt,\
				patch(self.clsName + ".cleanAllBibtexs") as _cab:
			self.assertEqual(self.mainW.cleanAllBibtexsAsk(), None)
			_agt.assert_called_once_with(
				"Insert the ordinal number of "
				+ "the bibtex element from which you want to start "
				+ "the cleaning:",
				"Where do you want to start cleanBibtexs from?",
				self.mainW)
			_ay.assert_called_once_with(
				"The text you inserted is not an integer. "
				+ "I will start from 0.\nDo you want to continue?",
				"Invalid entry")
			_cab.assert_called_once_with(0)

		with patch(self.modName + ".askYesNo", return_value=True) as _ay,\
				patch(self.modName + ".askGenericText",
					return_value=["12", True]) as _agt,\
				patch(self.clsName + ".cleanAllBibtexs") as _cab:
			self.assertEqual(self.mainW.cleanAllBibtexsAsk(), None)
			_agt.assert_called_once_with(
				"Insert the ordinal number of "
				+ "the bibtex element from which you want to start "
				+ "the cleaning:",
				"Where do you want to start cleanBibtexs from?",
				self.mainW)
			_ay.assert_not_called()
			_cab.assert_called_once_with(12)

	def test_cleanAllBibtexs(self):
		"""test cleanAllBibtexs"""
		with patch(self.clsName + ".statusBarMessage") as _sbm,\
				patch(self.clsName + "._runInThread") as _rit:
			self.mainW.cleanAllBibtexs()
			_sbm.assert_called_once_with(
				"Starting cleaning of bibtexs...")
			_rit.assert_called_once_with(Thread_cleanAllBibtexs,
				'Clean Bibtexs', 0, minProgress=0.0,
				progrStr='%) - cleaning: ', stopFlag=True,
				totStr='CleanBibtexs will process ', useEntries=None)
		with patch(self.clsName + ".statusBarMessage") as _sbm,\
				patch(self.clsName + "._runInThread") as _rit,\
				patch(self.clsName + ".refreshMainContent") as _rmc:
			self.mainW.cleanAllBibtexs(startFrom=12, useEntries=["a"])
			_sbm.assert_called_once_with(
				"Starting cleaning of bibtexs...")
			_rit.assert_called_once_with(Thread_cleanAllBibtexs,
				'Clean Bibtexs', 12, minProgress=0.0,
				progrStr='%) - cleaning: ', stopFlag=True,
				totStr='CleanBibtexs will process ', useEntries=["a"])

	def test_findBadBibtexs(self):
		"""test findBadBibtexs"""
		mainW = MainWindow(testing=True)
		def patcher(*args, **kwargs):
			mainW.badBibtexs = ["a", "b"]
		with patch(self.clsName + ".statusBarMessage") as _sbm,\
				patch(self.clsName + "._runInThread") as _rit,\
				patch(self.modName + ".infoMessage") as _im:
			self.mainW.findBadBibtexs()
			_sbm.assert_called_once_with("Starting checking bibtexs...")
			_rit.assert_called_once_with(
				Thread_findBadBibtexs, "Check Bibtexs",
				0, useEntries=None,
				totStr="findCorruptedBibtexs will process ",
				progrStr="%) - processing: ",
				minProgress=0., stopFlag=True)
			_im.assert_called_once_with("No invalid records found!")
		with patch(self.clsName + ".statusBarMessage") as _sbm,\
				patch(self.clsName + "._runInThread") as _rit,\
				patch(self.modName + ".infoMessage") as _im:
			self.mainW.findBadBibtexs(startFrom=12, useEntries=["abc"])
			_sbm.assert_called_once_with("Starting checking bibtexs...")
			_rit.assert_called_once_with(
				Thread_findBadBibtexs, "Check Bibtexs",
				12, useEntries=["abc"],
				totStr="findCorruptedBibtexs will process ",
				progrStr="%) - processing: ",
				minProgress=0., stopFlag=True)
			_im.assert_called_once_with("No invalid records found!")

		mainW._runInThread = patcher
		with patch(self.clsName + ".statusBarMessage") as _sbm,\
				patch(self.modName + ".askYesNo", return_value=False) as _ay,\
				patch(self.modName + ".infoMessage") as _im,\
				patch(self.modName + ".editBibtex") as _eb:
			mainW.findBadBibtexs()
			_im.assert_called_once_with(
				"These are the bibtex keys corresponding to invalid"
				+ " records:\na, b\n\nNo action will be performed.")
			_eb.assert_not_called()
		with patch(self.clsName + ".statusBarMessage") as _sbm,\
				patch(self.modName + ".askYesNo", return_value=True) as _ay,\
				patch(self.modName + ".editBibtex") as _eb:
			mainW.findBadBibtexs()
			_eb.assert_has_calls([call(mainW, "a"), call(mainW, "b")])

	def test_infoFromArxiv(self):
		"""test infoFromArxiv"""
		ffa = FieldsFromArxiv()
		ffa.output = ["title"]
		ffa.exec_ = MagicMock()
		ffa.result = False
		with patch(self.modName + ".FieldsFromArxiv",
				return_value=ffa) as _ffa,\
				patch("physbiblio.database.Entries.fetchAll") as _fa,\
				patch("physbiblio.database.Entries.fetchCursor",
					return_value=[{"bibkey": "a"}]) as _fc,\
				patch(self.clsName + ".statusBarMessage") as _sbm,\
				patch(self.clsName + "._runInThread") as _rit:
			self.mainW.infoFromArxiv()
			_ffa.assert_called_once_with()
			ffa.exec_.assert_called_once_with()
			_fa.assert_called_once_with(doFetch=False)
			_fc.assert_called_once_with()
			_sbm.assert_not_called()
			_rit.assert_not_called()

		ffa.result = True
		with patch(self.modName + ".FieldsFromArxiv",
				return_value=ffa) as _ffa,\
				patch("physbiblio.database.Entries.fetchAll") as _fa,\
				patch("physbiblio.database.Entries.fetchCursor",
					return_value=[{"bibkey": "a"}]) as _fc,\
				patch(self.clsName + ".statusBarMessage") as _sbm,\
				patch(self.clsName + "._runInThread") as _rit:
			self.mainW.infoFromArxiv()
			_ffa.assert_called_once_with()
			_fa.assert_called_once_with(doFetch=False)
			_fc.assert_called_once_with()
			_sbm.assert_called_once_with(
				"Starting importing info from arxiv...")
			_rit.assert_called_once_with(Thread_fieldsArxiv,
				'Get info from arXiv', ['a'], ['title'], minProgress=0.0,
				progrStr='%) - processing: arxiv:', stopFlag=True,
				totStr='Thread_fieldsArxiv will process ')
		with patch(self.modName + ".FieldsFromArxiv",
				return_value=ffa) as _ffa,\
				patch("physbiblio.database.Entries.fetchAll") as _fa,\
				patch("physbiblio.database.Entries.fetchCursor",
					return_value=[{"bibkey": "a"}]) as _fc,\
				patch(self.clsName + ".statusBarMessage") as _sbm,\
				patch(self.clsName + "._runInThread") as _rit:
			self.mainW.infoFromArxiv(
				useEntries=[{"bibkey": "a"}, {"bibkey": "b"}])
			_ffa.assert_called_once_with()
			_fa.assert_not_called()
			_fc.assert_not_called()
			_sbm.assert_called_once_with(
				"Starting importing info from arxiv...")
			_rit.assert_called_once_with(Thread_fieldsArxiv,
				'Get info from arXiv', ['a', 'b'], ['title'], minProgress=0.0,
				progrStr='%) - processing: arxiv:', stopFlag=True,
				totStr='Thread_fieldsArxiv will process ')

	def test_browseDailyArxiv(self):
		"""test browseDailyArxiv"""
		dad = DailyArxivDialog()
		dad.exec_ = MagicMock()
		dad.result = False
		dad.comboCat.setCurrentText("")
		with patch(self.modName + ".DailyArxivDialog",
				return_value=dad) as _dad:
			self.assertFalse(self.mainW.browseDailyArxiv())
			_dad.assert_called_once_with()
			dad.exec_.assert_called_once_with()

		dad.exec_ = MagicMock()
		dad.result = True
		dad.comboCat.setCurrentText("")
		with patch(self.modName + ".DailyArxivDialog",
				return_value=dad) as _dad:
			self.assertFalse(self.mainW.browseDailyArxiv())
			_dad.assert_called_once_with()
			dad.exec_.assert_called_once_with()

		with patch("physbiblio.gui.dialogWindows.DailyArxivDialog.updateCat"
				) as _uc:
			dad.comboCat.addItem("nonex")
			dad.comboCat.setCurrentText("nonex")
		dad.exec_ = MagicMock()
		dad.result = True
		with patch(self.modName + ".DailyArxivDialog",
				return_value=dad) as _dad,\
				patch("logging.Logger.warning") as _w,\
				patch("physbiblio.webimport.arxiv.WebSearch.arxivDaily",
					return_value=[]) as _ad:
			self.assertFalse(self.mainW.browseDailyArxiv())
			_dad.assert_called_once_with()
			dad.exec_.assert_called_once_with()
			_w.assert_called_once_with("Non-existent category! nonex")
			_ad.assert_not_called()

		dad.comboCat.setCurrentText("astro-ph")
		with patch(self.modName + ".DailyArxivDialog",
				return_value=dad) as _dad,\
				patch(self.modName + ".infoMessage") as _im,\
				patch("physbiblio.webimport.arxiv.WebSearch.arxivDaily",
					return_value=[]) as _ad:
			self.assertFalse(self.mainW.browseDailyArxiv())
			_dad.assert_called_once_with()
			_im.assert_called_once_with("No results obtained.")
			_ad.assert_called_once_with('astro-ph')

		dad.comboSub.setCurrentText("CO")
		with patch(self.modName + ".DailyArxivDialog",
				return_value=dad) as _dad,\
				patch(self.modName + ".infoMessage") as _im,\
				patch("physbiblio.webimport.arxiv.WebSearch.arxivDaily",
					return_value=[]) as _ad:
			self.assertFalse(self.mainW.browseDailyArxiv())
			_dad.assert_called_once_with()
			_im.assert_called_once_with("No results obtained.")
			_ad.assert_called_once_with('astro-ph.CO')

		das = DailyArxivSelect(
			{"12.345":
				{"bibpars": {
					"author": "me",
					"title": "title",
					"type": "",
					"eprint": "12.345",
					"replacement": False,
					"cross": False,
					"abstract": "some text",
					"primaryclass": "astro-ph"},
				"exist": 1}},
			self.mainW)
		self.mainW.importArXivResults = (['12.345'], [])
		das.abstractFormulas = AbstractFormulas
		das.exec_ = MagicMock()
		das.askCats.setCheckState(Qt.Unchecked)
		das.selected = {"12.345": True}
		das.result = False
		with patch(self.modName + ".DailyArxivDialog",
				return_value=dad) as _dad,\
				patch(self.modName + ".DailyArxivSelect",
					return_value=das) as _das,\
				patch("PySide2.QtWidgets.QApplication.setOverrideCursor"
					) as _sc,\
				patch("PySide2.QtWidgets.QApplication.restoreOverrideCursor"
					) as _rc,\
				patch(self.clsName + ".reloadMainContent") as _rmc,\
				patch(self.modName + ".infoMessage") as _im,\
				patch("physbiblio.webimport.arxiv.WebSearch.arxivDaily",
					return_value=[
						{"replacement": False,
						"cross": False,
						"eprint": "12.345"}
					]) as _ad:
			self.assertFalse(self.mainW.browseDailyArxiv())
			_dad.assert_called_once_with()
			_im.assert_not_called()
			_ad.assert_called_once_with('astro-ph.CO')
			_das.assert_called_once_with(
				{'12.345': {'exist': False, 'bibpars':
					{'type': '', 'eprint': '12.345',
					'cross': False, 'replacement': False}}},
				self.mainW)
			das.exec_.assert_called_once_with()
			self.assertEqual(_sc.call_count, 1)
			self.assertEqual(_rc.call_count, 1)
			_rmc.assert_called_once_with()

		das.exec_ = MagicMock()
		das.result = True
		with patch(self.modName + ".DailyArxivDialog",
				return_value=dad) as _dad,\
				patch(self.modName + ".DailyArxivSelect",
					return_value=das) as _das,\
				patch("PySide2.QtWidgets.QApplication.setOverrideCursor"
					) as _sc,\
				patch("PySide2.QtWidgets.QApplication.restoreOverrideCursor"
					) as _rc,\
				patch(self.clsName + ".askCatsForEntries") as _ace,\
				patch(self.clsName + ".reloadMainContent") as _rmc,\
				patch(self.clsName + ".statusBarMessage") as _sbm,\
				patch(self.modName + ".infoMessage") as _im,\
				patch("physbiblio.webimport.arxiv.WebSearch.arxivDaily",
					return_value=[
						{"replacement": False,
						"cross": False,
						"eprint": "12.345"}
					]) as _ad,\
				patch(self.clsName + "._runInThread") as _rit:
			self.assertFalse(self.mainW.browseDailyArxiv())
			_dad.assert_called_once_with()
			_im.assert_not_called()
			_ad.assert_called_once_with('astro-ph.CO')
			_das.assert_called_once_with(
				{'12.345': {'exist': False, 'bibpars':
					{'type': '', 'eprint': '12.345',
					'cross': False, 'replacement': False}}},
				self.mainW)
			das.exec_.assert_called_once_with()
			self.assertEqual(_sc.call_count, 1)
			self.assertEqual(_rc.call_count, 1)
			_rmc.assert_called_once_with()
			_sbm.assert_called_once_with(
				"Entries successfully imported: ['12.345']")
			_rit.assert_called_once_with(Thread_importDailyArxiv,
				'Import from arXiv',
				{'12.345': {'exist': False, 'bibpars':
					{'type': '', 'eprint': '12.345', 'cross': False,
					'replacement': False}}},
				stopFlag=True)
			_ace.assert_not_called()

		das.exec_ = MagicMock()
		das.askCats.setCheckState(Qt.Checked)
		with patch(self.modName + ".DailyArxivDialog",
				return_value=dad) as _dad,\
				patch(self.modName + ".DailyArxivSelect",
					return_value=das) as _das,\
				patch("PySide2.QtWidgets.QApplication.setOverrideCursor"
					) as _sc,\
				patch("PySide2.QtWidgets.QApplication.restoreOverrideCursor"
					) as _rc,\
				patch(self.clsName + ".askCatsForEntries") as _ace,\
				patch(self.clsName + ".reloadMainContent") as _rmc,\
				patch(self.clsName + ".statusBarMessage") as _sbm,\
				patch(self.modName + ".infoMessage") as _im,\
				patch("physbiblio.webimport.arxiv.WebSearch.arxivDaily",
					return_value=[
						{"replacement": False,
						"cross": False,
						"eprint": "12.345"}
					]) as _ad,\
				patch("physbiblio.database.CatsEntries.delete") as _cd,\
				patch(self.clsName + "._runInThread") as _rit:
			self.assertFalse(self.mainW.browseDailyArxiv())
			_dad.assert_called_once_with()
			_im.assert_not_called()
			_ad.assert_called_once_with('astro-ph.CO')
			_das.assert_called_once_with(
				{'12.345': {'exist': False, 'bibpars':
					{'type': '', 'eprint': '12.345',
					'cross': False, 'replacement': False}}},
				self.mainW)
			das.exec_.assert_called_once_with()
			self.assertEqual(_sc.call_count, 1)
			self.assertEqual(_rc.call_count, 1)
			_rmc.assert_called_once_with()
			_sbm.assert_called_once_with(
				"Entries successfully imported: ['12.345']")
			_rit.assert_called_once_with(Thread_importDailyArxiv,
				'Import from arXiv',
				{'12.345': {'exist': False, 'bibpars':
					{'type': '', 'eprint': '12.345', 'cross': False,
					'replacement': False}}},
				stopFlag=True)
			_ace.assert_called_once_with(['12.345'])
			_cd.assert_called_once_with(
				pbConfig.params["defaultCategories"], '12.345')

		das = DailyArxivSelect(
			{"12.345":
				{"bibpars": {
					"author": "me1",
					"title": "title1",
					"type": "",
					"eprint": "12.345",
					"replacement": False,
					"cross": False,
					"abstract": "some text",
					"primaryclass": "astro-ph"},
				"exist": 1},
			"12.346":
				{"bibpars": {
					"author": "me2",
					"title": "title2",
					"type": "",
					"eprint": "12.346",
					"replacement": False,
					"cross": True,
					"abstract": "some other text",
					"primaryclass": "astro-ph.CO"},
				"exist": 1},
			"12.347":
				{"bibpars": {
					"author": "me3",
					"title": "title3",
					"type": "",
					"eprint": "12.347",
					"replacement": False,
					"cross": False,
					"abstract": "some more text",
					"primaryclass": "hep-ph"},
				"exist": 1},
			"12.348":
				{"bibpars": {
					"author": "me4",
					"title": "title4",
					"type": "",
					"eprint": "12.348",
					"replacement": False,
					"cross": False,
					"abstract": "some more text",
					"primaryclass": "hep-ph"},
				"exist": 1},
			"12.349":
				{"bibpars": {
					"author": "me5",
					"title": "title5",
					"type": "",
					"eprint": "12.349",
					"replacement": False,
					"cross": False,
					"abstract": "some more text",
					"primaryclass": "hep-ex"},
				"exist": 1}},
			self.mainW)
		self.mainW.importArXivResults = (
			['12.345', '12.348', '12.350'], ['12.346', '12.348'])
		das.abstractFormulas = AbstractFormulas
		das.exec_ = MagicMock()
		das.askCats.setCheckState(Qt.Unchecked)
		das.selected = {"12.345": True, "12.346": True,
			"12.347": False, "12.348": True, "12.349": True}
		das.result = True
		das.askCats.setCheckState(Qt.Checked)
		with patch(self.modName + ".DailyArxivDialog",
				return_value=dad) as _dad,\
				patch(self.modName + ".DailyArxivSelect",
					return_value=das) as _das,\
				patch("PySide2.QtWidgets.QApplication.setOverrideCursor"
					) as _sc,\
				patch("PySide2.QtWidgets.QApplication.restoreOverrideCursor"
					) as _rc,\
				patch(self.clsName + ".askCatsForEntries") as _ace,\
				patch(self.clsName + ".reloadMainContent") as _rmc,\
				patch(self.clsName + ".statusBarMessage") as _sbm,\
				patch(self.modName + ".infoMessage") as _im,\
				patch("physbiblio.webimport.arxiv.WebSearch.arxivDaily",
					return_value=[
						{"author": "me1",
						"title": "title1",
						"type": "",
						"eprint": "12.345",
						"replacement": True,
						"cross": False,
						"abstract": "some text",
						"primaryclass": "astro-ph"},
						{"author": "me2",
						"title": "title2",
						"type": "",
						"eprint": "12.346",
						"replacement": True,
						"cross": True,
						"abstract": "some other text",
						"primaryclass": "astro-ph.CO"},
						{"author": "me3",
						"title": "title3",
						"type": "",
						"eprint": "12.347",
						"replacement": False,
						"cross": True,
						"abstract": "some more text",
						"primaryclass": "hep-ph"},
						{"author": "me4",
						"title": "title4",
						"type": "",
						"eprint": "12.348",
						"replacement": False,
						"cross": False,
						"abstract": "some more text",
						"primaryclass": "hep-ph"},
						{"author": "me5",
						"title": "title5",
						"type": "",
						"eprint": "12.349",
						"replacement": False,
						"cross": False,
						"abstract": "some more text",
						"primaryclass": "hep-ex"}
					]) as _ad,\
				patch(self.clsName + "._runInThread") as _rit:
			self.assertFalse(self.mainW.browseDailyArxiv())
			_dad.assert_called_once_with()
			_im.assert_not_called()
			_ad.assert_called_once_with('astro-ph.CO')
			_das.assert_called_once_with(
				{'12.346': {'exist': False, 'bibpars':
					{'eprint': '12.346', 'primaryclass': 'astro-ph.CO',
					'author': 'me2', 'abstract': 'some other text',
					'title': 'title2', 'type': '[replacement][cross-listed]',
					'cross': True, 'replacement': True}},
				'12.347': {'exist': False, 'bibpars':
					{'eprint': '12.347', 'primaryclass': 'hep-ph',
					'author': 'me3', 'abstract': 'some more text',
					'title': 'title3', 'type': '[cross-listed]',
					'cross': True, 'replacement': False}},
				'12.345': {'exist': False, 'bibpars':
					{'eprint': '12.345', 'primaryclass': 'astro-ph',
					'author': 'me1', 'abstract': 'some text',
					'title': 'title1', 'type': '[replacement]',
					'cross': False, 'replacement': True}},
				'12.348': {'exist': False, 'bibpars':
					{'eprint': '12.348', 'primaryclass': 'hep-ph',
					'author': 'me4', 'abstract': 'some more text',
					'title': 'title4', 'type': '', 'cross': False,
					'replacement': False}},
				'12.349': {'exist': False, 'bibpars':
					{'eprint': '12.349', 'primaryclass': 'hep-ex',
					'author': 'me5', 'abstract': 'some more text',
					'title': 'title5', 'type': '', 'cross': False,
					'replacement': False}}},
				self.mainW)
			self.assertEqual(_sc.call_count, 1)
			self.assertEqual(_rc.call_count, 1)
			_rmc.assert_called_once_with()
			_rit.assert_called_once_with(Thread_importDailyArxiv,
				'Import from arXiv',
				{'12.346': {'exist': False, 'bibpars': {'eprint': '12.346',
				'primaryclass': 'astro-ph.CO', 'author': 'me2',
				'abstract': 'some other text', 'title': 'title2',
				'type': '[replacement][cross-listed]', 'cross': True,
				'replacement': True}},
				'12.345': {'exist': False, 'bibpars': {'eprint': '12.345',
				'primaryclass': 'astro-ph', 'author': 'me1', 'abstract':
					'some text', 'title': 'title1', 'type': '[replacement]',
					'cross': False, 'replacement': True}},
				'12.348': {'exist': False, 'bibpars': {'eprint': '12.348',
				'primaryclass': 'hep-ph', 'author': 'me4', 'abstract':
					'some more text', 'title': 'title4', 'type': '',
					'cross': False, 'replacement': False}},
				'12.349': {'exist': False, 'bibpars': {'eprint': '12.349',
				'primaryclass': 'hep-ex', 'author': 'me5', 'abstract':
					'some more text', 'title': 'title5', 'type': '',
					'cross': False, 'replacement': False}}},
				stopFlag=True)
			_ace.assert_called_once_with(["12.345", "12.348", "12.350"])
			_sbm.assert_called_once_with(
				"Entries successfully imported: "
				+ "['12.345', '12.348', '12.350']")

	def test_sendMessage(self):
		"""test sendMessage"""
		with patch(self.modName + ".infoMessage") as _i:
			self.mainW.sendMessage("mytext")
			_i.assert_called_once_with("mytext")

	def test_done(self):
		"""test done"""
		with patch(self.clsName + ".statusBarMessage") as _sm:
			self.mainW.done()
			_sm.assert_called_once_with("...done!")


if __name__=='__main__':
	unittest.main()
