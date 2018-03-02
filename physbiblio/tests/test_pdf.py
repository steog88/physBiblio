#!/usr/bin/env python
"""
Test file for the physbiblio.pdf module.

This file is part of the PhysBiblio package.
"""
import sys, traceback, os
import shutil

if sys.version_info[0] < 3:
	import unittest2 as unittest
	from mock import MagicMock, patch, call
else:
	import unittest
	from unittest.mock import MagicMock, patch, call

try:
	from physbiblio.setuptests import *
	from physbiblio.errors import pBErrorManager
	from physbiblio.config import pbConfig
	from physbiblio.database import pBDB, physbiblioDB
	from physbiblio.pdf import pBPDF
except ImportError:
    print("Could not find physbiblio and its contents: configure your PYTHONPATH!")
    raise
except Exception:
	print(traceback.format_exc())

@unittest.skipIf(skipLongTests, "Long tests")
class TestPdfMethods(unittest.TestCase):
	"""
	Test the methods and functions in the pdf module
	"""
	def test_fnames(self):
		"""Test names of folders and directories"""
		self.assertEqual(pBPDF.badFName(r'a\b/c:d*e?f"g<h>i|' + "j'"),
			"a_b_c_d_e_f_g_h_i_j_")
		self.assertEqual(pBPDF.getFileDir(r'a\b/c:d*e?f"g<h>i|' + "j'"),
			os.path.join(pBPDF.pdfDir, "a_b_c_d_e_f_g_h_i_j_"))
		testPaperFolder = pBPDF.getFileDir("abc.def")
		pBDB.bibs.getField = MagicMock(return_value="12345678")
		self.assertEqual(pBPDF.getFilePath("abc.def", "arxiv"),
			os.path.join(testPaperFolder, "12345678.pdf"))

	def test_manageFiles(self):
		"""Test creation, copy and deletion of files and folders"""
		emptyPdfName = os.path.join(pBPDF.pdfDir, "tests_%s.pdf"%today_ymd)
		pBPDF.createFolder("abc.def")
		self.assertTrue(os.path.exists(pBPDF.getFileDir("abc.def")))
		pBPDF.renameFolder("abc.def", "abc.fed")
		self.assertFalse(os.path.exists(pBPDF.getFileDir("abc.def")))
		self.assertTrue(os.path.exists(pBPDF.getFileDir("abc.fed")))
		open(emptyPdfName, 'a').close()
		pBDB.bibs.getField = MagicMock(return_value="12345678")
		pBPDF.copyNewFile("abc.fed", emptyPdfName, "arxiv")
		pBPDF.copyNewFile("abc.fed", emptyPdfName,
			customName = "empty.pdf")
		self.assertTrue(os.path.exists(pBPDF.getFilePath("abc.fed", "arxiv")))
		os.remove(emptyPdfName)
		self.assertFalse(os.path.exists(emptyPdfName))
		pBPDF.copyToDir(pBPDF.pdfDir, "abc.fed", "arxiv")
		self.assertTrue(os.path.exists(os.path.join(pBPDF.pdfDir, "12345678.pdf")))
		self.assertTrue(pBPDF.removeFile("abc.fed", "arxiv"))
		self.assertFalse(pBPDF.removeFile("abc.fed", "arxiv"))
		os.remove(os.path.join(pBPDF.pdfDir, "12345678.pdf"))
		shutil.rmtree(pBPDF.getFileDir("abc.fed"))

	@unittest.skipIf(skipOnlineTests, "Long tests")
	def test_download(self):
		"""Test downloadArxiv"""
		pBDB.bibs.getField = MagicMock(return_value="1507.08204")
		self.assertTrue(pBPDF.downloadArxiv("abc.def"))
		self.assertTrue(pBPDF.checkFile("abc.def", "arxiv"))
		self.assertEqual(pBPDF.getExisting("abc.def", fullPath = False),
			["1507.08204.pdf"])
		self.assertEqual(pBPDF.getExisting("abc.def", fullPath = True),
			[os.path.join(pBPDF.getFileDir("abc.def"), "1507.08204.pdf")])
		self.assertTrue(pBPDF.removeFile("abc.def", "arxiv"))
		self.assertFalse(pBPDF.checkFile("abc.def", "arxiv"))
		pBDB.bibs.getField = MagicMock(return_value="1801.15000")
		self.assertFalse(pBPDF.downloadArxiv("abc.def"))
		pBDB.bibs.getField = MagicMock(return_value="")
		self.assertFalse(pBPDF.downloadArxiv("abc.def"))
		pBDB.bibs.getField = MagicMock(return_value=None)
		self.assertFalse(pBPDF.downloadArxiv("abc.def"))
		shutil.rmtree(pBPDF.getFileDir("abc.def"))

	def test_removeSpare(self):
		"""Test finding spare folders"""
		pBDB.bibs.getAll = MagicMock(return_value=[{"bibkey":"abc"}, {"bibkey":"def"}])
		pBPDF.pdfDir = os.path.join(pbConfig.path, "tmppdf_%s"%today_ymd)
		for q in ["abc", "def", "ghi"]:
			pBPDF.createFolder(q)
			self.assertTrue(os.path.exists(pBPDF.getFileDir(q)))
		pBPDF.removeSparePDFFolders()
		for q in ["abc", "def"]:
			self.assertTrue(os.path.exists(pBPDF.getFileDir(q)))
		self.assertFalse(os.path.exists(pBPDF.getFileDir("ghi")))
		shutil.rmtree(pBPDF.pdfDir)

if __name__=='__main__':
	print("\nStarting tests...\n")
	unittest.main()