"""
Use INSPIRE-HEP OAI API to collect information on single papers (given the identifier) or to harvest updates in a given time period.

This file is part of the PhysBiblio package.
"""
import sys, time
import codecs

if sys.version_info[0] < 3:
	#needed to set utf-8 as encoding
	reload(sys)
	sys.setdefaultencoding('utf-8')
	from httplib import IncompleteRead
else:
	from http.client import IncompleteRead

import datetime, traceback

import bibtexparser
from oaipmh.client import Client
from oaipmh.error import ErrorBase
from oaipmh.metadata import MetadataRegistry

if sys.version_info[0] < 3:
    from StringIO import StringIO
else:
    from io import StringIO
from lxml.etree import tostring
from pymarc import marcxml, MARCWriter, field
from oaipmh import metadata

try:
	from physbiblio.webimport.webInterf import *
	from physbiblio.parse_accents import *
	from bibtexparser.bibdatabase import BibDatabase
	from physbiblio.bibtexwriter import pbWriter
	from physbiblio.errors import pBErrorManager
except ImportError:
	print("Could not find physbiblio.errors and its contents: configure your PYTHONPATH!")
	print(traceback.format_exc())

def safe_list_get(l, idx, default = ""):
	"""
	Safely get an element from a list.
	No error if it doesn't exist...
	"""
	if l is not None:
		try:
			return l[idx]
		except IndexError:
			return default
	else:
		return default
		
def get_journal_ref_xml(marcxml):
	"""
	Read the marcxml record and write the info on the publication
	"""
	p = []
	y = []
	v = []
	c = []
	m = []
	x = []
	t = []
	w = []
	if marcxml["773"] is not None:
		for q in marcxml.get_fields("773"):
			p.append(parse_accents_str(q["p"]))	#journal name (even if submitted to only)
			v.append(parse_accents_str(q["v"]))	#volume
			y.append(parse_accents_str(q["y"]))	#year
			c.append(parse_accents_str(q["c"]))	#pages
			
			m.append(parse_accents_str(q["m"]))	#Erratum, Addendum, Publisher note
			
			x.append(parse_accents_str(q["x"]))	#freetext journal/book info
			t.append(parse_accents_str(q["t"]))	#for conf papers: presented at etc, freetext or KB?
			w.append(parse_accents_str(q["w"]))	#for conf papers: conference code
	return p, v, y, c, m, x, t, w

class MARCXMLReader(object):
	"""Returns the PyMARC record from the OAI structure for MARC XML"""
	def __call__(self, element):
		handler = marcxml.XmlHandler()
		if sys.version_info[0] < 3:
			marcxml.parse_xml(StringIO(tostring(element[0], encoding='UTF-8')), handler)
		else:
			marcxml.parse_xml(StringIO(tostring(element[0], encoding=str)), handler)
		return handler.records[0]

marcxml_reader = MARCXMLReader()

registry = metadata.MetadataRegistry()
registry.registerReader('marcxml', marcxml_reader)

