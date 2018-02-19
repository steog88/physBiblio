#!/usr/bin/env python
"""
Test file for the packages in the PhysBiblio application, a bibliography manager written in Python.

This file is part of the PhysBiblio package.
"""
import sys, datetime, traceback

try:
	from physbiblio.errors import pBErrorManager
	from physbiblio.webimport.webInterf import physBiblioWeb
except ImportError:
    print("Could not find physbiblio and its contents: configure your PYTHONPATH!")
    raise
except Exception:
	print(traceback.format_exc())

def test_pBErrorManager():
	"""
	Test pBErrorManager raising few exceptions.
	"""
	try:
		raise Exception("Test warning")
	except Exception as e:
		pBErrorManager(str(e), traceback, priority = 0)
	try:
		raise Exception("Test error")
	except Exception as e:
		pBErrorManager(str(e), traceback, priority = 1)
	try:
		raise Exception("Test critical error")
	except Exception as e:
		pBErrorManager(str(e), traceback, priority = 2)

def test_webImport():
	"""
	Test the functions that import entries from the web.
	Should not fail if everything works fine.

	Tests also pbWriter._entry_to_bibtex using the other functions
	"""
	print(physBiblioWeb.webSearch.keys())
	tests = {
		"arxiv": "1507.08204",
		"doi": "10.1088/0954-3899/43/3/033001",
		"inspire": "Gariazzo:2015rra",
		"inspireoai": "1385583",
		"isbn": "9780198508717",
		}
	for method, string in tests.items():
		if method == "inspireoai":
			print(physBiblioWeb.webSearch[method].retrieveOAIData(string))
		else:
			print(physBiblioWeb.webSearch[method].retrieveUrlFirst(string))
			print(physBiblioWeb.webSearch[method].retrieveUrlAll(string))
	print(physBiblioWeb.webSearch["inspire"].retrieveInspireID(tests["inspire"]))

	date1 = (datetime.date.today() - datetime.timedelta(1)).strftime("%Y-%m-%d")
	date2 = datetime.date.today().strftime("%Y-%m-%d")
	yren, monen, dayen = date1.split('-')
	yrst, monst, dayst = date2.split('-')
	date1 = datetime.datetime(int(yren), int(monen), int(dayen))
	date2 = datetime.datetime(int(yrst), int(monst), int(dayst))
	print(physBiblioWeb.webSearch["inspireoai"].retrieveOAIUpdates(date1, date2))

if __name__=='__main__':
	test_pBErrorManager()
	test_webImport()
