import sys, re, os
import urllib2
import socket
import pkgutil, traceback
try:
	from physbiblio.errors import pBErrorManager
except ImportError:
	print("Could not find physbiblio.errors and its contents: configure your PYTHONPATH!")
	print(traceback.format_exc())
try:
	import physbiblio.webimport as wi
	#from physbiblio.database import *
	from physbiblio.config import pbConfig
except ImportError:
	pBErrorManager("Could not find physbiblio and its contents: configure your PYTHONPATH!", traceback)
pkgpath = os.path.dirname(wi.__file__)
webInterfaces = [name for _, name, _ in pkgutil.iter_modules([pkgpath])]

class webInterf():
	"""this is the main class for the web search methods"""
	def __init__(self):
		"""initializes the class variables"""
		self.url = None
		self.urlArgs = None
		self.urlTimeout = float(pbConfig.params["timeoutWebSearch"])
		#save the names of the available web search interfaces
		self.interfaces = [ a for a in webInterfaces if a != "webInterf" ]
		self.webSearch = {}
		self.loaded = False
		
	def createUrl(self):
		"""joins the arguments of the GET query to get the full url"""
		return self.url + "?" + "&".join([a + "=" + b for a, b in self.urlArgs.iteritems()])
		
	def textFromUrl(self, url, headers = None):
		"""use urllib to get the html content of the given url"""
		try:
			if headers is not None:
				req = urllib2.Request(url, headers = headers)
			else:
				req = urllib2.Request(url)
			response = urllib2.urlopen(req, timeout = self.urlTimeout)
			data = response.read()
		except urllib2.URLError:
			pBErrorManager("[%s] -> error in retrieving data from url"%self.name)
			return None
		except socket.timeout:
			pBErrorManager("[%s] -> timed out"%self.name)
			return None
		try:
			text = data.decode('utf-8')
		except:
			pBErrorManager("[%s] -> bad codification, utf-8 decode failed"%self.name)
			return None
		return text
	
	def retrieveUrlFirst(self, search):
		"""retrieves the first bibtexs that the search gives"""
		return None
	def retrieveUrlAll(self, search):
		"""retrieves all the bibtexs that the search gives"""
		return None
	
	def loadInterfaces(self):
		"""load the codes that will interface with the main websites to search bibtex info into a dictionary of classes"""
		if self.loaded:
			return
		for q in self.interfaces:
			try:
				_temp = __import__("physbiblio.webimport." + q, globals(), locals(), ["webSearch"], -1)
				self.webSearch[q] = getattr(_temp, "webSearch")()
			except:
				pBErrorManager("physbiblio.webimport.%s import error"%q)
		self.loaded = True
	
	def retrieveUrlFirstFrom(self, search, method):
		"""will call subclass method"""
		getattr(self.webSearch[method], retrieveUrlFirst)(search)
		
	def retrieveUrlAllFrom(self, search, method):
		"""will call subclass method"""
		getattr(self.webSearch[method], retrieveUrlAll)(search)

physBiblioWeb = webInterf()
physBiblioWeb.loadInterfaces()