class webSearch(webInterf):
	"""Subclass of webInterf that can connect to INSPIRE-HEP to perform searches using the OAI API"""
	def __init__(self):
		"""
		Initializes the class variables using the webInterf constructor.

		Define additional specific parameters for the INSPIRE-HEP OAI API.
		"""
		webInterf.__init__(self)
		self.name = "inspireoai"
		self.description = "INSPIRE OAI interface"
		self.url = "http://inspirehep.net/oai2d"
		self.oai = Client(self.url, registry)
		self.correspondences = [
			["id", "inspire"],
			["year", "year"],
			["arxiv", "arxiv"],
			["oldkeys", "old_keys"],
			["firstdate", "firstdate"],
			["pubdate", "pubdate"],
			["doi", "doi"],
			["ads", "ads"],
			["isbn", "isbn"],
			["bibtex", "bibtex"],
		]
		self.bibtexFields = [
			"author", "title",
			"journal", "volume", "year", "pages",
			"arxiv", "primaryclass", "archiveprefix", "eprint",
			"doi", "isbn",
			"school", "reportnumber", "booktitle", "collaboration"]
		
	def retrieveUrlFirst(self,string):
		"""
		The OAI interface is not for string searches: use the retrieveOAIData function if you have the INSPIRE ID of the desired record
		"""
		pBErrorManager("[oai] -> ERROR: inspireoai cannot search strings in the DB")
		return ""
		
	def retrieveUrlAll(self,string):
		"""
		The OAI interface is not for string searches: use the retrieveOAIData function if you have the INSPIRE ID of the desired record
		"""
		pBErrorManager("[oai] -> ERROR: inspireoai cannot search strings in the DB")
		return ""
		
	def readRecord(self, record, readConferenceTitle = False):
		"""
		Read the content of a marcxml record to return a bibtex string
		"""
		tmpDict = {}
		record.to_unicode = True
		record.force_utf8 = True
		arxiv = ""
		tmpOld = []
		try:
			tmpDict["doi"] = None
			for q in record.get_fields('024'):
				if q["2"] == "DOI":
					tmpDict["doi"] = q["a"]
		except Exception as e:
			print(traceback.format_exc())
		try:
			tmpDict["arxiv"]  = None
			tmpDict["bibkey"] = None
			tmpDict["ads"]    = None
			for q in record.get_fields('035'):
				if q["9"] == "arXiv":
					tmp = q["a"]
					if tmp is not None:
						arxiv = tmp.replace("oai:arXiv.org:", "")
					else:
						arxiv = ""
					tmpDict["arxiv"] = arxiv
				if q["9"] == "SPIRESTeX" or q["9"] == "INSPIRETeX":
					if q["z"]:
						tmpDict["bibkey"] = q["z"]
					elif q["a"]:
						tmpOld.append(q["a"])
				if q["9"] == "ADS":
					if q["a"] is not None:
						tmpDict["ads"] = q["a"]
		except (IndexError, TypeError) as e:
			print(e)
		if tmpDict["bibkey"] is None and len(tmpOld) > 0:
			tmpDict["bibkey"] = tmpOld[0]
			tmpOld = []
		try:
			j, v, y, p, m, x, t, w = get_journal_ref_xml(record)
			tmpDict["journal"] = j[0]
			tmpDict["volume"]  = v[0]
			tmpDict["year"]    = y[0]
			tmpDict["pages"]   = p[0]
			if w[0] is not None:
				conferenceCode = w[0]
			else:
				conferenceCode = None
		except IndexError:
			tmpDict["journal"] = None
			tmpDict["volume"]  = None
			tmpDict["year"]    = None
			tmpDict["pages"]   = None
			conferenceCode = None
		try:
			firstdate = record["269"]
			if firstdate is not None:
				firstdate = firstdate["c"]
			else:
				firstdate = record["961"]
				if firstdate is not None:
					firstdate = firstdate["x"]
			tmpDict["firstdate"] = firstdate
		except TypeError:
			tmpDict["firstdate"] = None
		try:
			tmpDict["pubdate"] = record["260"]["c"]
		except TypeError:
			tmpDict["pubdate"] = None
		try:
			tmpDict["author"] = record["100"]["a"]
		except TypeError:
			tmpDict["author"] = ""
		try:
			addAuthors = 0
			for r in record.get_fields("700"):
				addAuthors += 1
				if addAuthors > pbConfig.params["maxAuthorSave"]:
					tmpDict["author"] += " and others"
					break
				tmpDict["author"] += " and %s"%r["a"]
		except:
			pass
		try:
			tmpDict["collaboration"] = record["710"]["g"]
		except TypeError:
			tmpDict["collaboration"] = None
		try:
			for q in record.get_fields('037'):
				if "arXiv" in q["a"]:
					tmpDict["primaryclass"] = q["c"]
					tmpDict["archiveprefix"] = q["9"]
					tmpDict["eprint"] = q["a"].lower().replace("arxiv:", "")
				else:
					tmpDict["reportnumber"] = q["a"]
		except:
			tmpDict["primaryclass"] = None
			tmpDict["archiveprefix"] = None
			tmpDict["eprint"] = None
			tmpDict["reportnumber"] = None
		try:
			tmpDict["title"] = record["245"]["a"]
		except TypeError:
			tmpDict["title"] = None
		try:
			tmpDict["isbn"] = record["020"]["a"]
		except TypeError:
			tmpDict["isbn"] = None
		if conferenceCode is not None and readConferenceTitle:
			url = "http://inspirehep.net/search?p=773__w%%3A%s+or+773__w%%3A%s+and+980__a%%3AProceedings&of=xe"%(conferenceCode, conferenceCode.replace("-", "%2F"))
			text = parse_accents_str(self.textFromUrl(url))
			title = re.compile('<title>(.*)</title>', re.MULTILINE)
			try:
				tmpDict["booktitle"] = [m.group(1) for m in title.finditer(text)][0]
			except IndexError:
				tmpDict["booktitle"] = None
		if tmpDict["isbn"] is not None:
			tmpDict["ENTRYTYPE"] = "book"
		else:
			try:
				collections = [r["a"].lower() for r in record.get_fields("980")]
			except:
				collections = []
			if "conferencepaper" in collections or conferenceCode is not None:
				tmpDict["ENTRYTYPE"] = "inproceedings"
			elif "thesis" in collections:
				tmpDict["ENTRYTYPE"] = "phdthesis"
				try:
					tmpDict["school"] = record["502"]["c"]
					tmpDict["year"] = record["502"]["d"]
				except:
					pass
			else:
				tmpDict["ENTRYTYPE"] = "article"
		tmpDict["oldkeys"] = ",".join(tmpOld)
		for k in tmpDict.keys():
			try:
				tmpDict[k] = parse_accents_str(tmpDict[k])
			except:
				pass
		bibtexDict = {"ENTRYTYPE": tmpDict["ENTRYTYPE"], "ID": tmpDict["bibkey"]}
		for k in self.bibtexFields:
			if k in tmpDict.keys() and tmpDict[k] is not None and tmpDict[k] is not "":
				bibtexDict[k] = tmpDict[k]
		try:
			if bibtexDict["arxiv"] == bibtexDict["eprint"] and bibtexDict["eprint"] is not None:
				del bibtexDict["arxiv"]
		except:
			pass
		db = bibtexparser.bibdatabase.BibDatabase()
		db.entries = [bibtexDict]
		tmpDict["bibtex"] = pbWriter.write(db)
		return tmpDict
	
	def retrieveOAIData(self, inspireID, bibtex = None, verbose = 0, readConferenceTitle = False):
		"""
		Get the marcxml entry for a given record

		Parameters:
			inspireID: the INSPIRE-HEP identifier (a number) of the desired entry
			bibtex (default None): whether the bibtex should be included in the output dictionary
			verbose (default 0): increase the output level
			readConferenceTitle (boolean, default False): try to read the conference title if dealing with a proceeding

		Output:
			the dictionary containing the bibtex information
		"""
		try:
			record = self.oai.getRecord(metadataPrefix = 'marcxml', identifier = "oai:inspirehep.net:" + inspireID)
		except (URLError, ErrorBase, IncompleteRead):
			pBErrorManager("[oai] ERROR: impossible to get marcxml for entry %s"%inspireID, traceback)
			return False
		nhand = 0
		if verbose > 0:
			print("[oai] reading data --- " + time.strftime("%c"))
		try:
			if record[1] is None:
				raise ValueError("[oai] Empty record!")
			res = self.readRecord(record[1], readConferenceTitle = readConferenceTitle)
			res["id"] = inspireID
			if bibtex is not None and res["pages"] is not None:
				self.updateBibtex(res, bibtex)
			if verbose > 0:
				print("[oai] done.")
			return res
		except Exception:
			pBErrorManager("[oai] ERROR: impossible to read marcxml for entry %s"%inspireID, traceback)
			return False

	def updateBibtex(self, res, bibtex):
		"""use OAI data to update the (existing) bibtex information of an entry"""
		try:
			element = bibtexparser.loads(bibtex).entries[0]
		except:
			pBErrorManager("[inspireoai] invalid bibtex!\n%s"%bibtex)
			return bibtex
		try:
			res["journal"] = res["journal"].replace(".", ". ")
		except AttributeError:
			pBErrorManager("[DB] 'journal' from OAI is missing or not a string (recid:%s)"%res["id"])
			return bibtex
		try:
			for k in ["doi", "volume", "pages", "year", "journal"]:
				if res[k] != "" and res[k] is not None:
					element[k] = res[k]
		except KeyError:
			pBErrorManager("[DB] something from OAI is missing (recid:%s)"%res["id"])
			return bibtex
		db = BibDatabase()
		db.entries = [element]
		return pbWriter.write(db)

	def retrieveOAIUpdates(self, date1, date2):
		"""
		Harvest the OAI API to get all the updates and new occurrences between two dates

		Parameters:
			date1, date2: dates that define the time interval to be searched

		Output:
			a list of dictionaries containing the bibtex information
		"""
		recs = self.oai.listRecords(metadataPrefix = 'marcxml', from_ = date1, until = date2, set = "INSPIRE:HEP")
		nhand = 0
		print("\n[oai] STARTING OAI harvester --- " + time.strftime("%c") + "\n\n")
		foundObjects = []
		for count, rec in enumerate(recs):
			id = rec[0].identifier()
			if count % 500 == 0:
				print("[oai] Processed %d elements"%count)
			record = rec[1] # Get pyMARC representation
			if not record:
				continue
			try:
				tmpDict = self.readRecord(record)
				id_ = id.replace("oai:inspirehep.net:", "")
				tmpDict["id"] = id_
				foundObjects.append(tmpDict)
			except Exception as e:
				print(count, id)
				print(e)
				print(traceback.format_exc())
		print("[oai] Processed %d elements"%count)
		print("[oai] END --- " + time.strftime("%c") + "\n\n")
		return foundObjects
