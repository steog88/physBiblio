#!/usr/bin/env python
"""
Test file for the physbiblio.firstOpen module.

This file is part of the PhysBiblio package.
"""
import sys, traceback
import six
import datetime

if sys.version_info[0] < 3:
	import unittest2 as unittest
	from mock import patch, call
	from StringIO import StringIO
else:
	import unittest
	from unittest.mock import patch, call
	from io import StringIO

try:
	from physbiblio.setuptests import *
	from physbiblio.errors import pBErrorManager
	from physbiblio.config import pbConfig
	from physbiblio.database import physbiblioDB
	from physbiblio.firstOpen import createTables
except ImportError:
    print("Could not find physbiblio and its contents: configure your PYTHONPATH!")
    raise
except Exception:
	print(traceback.format_exc())

class TestFirstOpenMethods(unittest.TestCase):
	"""Tests for methods in physbiblio.firstOpen"""

	def test_createTables(self):
		"""Test that all the tables are created at first time, if DB is empty"""
		tempDBName = os.path.join(pbConfig.path, "tests_first_%s.db"%today_ymd)
		if os.path.exists(tempDBName):
			os.remove(tempDBName)
		open(tempDBName, 'a').close()
		self.pBDB = physbiblioDB(tempDBName, noOpen = True)
		self.pBDB.openDB()

		self.assertTrue(self.pBDB.cursExec("SELECT name FROM sqlite_master WHERE type='table';"))
		self.assertEqual([name[0] for name in self.pBDB.cursor()], [])
		createTables(self.pBDB)
		self.assertTrue(self.pBDB.cursExec("SELECT name FROM sqlite_master WHERE type='table';"))
		self.assertEqual(sorted([name[0] for name in self.pBDB.cursor()]), ["categories", "entries", "entryCats", "entryExps", "expCats", "experiments"])
		self.assertTrue([e["name"] for e in self.pBDB.cats.getAll()], ["Main", "Tags"])

		os.remove(tempDBName)
		open(tempDBName, 'a').close()
		self.pBDB = physbiblioDB(tempDBName)
		self.assertTrue(self.pBDB.cursExec("SELECT name FROM sqlite_master WHERE type='table';"))
		self.assertEqual(sorted([name[0] for name in self.pBDB.cursor()]), ["categories", "entries", "entryCats", "entryExps", "expCats", "experiments"])
		self.assertTrue([e["name"] for e in self.pBDB.cats.getAll()], ["Main", "Tags"])
