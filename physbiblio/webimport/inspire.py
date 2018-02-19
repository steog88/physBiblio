"""
Module that deals with importing info from the INSPIRE-HEP API.
"""
import traceback
try:
	from physbiblio.errors import pBErrorManager
except ImportError:
	print("Could not find physbiblio.errors and its contents: configure your PYTHONPATH!")
	print(traceback.format_exc())
from physbiblio.config import pbConfig
from physbiblio.webimport.webInterf import *
from physbiblio.parse_accents import *

class webSearch(webInterf):
	"""Subclass of webInterf that can connect to INSPIRE-HEP to perform searches"""
	def __init__(self):
		"""
		Initializes the class variables using the webInterf constructor.

		Define additional specific parameters for the INSPIRE-HEP API.
		"""
		webInterf.__init__(self)
		self.name = "inspire"
		self.description = "INSPIRE fetcher"
		self.url = pbConfig.inspireSearchBase
		self.urlRecord = pbConfig.inspireRecord
		self.urlArgs = {
			#"action_search": "Search",
			"sf": "year",
			"so": "a",
			"rg": "250",
			"sc": "0",
			"eb": "B",
			"of": "hx"#for bibtex format ---- hb for standard format, for retrieving inspireid
			}
		
	def retrieveUrlFirst(self, string):
		"""
		Retrieves the first result from the content of the given web page.

		Parameters:
			string: the search string

		Output:
			returns the bibtex string obtained from the API
		"""
		self.urlArgs["p"] = "\"" + string + "\""
		url = self.createUrl()
		print("[inspire] search %s -> %s"%(string, url))
		text = self.textFromUrl(url)
		try:
			i1 = text.find("<pre>")
			i2 = text.find("</pre>")
			if i1 > 0 and i2 > 0:
				bibtex = text[i1 + 5 : i2]
			else:
				bibtex = ""
			return parse_accents_str(bibtex)
		except Exception:
			pBErrorManager("[inspire] -> ERROR: impossible to get results", traceback)
			return ""
		
	def retrieveUrlAll(self, string):
		"""
		Retrieves all the result from the content of the given web page.

		Parameters:
			string: the search string

		Output:
			returns the bibtex string obtained from the API
		"""
		self.urlArgs["p"] = "\"" + string + "\""
		url = self.createUrl()
		print("[inspire] search %s -> %s"%(string, url))
		text = self.textFromUrl(url)
		try:
			i1 = text.find("<pre>")
			i2 = text.rfind("</pre>")
			if i1 > 0 and i2 > 0:
				bibtex = text[i1 + 5 : i2]
			else:
				bibtex = ""
			return parse_accents_str(bibtex.replace("<pre>", "").replace("</pre>", ""))
		except Exception:
			pBErrorManager("[inspire] -> ERROR: impossible to get results", traceback)
			return ""
	
	def retrieveInspireID(self, string, number = None):
		"""
		Read the fetched content for a given entry to obtain its INSPIRE-HEP ID

		Parameters:
			string: the search string
			number (optional): the integer corresponding to the desired entry in the list, if more than one is present
		"""
		i = 0
		self.urlArgs["p"] = "\"" + string + "\""
		self.urlArgs["of"] = "hb" #do not ask bibtex, but standard
		url = self.createUrl()
		self.urlArgs["of"] = "hx" #restore
		print("[inspire] search ID of %s -> %s"%(string, url))
		text = self.textFromUrl(url)
		try:
			searchID = re.compile('titlelink(.*)?(http|https)://inspirehep.net/record/([0-9]*)?">')
			for q in searchID.finditer(text):
				if len(q.group()) > 0:
					if number is None or i == number:
						inspireID = q.group(3)
						break
					else:
						i += 1
			print("[inspire] found: %s"%inspireID)
			return inspireID
		except Exception:
			pBErrorManager("[inspire] -> ERROR: impossible to get results", traceback)
			return ""
