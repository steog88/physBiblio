"""
Module that manages the actions on the database (and few more).

This file is part of the PhysBiblio package.
"""
import sqlite3
from sqlite3 import OperationalError, ProgrammingError, DatabaseError
import os, re, traceback, datetime
import ast
import bibtexparser
import six.moves
from pyparsing import ParseException

try:
	from physbiblio.config import pbConfig
	from physbiblio.bibtexwriter import pbWriter
	from physbiblio.errors import pBErrorManager
	import physbiblio.firstOpen as pbfo
	from physbiblio.webimport.webInterf import physBiblioWeb
	import physbiblio.tablesDef
	from physbiblio.parse_accents import *
except ImportError:
    print("Could not find physbiblio and its contents: configure your PYTHONPATH!")

encoding_default = 'iso-8859-15'
parser = bibtexparser.bparser.BibTexParser()
parser.encoding = encoding_default
parser.customization = parse_accents_record
parser.alt_dict = {}

class physbiblioDB():
	"""
	Contains most of the basic functions on the database.
	Will be subclassed to do everything else.
	"""
	def __init__(self, dbname = pbConfig.params['mainDatabaseName'], noOpen = False):
		"""
		Initialize database class (column names, descriptions) and opens the database.

		Parameters:
			dbname: the name of the database to be opened
		"""
		#structure of the tables
		self.tableFields = physbiblio.tablesDef.tableFields
		self.descriptions = physbiblio.tablesDef.fieldsDescriptions
		#names of the columns
		self.tableCols = {}
		for q in self.tableFields.keys():
			self.tableCols[q] = [ a[0] for a in self.tableFields[q] ]

		self.dbChanged = False
		self.conn = None
		self.curs = None
		self.dbname = dbname
		db_is_new = not os.path.exists(self.dbname)

		if not noOpen:
			self.openDB()
			if db_is_new:
				print("-------New database. Creating tables!\n\n")
				pbfo.createTables(self)

		# self.cursExec("ALTER TABLE entries ADD COLUMN abstract TEXT")

		self.lastFetched = None
		self.catsHier = None

		self.loadSubClasses()


	def openDB(self):
		"""
		Open the database and creates the self.conn (connection) and self.curs (cursor) objects.

		Output:
			True if successfull
		"""
		print("[DB] Opening database: %s"%self.dbname)
		self.conn = sqlite3.connect(self.dbname, check_same_thread=False)
		self.conn.row_factory = sqlite3.Row
		self.curs = self.conn.cursor()
		return True

	def reOpenDB(self, newDB = None):
		"""
		Close the currently open database and open a new one (the same if newDB is None).

		Parameters:
			newDB: None (default) or the name of the new database

		Output:
			True if successfull
		"""
		if newDB is not None:
			self.closeDB()
			del self.conn
			del self.curs
			self.dbname = newDB
			db_is_new = not os.path.exists(self.dbname)
			self.openDB()
			if db_is_new:
				print("-------New database. Creating tables!\n\n")
				pbfo.createTables(self)

			self.lastFetched = None
			self.catsHier = None
			self.loadSubClasses()
		else:
			self.closeDB()
			self.openDB()
			self.lastFetched = None
			self.catsHier = None
			self.loadSubClasses()
		return True

	def closeDB(self):
		"""
		Close the database.
		"""
		print("[DB] Closing database...")
		self.conn.close()
		return True

	def checkUncommitted(self):
		"""
		Check if there are uncommitted changes.

		Output:
			True/False
		"""
		#return self.conn.in_transaction() #works only with sqlite > 3.2...
		return self.dbChanged

	def commit(self, verbose = True):
		"""
		Commit the changes.

		Output:
			True if successfull, False if an exception occurred
		"""
		try:
			self.conn.commit()
			self.dbChanged = False
			if verbose:
				print("[DB] saved.")
			return True
		except Exception:
			pBErrorManager("[DB] Impossible to commit!", traceback)
			return False

	def undo(self, verbose = True):
		"""
		Undo the uncommitted changes and roll back to the last commit.

		Output:
			True if successfull, False if an exception occurred
		"""
		try:
			self.conn.rollback()
			self.dbChanged = False
			if verbose:
				print("[DB] rolled back to last commit.")
			return True
		except Exception:
			pBErrorManager("[DB] Impossible to rollback!", traceback)
			return False
		
	def connExec(self, query, data = None):
		"""
		Execute connection.

		Parameters:
			query (string): the query to be executed
			data (dictionary or list): the values of the parameters in the query

		Output:
			True if successfull, False if an exception occurred
		"""
		try:
			if data:
				self.conn.execute(query,data)
			else:
				self.conn.execute(query)
		except (OperationalError, ProgrammingError, DatabaseError) as err:
			pBErrorManager('[connExec] ERROR: %s'%err, traceback)
			return False
		else:
			self.dbChanged = True
			return True

	def cursExec(self,query,data=None):
		"""
		Execute cursor.

		Parameters:
			query (string): the query to be executed
			data (dictionary or list): the values of the parameters in the query

		Output:
			True if successfull, False if an exception occurred
		"""
		try:
			if data:
				self.curs.execute(query,data)
			else:
				self.curs.execute(query)
		except Exception as err:
			pBErrorManager('[cursExec] ERROR: %s\nThe query was: "%s"\n and the parameters: %s'%(err, query, data), traceback)
			return False
		else:
			return True
	
	def loadSubClasses(self):
		"""
		Load the subclasses that manage the content in the various tables in the database.

		Output:
			True if successfull
		"""
		try:
			del self.bibs
			del self.cats
			del self.exps
			del self.bibExp
			del self.catBib
			del self.catExp
			del self.utils
		except:
			pass
		self.utils = utilities(self)
		self.bibs = entries(self)
		self.cats = categories(self)
		self.exps = experiments(self)
		self.bibExp = entryExps(self)
		self.catBib = catsEntries(self)
		self.catExp = catsExps(self)
		return True

class physbiblioDBSub():
	"""
	Uses physbiblioDB instance 'self.mainDB = parent' to act on the database.
	All the subcategories of physbiblioDB are defined starting from this one.
	"""
	def __init__(self, parent):
		"""
		Initialize DB class, connecting to the main physbiblioDB instance (parent).
		"""
		self.mainDB = parent
		#structure of the tables
		self.tableFields = physbiblio.tablesDef.tableFields
		#names of the columns
		self.tableCols = {}
		for q in self.tableFields.keys():
			self.tableCols[q] = [ a[0] for a in self.tableFields[q] ]

		self.conn = self.mainDB.conn
		self.curs = self.mainDB.curs
		self.dbname = self.mainDB.dbname

		self.lastFetched = None
		self.catsHier = None

	def literal_eval(self, string):
		try:
			if "[" in string and "]" in string:
				return ast.literal_eval(string.strip())
			elif "," in string:
				return ast.literal_eval("[%s]"%string.strip())
			else:
				return string.strip()
		except SyntaxError:
			pBErrorManager("[DB] error in literal_eval with string '%s'"%string)
			return None

	def closeDB(self):
		"""
		Close the database (using physbiblioDB.close)
		"""
		self.mainDB.closeDB()

	def commit(self):
		"""
		Commit the changes (using physbiblioDB.commit)
		"""
		self.mainDB.commit()

	def connExec(self,query,data=None):
		"""
		Execute connection (see physbiblioDB.connExec)
		"""
		return self.mainDB.connExec(query, data = data)

	def cursExec(self,query,data=None):
		"""
		Execute cursor (see physbiblioDB.cursExec)
		"""
		return self.mainDB.cursExec(query, data = data)

class categories(physbiblioDBSub):
	"""
	Subclass that manages the functions for the categories.
	"""
	def insert(self, data):
		"""
		Insert a new category

		Parameters:
			data: the dictionary containing the category field values

		Output:
			False if another category with the same name and parent is present, the output of self.connExec otherwise
		"""
		try:
			self.cursExec("""
				select * from categories where name=? and parentCat=?
				""", (data["name"], data["parentCat"]))
		except KeyError:
			pBErrorManager("[DB] missing field when inserting category", traceback)
			return False
		if self.curs.fetchall():
			print("An entry with the same name is already present in the same category!")
			return False
		else:
			return self.connExec("""
				INSERT into categories (name, description, parentCat, comments, ord)
					values (:name, :description, :parentCat, :comments, :ord)
				""", data)

	def update(self, data, idCat):
		"""
		Update all the fields of an existing category

		Parameters:
			data: the dictionary containing the category field values
			idCat: the id of the category in the database

		Output:
			the output of self.connExec
		"""
		data["idCat"] = idCat
		query = "replace into categories (" +\
					", ".join(data.keys()) + ") values (:" + \
					", :".join(data.keys()) + ")\n"
		return self.connExec(query, data)

	def updateField(self, idCat, field, value):
		"""
		Update a field of an existing category

		Parameters:
			idCat: the id of the category in the database
			field: the name of the field
			value: the value of the field

		Output:
			False if the field or the value is not valid, the output of self.connExec otherwise
		"""
		print("[DB] updating '%s' for entry '%s'"%(field, idCat))
		if field in self.tableCols["categories"] and field is not "idCat" \
				and value is not "" and value is not None:
			query = "update categories set " + field + "=:field where idCat=:idCat\n"
			return self.connExec(query, {"field": value, "idCat": idCat})
		else:
			return False

	def delete(self, idCat, name = None):
		"""
		Delete a category, its subcategories and all their connections.
		Cannot delete categories with id ==0 or ==1 (Main and Tags, the default categories).

		Parameters:
			idCat: the id of the category (or a list)
			name (optional): if id is smaller than 2, the name is used instead.

		Output:
			False if id ==0 or ==1, True otherwise
		"""
		if type(idCat) is list:
			for c in idCat:
				self.delete(c)
		else:
			if idCat < 2 and name:
				result = self.extractCatByName(name)
				idCat = result[0]["idCat"]
			if idCat < 2:
				print("[DB] Error: should not delete the category with id: %d%s."%(idCat, " (name: %s)"%name if name else ""))
				return False
			print("[DB] using idCat=%d"%idCat)
			print("[DB] looking for child categories")
			for row in self.getChild(idCat):
				self.delete(row["idCat"])
			self.cursExec("""
			delete from categories where idCat=?
			""", (idCat, ))
			self.cursExec("""
			delete from expCats where idCat=?
			""", (idCat, ))
			self.cursExec("""
			delete from entryCats where idCat=?
			""", (idCat, ))
			return True

	def getAll(self):
		"""
		Get all the categories

		Output:
			the list of `sqlite3.Row` objects with all the categories in the database
		"""
		self.cursExec("""
		select * from categories
		""")
		return self.curs.fetchall()

	def getByID(self, idCat):
		"""
		Get a category given its id

		Parameters:
			idCat: the id of the required category

		Output:
			the list (len = 1) of `sqlite3.Row` objects with all the matching categories
		"""
		self.cursExec("""
			select * from categories where idCat=?
			""", (idCat, ))
		return self.curs.fetchall()

	def getDictByID(self, idCat):
		"""
		Get a category given its id, returns a standard dictionary

		Parameters:
			idCat: the id of the required category

		Output:
			a dictionary with all field values for the required category
		"""
		self.cursExec("""
			select * from categories where idCat=?
			""", (idCat, ))
		try:
			entry = self.curs.fetchall()[0]
			catDict = {}
			for i,k in enumerate(self.tableCols["categories"]):
				catDict[k] = entry[i]
		except:
			print("[DB] Error in extracting category by idCat")
			catDict = None
		return catDict

	def getByName(self,name):
		"""
		Get categories given the name

		Parameters:
			name: the name of the required category

		Output:
			the list of `sqlite3.Row` objects with all the matching categories
		"""
		self.cursExec("""
		select * from categories where name=?
		""", (name,))
		return self.curs.fetchall()

	def getChild(self, parent):
		"""
		Get the subcategories that have as a parent the given one

		Parameters:
			parent: the id of the parent category

		Output:
			the list of `sqlite3.Row` objects with all the matching categories
		"""
		self.cursExec("""
		select cats1.*
		from categories as cats
		join categories as cats1 on cats.idCat=cats1.parentCat
		where cats.idCat=?
		""", (parent, ))
		return self.curs.fetchall()

	def getParent(self, child):
		"""get parent directory of a given one"""
		"""
		Get the category that is the parent of the given one

		Parameters:
			child: the id of the child category

		Output:
			the list (len = 1) of `sqlite3.Row` objects with all the matching categories
		"""
		self.cursExec("""
		select cats.*
		from categories as cats
		join categories as cats1 on cats.idCat=cats1.parentCat
		where cats1.idCat=?
		""", (child, ))
		return self.curs.fetchall()

	def getHier(self, cats = None, startFrom = 0, replace = True):
		"""
		Builds a tree with the parent/child structure of the categories

		Parameters:
			cats: the list of `sqlite3.Row` objects of the categories to be considered or None (in this case the list is taken from self.getAll)
			startFrom (default 0, the main category): the parent category starting from which the tree should be built
			replace (boolean, default True): if True, rebuild the structure again, if False return the previously calculated one

		Output:
			the dictionary defining the tree of subcategories of the initial one
		"""
		if self.catsHier is not None and not replace:
			return self.catsHier
		if cats is None:
			cats = self.getAll()
		def addSubCats(idC):
			"""
			The subfunction that recursively builds the list of child categories

			Parameters:
				idC: the id of the parent category
			"""
			tmp = {}
			for c in [ a for a in cats if a["parentCat"] == idC and a["idCat"] != 0 ]:
				tmp[c["idCat"]] = addSubCats(c["idCat"])
			return tmp
		catsHier = {}
		catsHier[startFrom] = addSubCats(startFrom)
		self.catsHier = catsHier
		return catsHier

	def printHier(self, startFrom = 0, sp = 5*" ", withDesc = False, depth = 10, replace = False):
		"""
		Print categories and subcategories in a tree-like form

		Parameters:
			startFrom (default 0, the main category): the starting parent category
			sp (default 5*" "): the spacing to use while indenting inner levels
			withDesc (boolean, default False): if True, print also the category description
			depth (default 10): the maximum number of levels to print
			replace (boolean, default True): if True, rebuild the structure again, if False return the previously calculated one
		"""
		cats = self.getAll()
		if depth < 2:
			print("[DB] invalid depth in printCatHier (must be greater than 2)")
			depth = 10
		catsHier = self.getHier(cats, startFrom=startFrom, replace = replace)
		def printSubGroup(tree, indent = "", startDepth = 0):
			"""
			The subfunction that recursively builds the list of child categories

			Parameters:
				tree (dictionary): the tree structure to use
				indent (default ""): the indentation level from which to start
				startDepth (default 0): the depth from which to start
			"""
			if startDepth <= depth:
				for l in cats_alphabetical(tree.keys(), self.mainDB):
					print(indent + catString(l, self.mainDB, withDesc = withDesc))
					printSubGroup(tree[l], (startDepth + 1) * sp, startDepth + 1)
		printSubGroup(catsHier)

	def getByEntry(self, key):
		"""
		Find all the categories associated to a given entry

		Parameters:
			key: the bibtex key of the entry

		Output:
			the list of `sqlite3.Row` objects with all the matching categories
		"""
		self.cursExec("""
				select * from categories
				join entryCats on categories.idCat=entryCats.idCat
				where entryCats.bibkey=?
				""", (key,))
		return self.curs.fetchall()

	def getByExp(self, idExp):
		"""
		Find all the categories associated to a given experiment

		Parameters:
			idExp: the id of the experiment

		Output:
			the list of `sqlite3.Row` objects with all the matching categories
		"""
		self.cursExec("""
				select * from categories
				join expCats on categories.idCat=expCats.idCat
				where expCats.idExp=?
				""", (idExp,))
		return self.curs.fetchall()

class catsEntries(physbiblioDBSub):
	"""
	Functions for connecting categories and entries
	"""
	def getOne(self, idCat, key):
		"""
		Find connections between a category and an entry

		Parameters:
			idCat: the category id
			key: the bibtex key

		Output:
			the list of `sqlite3.Row` objects with all the matching connections
		"""
		self.cursExec("""
				select * from entryCats where bibkey=:bibkey and idCat=:idCat
				""",
				{"bibkey": key, "idCat": idCat})
		return self.curs.fetchall()

	def getAll(self):
		"""
		Get all the connections

		Output:
			the list of `sqlite3.Row` objects
		"""
		self.cursExec("""
				select * from entryCats
				""")
		return self.curs.fetchall()

	def insert(self, idCat, key):
		"""
		Create a new connection between a category and a bibtex entry

		Parameters:
			idCat: the category id (or a list)
			key: the bibtex key (or a list)

		Output:
			False if the connection is already present, the output of self.connExec otherwise
		"""
		if type(idCat) is list:
			for q in idCat:
				self.insert(q, key)
		elif type(key) is list:
			for q in key:
				self.insert(idCat, q)
		else:
			if len(self.getOne(idCat, key))==0:
				return self.connExec("""
						INSERT into entryCats (bibkey, idCat) values (:bibkey, :idCat)
						""",
						{"bibkey": key, "idCat": idCat})
			else:
				print("[DB] entryCat already present: (%d, %s)"%(idCat, key))
				return False

	def delete(self, idCat, key):
		"""
		Delete a connection between a category and a bibtex entry

		Parameters:
			idCat: the category id (or a list)
			key: the bibtex key (or a list)

		Output:
			the output of self.connExec
		"""
		if type(idCat) is list:
			for q in idCat:
				self.delete(q, key)
		elif type(key) is list:
			for q in key:
				self.delete(idCat, q)
		else:
			return self.connExec("""
					delete from entryCats where bibkey=:bibkey and idCat=:idCat
					""",
					{"bibkey": key, "idCat": idCat})

	def updateBibkey(self, new, old):
		"""
		Update the connections affected by a bibkey change

		Parameters:
			new: the new bibtex key
			old: the old bibtex key

		Output:
			the output of self.connExec
		"""
		print("[DB] updating entryCats for bibkey change, from '%s' to '%s'"%(old, new))
		query = "update entryCats set bibkey=:new where bibkey=:old\n"
		return self.connExec(query, {"new": new, "old": old})

	def askCats(self, keys):
		"""
		Loop over the given bibtex keys and ask for the categories to be associated with them

		Parameters:
			keys: a single key or a list of bibtex keys
		"""
		if type(keys) is not list:
			keys = [keys]
		for k in keys:
			string = six.moves.input("categories for '%s': "%k)
			try:
				cats = self.literal_eval(string)
				self.insert(cats, k)
			except:
				print("[DB] something failed in reading your input '%s'"%string)

	def askKeys(self, cats):
		"""
		Loop over the given categories and ask for the bibtex keys to be associated with them

		Parameters:
			cats: a single id or a list of categories
		"""
		if type(cats) is not list:
			cats = [cats]
		for c in cats:
			string = six.moves.input("entries for '%d': "%c)
			try:
				keys = self.literal_eval(string)
				self.insert(c, keys)
			except:
				print("[DB] something failed in reading your input '%s'"%string)

class catsExps(physbiblioDBSub):
	"""
	Functions for connecting categories and experiments
	"""
	def getOne(self, idCat, idExp):
		"""
		Find connections between a category and an experiment

		Parameters:
			idCat: the category id
			idExp: the experiment id

		Output:
			the list of `sqlite3.Row` objects with all the matching connections
		"""
		self.cursExec("""
				select * from expCats where idExp=:idExp and idCat=:idCat
				""",
				{"idExp": idExp, "idCat": idCat})
		return self.curs.fetchall()

	def getAll(self):
		"""
		Get all the connections

		Output:
			the list of `sqlite3.Row` objects
		"""
		self.cursExec("""
				select * from expCats
				""")
		return self.curs.fetchall()

	def insert(self, idCat, idExp):
		"""
		Create a new connection between a category and an experiment

		Parameters:
			idCat: the category id (or a list)
			idExp: the experiment id (or a list)

		Output:
			False if the connection is already present, the output of self.connExec otherwise
		"""
		if type(idCat) is list:
			for q in idCat:
				self.insert(q, idExp)
		elif type(idExp) is list:
			for q in idExp:
				self.insert(idCat, q)
		else:
			if len(self.getOne(idCat, idExp))==0:
				return self.connExec("""
						INSERT into expCats (idExp, idCat) values (:idExp, :idCat)
						""",
						{"idExp": idExp, "idCat": idCat})
			else:
				print("[DB] expCat already present: (%d, %d)"%(idCat, idExp))
				return False

	def delete(self, idCat, idExp):
		"""
		Delete a connection between a category and an experiment

		Parameters:
			idCat: the category id (or a list)
			idExp: the experiment id (or a list)

		Output:
			the output of self.connExec
		"""
		if type(idCat) is list:
			for q in idCat:
				self.delete(q, idExp)
		elif type(idExp) is list:
			for q in idExp:
				self.delete(idCat, q)
		else:
			return self.connExec("""
					delete from expCats where idExp=:idExp and idCat=:idCat
					""",
					{"idExp": idExp, "idCat": idCat})

	def askCats(self, exps):
		"""
		Loop over the given experiment ids and ask for the categories to be associated with them

		Parameters:
			exps: a single id or a list of experiment ids
		"""
		if type(exps) is not list:
			exps = [exps]
		for e in exps:
			string = six.moves.input("categories for '%d': "%e)
			try:
				cats = self.literal_eval(string)
				self.insert(cats, e)
			except:
				print("[DB] something failed in reading your input '%s'"%string)

	def askExps(self, cats):
		"""
		Loop over the given category ids and ask for the experiments to be associated with them

		Parameters:
			cats: a single id or a list of category ids
		"""
		if type(cats) is not list:
			cats = [cats]
		for c in cats:
			string = six.moves.input("experiments for '%d': "%c)
			try:
				exps = self.literal_eval(string)
				self.insert(c, exps)
			except:
				print("[DB] something failed in reading your input '%s'"%string)

class entryExps(physbiblioDBSub):
	"""
	Functions for connecting entries and experiments
	"""
	def getOne(self, key, idExp):
		"""
		Find connections between an entry and an experiment

		Parameters:
			key: the bibtex key
			idExp: the experiment id

		Output:
			the list of `sqlite3.Row` objects with all the matching connections
		"""
		self.cursExec("""
				select * from entryExps where idExp=:idExp and bibkey=:bibkey
				""",
				{"idExp": idExp, "bibkey": key})
		return self.curs.fetchall()

	def getAll(self):
		"""
		Get all the connections

		Output:
			the list of `sqlite3.Row` objects
		"""
		self.cursExec("""
				select * from entryExps
				""")
		return self.curs.fetchall()

	def insert(self, key, idExp):
		"""
		Create a new connection between a bibtex entry and an experiment

		Parameters:
			key: the bibtex key (or a list)
			idExp: the experiment id (or a list)

		Output:
			False if the connection is already present, the output of self.connExec otherwise
		"""
		if type(key) is list:
			for q in key:
				self.insert(q, idExp)
		elif type(idExp) is list:
			for q in idExp:
				self.insert(key, q)
		else:
			if len(self.getOne(key, idExp))==0:
				if self.connExec("""
						INSERT into entryExps (idExp, bibkey) values (:idExp, :bibkey)
						""",
						{"idExp": idExp, "bibkey": key}):
					for c in self.mainDB.cats.getByExp(idExp):
						self.mainDB.catBib.insert(c["idCat"],key)
					return True
			else:
				print("[DB] entryExp already present: (%s, %d)"%(key, idExp))
				return False

	def delete(self, key, idExp):
		"""
		Delete a connection between a bibtex entry and an experiment

		Parameters:
			key: the bibtex key (or a list)
			idExp: the experiment id (or a list)

		Output:
			the output of self.connExec
		"""
		if type(key) is list:
			for q in key:
				self.delete(q, idExp)
		elif type(idExp) is list:
			for q in idExp:
				self.delete(key, q)
		else:
			return self.connExec("""
					delete from entryExps where idExp=:idExp and bibkey=:bibkey
					""",
					{"idExp": idExp, "bibkey": key})

	def updateBibkey(self, new, old):
		"""
		Update the connections affected by a bibkey change

		Parameters:
			new: the new bibtex key
			old: the old bibtex key

		Output:
			the output of self.connExec
		"""
		print("[DB] updating entryCats for bibkey change, from '%s' to '%s'"%(old, new))
		query = "update entryExps set bibkey=:new where bibkey=:old\n"
		return self.connExec(query, {"new": new, "old": old})

	def askExps(self, keys):
		"""
		Loop over the given bibtex keys and ask for the experiments to be associated with them

		Parameters:
			keys: a single key or a list of bibtex keys
		"""
		if type(keys) is not list:
			keys = [keys]
		for k in keys:
			string = six.moves.input("experiments for '%s': "%k)
			try:
				exps = self.literal_eval(string)
				self.insert(k, exps)
			except:
				print("[DB] something failed in reading your input '%s'"%string)

	def askKeys(self, exps):
		"""
		Loop over the given experiment ids and ask for the bibtexs to be associated with them

		Parameters:
			exps: a single id or a list of experiment ids
		"""
		if type(exps) is not list:
			exps = [exps]
		for e in exps:
			string = six.moves.input("entries for '%d': "%e)
			try:
				keys = self.literal_eval(string)
				self.insert(keys, e)
			except:
				print("[DB] something failed in reading your input '%s'"%string)

class experiments(physbiblioDBSub):
	"""
	Functions to manage the experiments
	"""
	def insert(self, data):
		"""
		Insert a new experiment

		Parameters:
			data: the dictionary with the experiment fields

		Output:
			the output of self.connExec
		"""
		return self.connExec("""
				INSERT into experiments (name, comments, homepage, inspire)
					values (:name, :comments, :homepage, :inspire)
				""", data)

	def update(self, data, idExp):
		"""
		Update an existing experiment

		Parameters:
			data: the dictionary with the experiment fields
			idExp: the experiment id

		Output:
			the output of self.connExec
		"""
		data["idExp"] = idExp
		query = "replace into experiments (" +\
					", ".join(data.keys()) + ") values (:" + \
					", :".join(data.keys()) + ")\n"
		return self.connExec(query, data)

	def updateField(self, idExp, field, value):
		"""
		Update an existing experiment

		Parameters:
			idExp: the experiment id
			field: the field name
			value: the new field value

		Output:
			False if the field or the content is invalid, the output of self.connExec otherwise
		"""
		print("[DB] updating '%s' for entry '%s'"%(field, idExp))
		if field in self.tableCols["experiments"] and field is not "idExp" \
				and value is not "" and value is not None:
			query = "update experiments set " + field + "=:field where idExp=:idExp\n"
			return self.connExec(query, {"field": value, "idExp": idExp})
		else:
			return False

	def delete(self, idExp):
		"""
		Delete an experiment and all its connections

		Parameters:
			idExp: the experiment ID
		"""
		if type(idExp) is list:
			for e in idExp:
				self.delete(e)
		else:
			print("[DB] using idExp=%d"%idExp)
			self.cursExec("""
			delete from experiments where idExp=?
			""", (idExp, ))
			self.cursExec("""
			delete from expCats where idExp=?
			""", (idExp, ))
			self.cursExec("""
			delete from entryExps where idExp=?
			""", (idExp, ))

	def getAll(self, orderBy = "name", order = "ASC"):
		"""
		Get all the experiments

		Parameters:
			orderBy: the field used to order the output
			order: "ASC" or "DESC"

		Output:
			the list of `sqlite3.Row` objects with all the experiments in the database
		"""
		self.cursExec("""
			select * from experiments
			order by %s %s
			"""%(orderBy, order))
		return self.curs.fetchall()

	def getByID(self, idExp):
		"""
		Get experiment matching the given id

		Parameters:
			idExp: the experiment id

		Output:
			the list (len = 1) of `sqlite3.Row` objects with all the matching experiments
		"""
		self.cursExec("""
			select * from experiments where idExp=?
			""", (idExp, ))
		return self.curs.fetchall()

	def getDictByID(self, idExp):
		"""
		Get experiment matching the given id, returns a standard dictionary

		Parameters:
			idExp: the experiment id

		Output:
			the list (len = 1) of `sqlite3.Row` objects with all the matching experiments
		"""
		self.cursExec("""
			select * from experiments where idExp=?
			""", (idExp, ))
		try:
			entry = self.curs.fetchall()[0]
			expDict = {}
			for i,k in enumerate(self.tableCols["experiments"]):
				expDict[k] = entry[i]
		except:
			print("[DB] Error in extracting experiment by idExp")
			expDict = None
		return expDict

	def getByName(self, name):
		"""
		Get all the experiments matching a given name

		Parameters:
			name: the experiment name to be matched

		Output:
			the list of `sqlite3.Row` objects with all the matching experiments
		"""
		self.cursExec("""
			select * from experiments where name=?
			""", (name, ))
		return self.curs.fetchall()

	def filterAll(self, string):
		"""
		Get all the experiments matching a given string

		Parameters:
			string: the string to be matched

		Output:
			the list of `sqlite3.Row` objects with all the matching experiments
		"""
		string = "%" + string + "%"
		self.cursExec("""
			select * from experiments where name LIKE ? OR comments LIKE ? OR homepage LIKE ? OR inspire LIKE ?
			""", (string, string, string, string))
		return self.curs.fetchall()

	def to_str(self, q):
		"""
		Convert the experiment row in a string

		Parameters:
			q: the experiment record (sqlite3.Row or dict)
		"""
		return "%3d: %-20s [%-40s] [%s]"%(q["idExp"], q["name"], q["homepage"], q["inspire"])

	def printInCats(self, startFrom = 0, sp = 5 * " ", withDesc = False):
		"""
		Prints the experiments under the corresponding categories

		Parameters:
			startFrom (int): where to start from
			sp (string): the spacing
			withDesc (boolean, default False): whether to print the description
		"""
		cats = self.mainDB.cats.getAll()
		exps = self.getAll()
		catsHier = self.mainDB.cats.getHier(cats, startFrom = startFrom)
		showCat = {}
		for c in cats:
			showCat[c["idCat"]] = False
		def expString(idExp):
			"""
			Get the string describing the experiment

			Parameters:
				idExp: the experiment id

			Output:
				the string
			"""
			exp = [ e for e in exps if e["idExp"] == idExp ][0]
			if withDesc:
				return sp + '-> %s (%d) - %s'%(exp['name'], exp['idExp'], exp['comments'])
			else:
				return sp + '-> %s (%d)'%(exp['name'], exp['idExp'])
		def alphabetExp(listId):
			"""
			Order experiments within a list in alphabetical order

			Parameters:
				listId: the list of experiment ids

			Output:
				the ordered list of id
			"""
			listIn = [ e for e in exps if e["idExp"] in listId ]
			decorated = [ (x["name"], x) for x in listIn ]
			decorated.sort()
			return [ x[1]["idExp"] for x in decorated ]
		expCats = {}
		for (a, idE, idC) in self.mainDB.catExp.getAll():
			if idC not in expCats.keys():
				expCats[idC] = []
				showCat[idC] = True
			expCats[idC].append(idE)
		def printExpCats(ix, lev):
			"""
			Prints the experiments in a given category

			Parameters:
				ix: the category id
				lev: the indentation level
			"""
			try:
				for e in alphabetExp(expCats[ix]):
					print(lev * sp + expString(e))
			except:
				pBErrorManager("[DB] error printing experiments!", traceback)
		for l0 in cats_alphabetical(catsHier.keys(), self.mainDB):
			for l1 in cats_alphabetical(catsHier[l0].keys(), self.mainDB):
				if showCat[l1]:
					showCat[l0] = True
				for l2 in cats_alphabetical(catsHier[l0][l1].keys(), self.mainDB):
					if showCat[l2]:
						showCat[l0] = True
						showCat[l1] = True
					for l3 in cats_alphabetical(catsHier[l0][l1][l2].keys(), self.mainDB):
						if showCat[l3]:
							showCat[l0] = True
							showCat[l1] = True
							showCat[l2] = True
						for l4 in cats_alphabetical(catsHier[l0][l1][l2][l3].keys(), self.mainDB):
							if showCat[l4]:
								showCat[l0] = True
								showCat[l1] = True
								showCat[l2] = True
								showCat[l2] = True
		for l0 in cats_alphabetical(catsHier.keys(), self.mainDB):
			if showCat[l0]:
				print(catString(l0, self.mainDB))
				printExpCats(l0, 1)
			for l1 in cats_alphabetical(catsHier[l0].keys(), self.mainDB):
				if showCat[l1]:
					print(sp + catString(l1, self.mainDB))
					printExpCats(l1, 2)
				for l2 in cats_alphabetical(catsHier[l0][l1].keys(), self.mainDB):
					if showCat[l2]:
						print(2*sp + catString(l2, self.mainDB))
						printExpCats(l2, 3)
					for l3 in cats_alphabetical(catsHier[l0][l1][l2].keys(), self.mainDB):
						if showCat[l3]:
							print(3*sp + catString(l3, self.mainDB))
							printExpCats(l3, 4)
						for l4 in cats_alphabetical(catsHier[l0][l1][l2][l3].keys(), self.mainDB):
							if showCat[l4]:
								print(4*sp + catString(l4, self.mainDB))
								printExpCats(l4, 5)

	def printAll(self, exps = None, orderBy = "name", order = "ASC"):
		"""
		Print all the experiments

		Parameters:
			exps: the experiments (if None it gets all the experiments in the database)
			orderBy: the field to use for ordering the experiments, if they are not given
			order: which order, if exps is not given
		"""
		if exps is None:
			exps = self.getAll(orderBy = orderBy, order = order)
		for q in exps:
			print(self.to_str(q))

	def getByCat(self, idCat):
		"""
		Get all the experiments associated with a given category

		Parameters:
			idCat: the id of the category to be matched

		Output:
			the list of `sqlite3.Row` objects with all the matching experiments
		"""
		query = """
				select * from experiments
				join expCats on experiments.idExp=expCats.idExp
				where expCats.idCat=?
				"""
		self.cursExec(query, (idCat,))
		return self.curs.fetchall()

	def getByEntry(self, key):
		"""
		Get all the experiments matching a given bibtex entry

		Parameters:
			key: the key of the bibtex to be matched

		Output:
			the list of `sqlite3.Row` objects with all the matching experiments
		"""
		self.cursExec("""
				select * from experiments
				join entryExps on experiments.idExp=entryExps.idExp
				where entryExps.bibkey=?
				""", (key, ))
		return self.curs.fetchall()

class entries(physbiblioDBSub):
	"""
	Functions to manage the bibtex entries
	"""
	def __init__(self, parent):
		"""
		Call parent __init__ and create an empty lastFetched & c.
		"""
		physbiblioDBSub.__init__(self, parent)
		self.lastFetched = []
		self.lastQuery = "select * from entries limit 10"
		self.lastVals = ()
		self.lastInserted = []

	def delete(self, key):
		"""
		Delete an entry and all its connections

		Parameters:
			key: the bibtex key (or a list)
		"""
		if type(key) is list:
			for k in key:
				self.delete(k)
		else:
			print("[DB] delete entry, using key = '%s'"%key)
			self.cursExec("""
			delete from entries where bibkey=?
			""", (key,))
			self.cursExec("""
			delete from entryCats where bibkey=?
			""", (key,))
			self.cursExec("""
			delete from entryExps where bibkey=?
			""", (key,))

	def completeFetched(self, fetched_in):
		"""
		Use the database content to add additional fields ("bibtexDict", "published", "author", "title", "journal", "volume", "number", "pages") to the query results.

		Parameters:
			fetched_in: the list of `sqlite3.Row` objects returned by the last query

		Output:
			a dictionary with the original and the new fields
		"""
		fetched_out = []
		for el in fetched_in:
			tmp = {}
			for k in el.keys():
				tmp[k] = el[k]
			try:
				tmp["bibtexDict"] = bibtexparser.loads(el["bibtex"]).entries[0]
			except IndexError:
				tmp["bibtexDict"] = {}
			except ParseException:
				pBErrorManager("[DB] Problem in parsing the following bibtex code:\n%s"%el["bibtex"])
				tmp["bibtexDict"] = {}
			for fi in ["title", "journal", "volume", "number", "pages"]:
				try:
					tmp[fi] = tmp["bibtexDict"][fi]
				except KeyError:
					tmp[fi] = ""
			try:
				tmp["published"] = " ".join([tmp["journal"], tmp["volume"], "(%s)"%tmp["year"], tmp["pages"]])
			except KeyError:
				tmp["published"] = ""
			try:
				author = tmp["bibtexDict"]["author"]
				if author.count("and") > pbConfig.params["maxAuthorNames"] - 1:
					author = author[:author.index("and")] + "et al."
				tmp["author"] = author
			except KeyError:
				tmp["author"] = ""
			fetched_out.append(tmp)
		return fetched_out

	def fetchFromLast(self):
		"""
		Fetch entries using the last saved query

		Output:
			self
		"""
		try:
			if len(self.lastVals) > 0:
				self.cursExec(self.lastQuery, self.lastVals)
			else:
				self.cursExec(self.lastQuery)
		except:
			print("[DB] query failed: %s"%self.lastQuery)
			print(self.lastVals)
		fetched_in = self.curs.fetchall()
		self.lastFetched = self.completeFetched(fetched_in)
		return self

	def fetchFromDict(self, queryDict = {}, catExpOperator = "and", defaultConnection = "and",
			orderBy = "firstdate", orderType = "ASC", limitTo = None, limitOffset = None, saveQuery = True):
		"""
		Fetch entries using a number of criterions

		Parameters:
			queryDict: a dictionary containing mostly dictionaries for the fields used to filter and the criterion for each field. Possible fields:
				"cats" or "exps" > {"operator": the logical connection, "id": the id to match}
				"catExpOperator" > "and" or "or" (see below)
				Each other item should be a dictionary with the following fields:
				{"str": the string to match
				"operator": "like" if the field must only contain the string, "=" for exact match
				"connection" (optional): logical operator}

			catExpOperator: "and" (default) or "or", the logical operator that connects multiple category + experiment searches. May be overwritten by an item in queryDict
			defaultConnection: "and" (default) or "or", the default logical operator for multiple field matches
			orderBy: the name of the field according to which the results are ordered
			orderType: "ASC" (default) or "DESC"
			limitTo (int or None): maximum number of results. If None, do not limit
			limitOffset (int or None): where to start in the ordered list. If None, use 0
			saveQuery (boolean, default True): if True, save the query for future reuse

		Output:
			self
		"""
		def getQueryStr(di):
			return "%%%s%%"%di["str"] if di["operator"] == "like" else di["str"]
		first = True
		vals = ()
		query = """select * from entries """
		prependTab = ""
		jC,wC,vC,jE,wE,vE = ["","","","","",""]
		if "catExpOperator" in queryDict.keys():
			catExpOperator = queryDict["catExpOperator"]
			del queryDict["catExpOperator"]
		def catExpStrings(tp, tabName, fieldName):
			"""
			Returns the string and the data needed to perform a search using categories and/or experiments

			Parameters:
				tp: the field of queryDict to consider
				tabName: the name of the table to consider
				fieldName: the name of the primary key in the considered table

			Output:
				joinStr, whereStr, valsTmp:
				the string containing the `join` structure, the one containing the `where` conditions and a tuple with the values of the fields
			"""
			joinStr = ""
			whereStr = ""
			valsTmp = tuple()
			if type(queryDict[tp]["id"]) is list:
				if queryDict[tp]["operator"] == "or":
					joinStr += " left join %s on entries.bibkey=%s.bibkey"%(tabName, tabName)
					whereStr += "(%s)"%queryDict[tp]["operator"].join(
						[" %s.%s=? "%(tabName,fieldName) for q in queryDict[tp]["id"]])
					valsTmp = tuple(queryDict[tp]["id"])
				elif queryDict[tp]["operator"] == "and":
					joinStr += " ".join(
						[" left join %s %s%d on entries.bibkey=%s%d.bibkey"%(tabName,tabName,iC,tabName,iC) for iC,q in enumerate(queryDict[tp]["id"])])
					whereStr += "(" + " and ".join(
						["%s%d.%s=?"%(tabName, iC, fieldName) for iC,q in enumerate(queryDict[tp]["id"])]) + ")"
					valsTmp = tuple(queryDict[tp]["id"])
				else:
					pBErrorManager("[DB] invalid operator for joining cats!")
					return joinStr, whereStr, valsTmp
			else:
				joinStr += "left join %s on entries.bibkey=%s.bibkey"%(tabName, tabName)
				whereStr += "%s.%s=? "%(tabName, fieldName)
				valsTmp = tuple(str(queryDict["cats"]["id"]))
			return joinStr, whereStr, valsTmp
		if "cats" in queryDict.keys():
			jC,wC,vC = catExpStrings("cats", "entryCats", "idCat")
			del queryDict["cats"]
		else:
			jC, wC, vC = "", "", tuple()
		if "exps" in queryDict.keys():
			jE,wE,vE = catExpStrings("exps", "entryExps", "idExp")
			del queryDict["exps"]
		else:
			jE, wE, vE = "", "", tuple()
		if jC != "" or jE != "":
			prependTab = "entries."
			toJoin = []
			if wC != "":
				toJoin.append(wC)
			if wE != "":
				toJoin.append(wE)
			query += jC + jE + " where " + " %s "%(catExpOperator).join(toJoin)
			vals += vC + vE
			first = False
		for k in queryDict.keys():
			if first:
				query += " where "
				first = False
			else:
				query += " %s "%queryDict[k]["connection"] if "connection" in queryDict[k].keys() else defaultConnection
			s = k.split("#")[0]
			if s in self.tableCols["entries"]:
				query += " %s%s %s ?"%(prependTab, s, queryDict[k]["operator"])
				vals += (getQueryStr(queryDict[k]), )
		query += " order by " + prependTab + orderBy + " " + orderType if orderBy else ""
		if limitTo is not None:
			query += " LIMIT %s"%(str(limitTo))
		if limitOffset is not None:
			if limitTo is None:
				query += " LIMIT 100000"
			query += " OFFSET %s"%(str(limitOffset))
		if saveQuery:
			self.lastQuery = query
			self.lastVals  = vals
		print("[DB] using query:\n%s"%query)
		print(vals)
		try:
			if len(vals) > 0:
				self.cursExec(query, vals)
			else:
				self.cursExec(query)
		except:
			pBErrorManager("[DB] query failed: %s"%query, traceback)
			print(vals)
		fetched_in = self.curs.fetchall()
		self.lastFetched = self.completeFetched(fetched_in)
		return self

	def fetchAll(self, params = None, connection = "and", operator = "=",
			orderBy = "firstdate", orderType = "ASC", limitTo = None, limitOffset = None, saveQuery = True):
		"""
		Fetch entries using a number of criterions. Simpler than self.fetchFromDict.

		Parameters:
			params (a dictionary or None): if a dictionary, it must contain the structure "field": "value"
			connection: "and"/"or", default "and"
			operator: "=" for exact match (default), "like" for containing match
			orderBy: the name of the field according to which the results are ordered
			orderType: "ASC" (default) or "DESC"
			limitTo (int or None): maximum number of results. If None, do not limit
			limitOffset (int or None): where to start in the ordered list. If None, use 0
			saveQuery (boolean, default True): if True, save the query for future reuse

		Output:
			self
		"""
		query = "select * from entries "
		vals = ()
		if connection.strip() != "and" and connection.strip() != "or":
			pBErrorManager("[DB] invalid logical connection operator ('%s') in database operations!\nReverting to default 'and'."%connection)
			connection = "and"
		if operator.strip() != "=" and operator.strip() != "like":
			pBErrorManager("[DB] invalid comparison operator ('%s') in database operations!\nReverting to default '='."%operator)
			operator = "="
		if orderType.strip() != "ASC" and orderType.strip() != "DESC":
			pBErrorManager("[DB] invalid ordering ('%s') in database operations!\nReverting to default 'ASC'."%orderType)
			orderType = "ASC"
		if params and len(params) > 0:
			query += " where "
			first = True
			for k, v in params.items():
				if type(v) is list:
					for v1 in v:
						if first:
							first = False
						else:
							query += " %s "%connection
						query += k + " %s "%operator + " ? "
						if operator.strip() == "like" and "%" not in v1:
							v1 = "%%%s%%"%v1
						vals += (v1,)
				else:
					if first:
						first = False
					else:
						query += " %s "%connection
					query += k + " %s "%operator + "? "
					if operator.strip() == "like" and "%" not in v:
						v = "%%%s%%"%v
					vals += (v,)
		query += " order by " + orderBy + " " + orderType if orderBy else ""
		if limitTo is not None:
			query += " LIMIT %s"%(str(limitTo))
			if limitOffset is not None:
				query += " OFFSET %s"%(str(limitOffset))
		if saveQuery:
			self.lastQuery = query
			self.lastVals  = vals
		try:
			if len(vals) > 0:
				self.cursExec(query, vals)
			else:
				self.cursExec(query)
		except:
			print("[DB] query failed: %s"%query)
			print(vals)
		fetched_in = self.curs.fetchall()
		self.lastFetched = self.completeFetched(fetched_in)
		return self
	
	def getAll(self, params = None, connection = "and", operator = "=", orderBy = "firstdate", orderType = "ASC", limitTo = None, limitOffset = None, saveQuery = True):
		"""
		Use self.fetchAll and returns the dictionary of fetched entries

		Parameters: see self.fetchAll

		Output:
			a dictionary
		"""
		return self.fetchAll(params = params, connection = connection, operator = operator, orderBy = orderBy, orderType = orderType, limitTo = limitTo, limitOffset = limitOffset, saveQuery = saveQuery).lastFetched

	def fetchByBibkey(self, bibkey, saveQuery = True):
		"""
		Use self.fetchAll with a match on the bibtex key and returns the dictionary of fetched entries

		Parameters:
			bibkey: the bibtex key to match (or a list)
			saveQuery (boolean, default True): whether to save the query or not

		Output:
			self
		"""
		if type(bibkey) is list:
			return self.fetchAll(params = {"bibkey": bibkey},
				connection = "or", saveQuery = saveQuery)
		else:
			return self.fetchAll(params = {"bibkey": bibkey}, saveQuery = saveQuery)
		
	def getByBibkey(self, bibkey, saveQuery = True):
		"""
		Use self.fetchByBibkey and returns the dictionary of fetched entries

		Parameters: see self.fetchByBibkey

		Output:
			a dictionary
		"""
		return self.fetchByBibkey(bibkey, saveQuery = saveQuery).lastFetched

	def fetchByKey(self, key, saveQuery = True):
		"""
		Use self.fetchAll with a match on the bibtex key in the bibkey, bibtex or old_keys fields and returns the dictionary of fetched entries

		Parameters:
			key: the bibtex key to match (or a list)
			saveQuery (boolean, default True): whether to save the query or not

		Output:
			self
		"""
		if type(key) is list:
			strings = ["%%%s%%"%q for q in key]
			return self.fetchAll(
				params = {"bibkey": strings, "old_keys": strings, "bibtex": strings},
				connection = "or ",
				operator = " like ",
				saveQuery = saveQuery)
		else:
			return self.fetchAll(
				params = {"bibkey": "%%%s%%"%key, "old_keys": "%%%s%%"%key, "bibtex": "%%%s%%"%key},
				connection = "or ",
				operator = " like ",
				saveQuery = saveQuery)

	def getByKey(self, key, saveQuery = True):
		"""
		Use self.fetchByKey and returns the dictionary of fetched entries

		Parameters: see self.fetchByKey

		Output:
			a dictionary
		"""
		return self.fetchByKey(key, saveQuery = saveQuery).lastFetched

	def fetchByBibtex(self, string, saveQuery = True):
		"""
		Use self.fetchAll with a match on the bibtex content and returns the dictionary of fetched entries

		Parameters:
			string: the string to match in the bibtex (or a list)
			saveQuery (boolean, default True): whether to save the query or not

		Output:
			self
		"""
		if type(string) is list:
			return self.fetchAll(
				params = {"bibtex":["%%%s%%"%q for q in string]},
				connection = "or",
				operator = " like ",
				saveQuery = saveQuery)
		else:
			return self.fetchAll(
				params = {"bibtex":"%%%s%%"%string},
				operator = " like ",
				saveQuery = saveQuery)

	def getByBibtex(self, string, saveQuery = True):
		"""
		Use self.fetchByBibtex and returns the dictionary of fetched entries

		Parameters: see self.fetchByBibtex

		Output:
			a dictionary
		"""
		return self.fetchByBibtex(string, saveQuery = saveQuery).lastFetched

	def getField(self, key, field):
		"""
		Extract the content of one field from a entry in the database, searched by bibtex key

		Parameters:
			key: the bibtex key
			field: the field name

		Output:
			False if the search failed, the output of self.getByBibkey otherwise
		"""
		try:
			return self.getByBibkey(key, saveQuery = False)[0][field]
		except IndexError:
			print("[DB] ERROR in getEntryField('%s', '%s'): no element found?"%(key, field))
			return False
		except KeyError:
			print("[DB] ERROR in getEntryField('%s', '%s'): the field is missing?"%(key, field))
			return False

	def toDataDict(self, key):
		"""
		Convert the entry bibtex into a dictionary

		Parameters:
			key: the bibtex key

		Output:
			the output of self.prepareInsertEntry
		"""
		return self.prepareInsert(self.getField(key, "bibtex"))

	def getDoiUrl(self, key):
		"""
		Get the doi.org url for the entry, if it has something in the doi field

		Parameters:
			key: the bibtex key

		Output:
			a string
		"""
		url = self.getField(key, "doi")
		return pbConfig.doiUrl + url if url != "" and url is not False and url is not None else False

	def getArxivUrl(self, key, urlType = "abs"):
		"""
		Get the arxiv.org url for the entry, if it has something in the arxiv field

		Parameters:
			key: the bibtex key
			urlType: "abs" or "pdf"

		Output:
			a string
		"""
		url = self.getField(key, "arxiv")
		return pbConfig.arxivUrl + urlType + "/" + url if url != "" and url is not False and url is not None and url is not "" else False

	def insert(self, data):
		"""
		Insert an entry

		Parameters:
			data: a dictionary with the data fields to be inserted

		Output:
			the output of self.connExec
		"""
		return self.connExec("INSERT into entries (" +
					", ".join(self.tableCols["entries"]) + ") values (:" +
					", :".join(self.tableCols["entries"]) + ")\n",
					data)

	def update(self, data, oldkey):
		"""
		Update an entry

		Parameters:
			data: a dictionary with the new field contents
			oldKey: the bibtex key of the entry to be updated

		Output:
			the output of self.connExec
		"""
		data["bibkey"] = oldkey
		query = "replace into entries (" +\
					", ".join(data.keys()) + ") values (:" + \
					", :".join(data.keys()) + ")\n"
		return self.connExec(query, data)

	def prepareInsert(self,
			bibtex, bibkey = None, inspire = None, arxiv = None, ads = None, scholar = None, doi = None, isbn = None,
			year = None, link = None, comments = None, old_keys = None, crossref = None,
			exp_paper = None, lecture = None, phd_thesis = None, review = None, proceeding = None, book = None,
			marks = None, firstdate = None, pubdate = None, noUpdate = None, abstract = None, number = None):
		"""
		Convert a bibtex into a dictionary, eventually using also additional info

		Mandatory parameter:
			bibtex: the bibtex string for the entry (more than one is allowed, only one will be considered, see Optional argument>number)

		Optional fields:
			number (default None, converted to 0): the index of the desired entry in the list of bibtex strings
			the value for the fields in the database table:
			bibkey, inspire, arxiv, ads, scholar, doi, isbn, year, link, comments, old_keys, crossref, exp_paper, lecture, phd_thesis, review, proceeding, book, marks, firstdate, pubdate, noUpdate, abstract

		Output:
			a dictionary with all the field values for self.insert
		"""
		data = {}
		if number is None:
			number = 0
		try:
			element = bibtexparser.loads(bibtex).entries[number]
			data["bibkey"] = bibkey if bibkey else element["ID"]
		except IndexError:
			print("[DB] ERROR: no elements found?")
			data["bibkey"] = ""
			return data
		except KeyError:
			print("[DB] ERROR: impossible to parse bibtex!")
			data["bibkey"] = ""
			return data
		db = bibtexparser.bibdatabase.BibDatabase()
		db.entries = []
		db.entries.append(element)
		data["bibtex"]  = self.rmBibtexComments(self.rmBibtexACapo(pbWriter.write(db).strip()))
		data["inspire"] = inspire if inspire else None
		if arxiv:
			data["arxiv"] = arxiv
		else:
			try:
				data["arxiv"] = element["arxiv"]
			except KeyError:
				try:
					data["arxiv"] = element["eprint"]
				except KeyError:
					data["arxiv"] = ""
		data["ads"] = ads if ads else None
		data["scholar"] = scholar if scholar else None
		if doi:
			data["doi"] = doi
		else:
			try:
				data["doi"] = element["doi"]
			except KeyError:
				data["doi"] = None
		if isbn:
			data["isbn"] = isbn
		else:
			try:
				data["isbn"] = element["isbn"]
			except KeyError:
				data["isbn"] = None
		data["year"] = None
		if year:
			data["year"] = year
		else:
			try:
				data["year"] = element["year"]
			except KeyError:
				try:
					identif = re.compile("([0-9]{4}.[0-9]{4,5}|[0-9]{7})*")
					for t in identif.finditer(data["arxiv"]):
						if len(t.group()) > 0:
							e = t.group()
							a = e[0:2]
							if int(a) > 80:
								data["year"] = "19"+a
							else:
								data["year"] = "20"+a
				except KeyError:
					data["year"]=None
		if link:
			data["link"] = link
		else:
			try:
				if data["arxiv"] != "":
					data["link"] = pbConfig.arxivUrl + "abs/" + data["arxiv"]
				else:
					data["link"] = None
			except KeyError:
				try:
					data["link"] = pbConfig.doiUrl + data["doi"]
				except KeyError:
					data["link"] = None
		data["comments"] = comments if comments else None
		data["old_keys"] = old_keys if old_keys else None
		if crossref:
			data["crossref"] = crossref
		else:
			try:
				data["crossref"] = element["crossref"]
			except KeyError:
				data["crossref"] = None
		data["exp_paper"] = 1 if exp_paper else 0
		data["lecture"] = 1 if lecture else 0
		data["phd_thesis"] = 1 if phd_thesis else 0
		data["review"] = 1 if review else 0
		data["proceeding"] = 1 if proceeding else 0
		data["book"] = 1 if book else 0
		data["noUpdate"] = 1 if noUpdate else 0
		data["marks"] = marks if marks else ""
		if not abstract:
			try:
				abstract = element["abstract"]
			except KeyError:
				pass
		data["abstract"] = abstract if abstract else None
		data["firstdate"] = firstdate if firstdate else datetime.date.today().strftime("%Y-%m-%d")
		data["pubdate"] = pubdate if pubdate else ""
		return data
		
	def prepareUpdateByKey(self, key_old, key_new):
		"""
		Get an entry bibtex and prepare an update, using the new bibtex from another database entry

		Parameters:
			key_old: the key of the old entry
			key_new: the key of the new entry

		Output:
			the output of self.prepareInsert(u)
		"""
		u = self.prepareUpdate(self.getField(key_old, "bibtex"), self.getField(key_new, "bibtex"))
		return self.prepareInsert(u)
	
	def prepareUpdateByBibtex(self, key_old, bibtex_new):
		"""
		Get an entry bibtex and prepare an update, using the new bibtex passed as an argument

		Parameters:
			key_old: the key of the old entry
			bibtex_new: the new bibtex

		Output:
			the output of self.prepareInsert(u)
		"""
		u = self.prepareUpdate(self.getEntryField(key_old, "bibtex"), bibtex_new)
		return self.prepareInsert(u)
		
	def prepareUpdate(self, bibtexOld, bibtexNew):
		"""
		Prepare the update of an entry, comparing two bibtexs.
		Uses the fields from the old bibtex, adds the ones in the new bibtex and updates the repeated ones

		Parameters:
			bibtexOld: the old bibtex
			bibtexNew: the new bibtex

		Output:
			the joined bibtex
		"""
		elementOld = bibtexparser.loads(bibtexOld).entries[0]
		elementNew = bibtexparser.loads(bibtexNew).entries[0]
		db = bibtexparser.bibdatabase.BibDatabase()
		db.entries = []
		keep = elementOld
		for k in elementNew.keys():
			if k not in elementOld.keys():
				keep[k] = elementNew[k]
			elif elementNew[k] and elementNew[k] != elementOld[k] and k != "bibtex" and k != "ID":
				keep[k] = elementNew[k]
		db.entries.append(keep)
		return pbWriter.write(db)

	def updateInspireID(self, string, key = None, number = None):
		"""
		Use inspire websearch module to get and update the inspire ID of an entry

		Parameters:
			string: the string so be searched
			key (optional): the bibtex key of the database entry
			number (optional): the index of the desired element in the list of results

		Output:
			the id or False if empty
		"""
		newid = physBiblioWeb.webSearch["inspire"].retrieveInspireID(string, number = number)
		if key is None:
			key = string
		if newid is not "":
			query = "update entries set inspire=:inspire where bibkey=:bibkey\n"
			if self.connExec(query, {"inspire": newid, "bibkey": key}):
				return newid
		else:
			return False
	
	def updateField(self, key, field, value, verbose = 1):
		"""
		Update a single field of an entry

		Parameters:
			key: the bibtex key
			field: the field name
			value: the new value of the field
			verbose (int): increase output level

		Output:
			the output of self.connExec or False if the field is invalid
		"""
		if verbose > 0:
			print("[DB] updating '%s' for entry '%s'"%(field, key))
		if field in self.tableCols["entries"] and field != "bibkey" \
				and value is not None:
			query = "update entries set " + field + "=:field where bibkey=:bibkey\n"
			if verbose > 1:
				print(query, field, value)
			return self.connExec(query, {"field": value, "bibkey": key})
		else:
			if verbose > 1:
				print("[DB] non-existing field or unappropriated value: (%s, %s, %s)"%(key, field, value))
			return False
	
	def updateBibkey(self, oldKey, newKey):
		"""
		Update the bibtex key of an entry

		Parameters:
			oldKey: the old bibtex key
			newKey: the new bibtex key

		Output:
			the output of self.connExec or False if some errors occurred
		"""
		print("[DB] updating bibkey for entry '%s' into '%s'"%(oldKey, newKey))
		try:
			query = "update entries set bibkey=:new where bibkey=:old\n"
			if self.connExec(query, {"new": newKey, "old": oldKey}):
				query = "update entryCats set bibkey=:new where bibkey=:old\n"
				if self.connExec(query, {"new": newKey, "old": oldKey}):
					query = "update entryExps set bibkey=:new where bibkey=:old\n"
					return self.connExec(query, {"new": newKey, "old": oldKey})
				else:
					return False
			else:
				return False
		except:
			print(traceback.format_exc())
			return False
			
	def getDailyInfoFromOAI(self, date1 = None, date2 = None):
		"""
		Use inspire OAI webinterface to get updated information on the entries between two dates

		Parameters:
			date1, date2: the two dates defining the time interval to consider
		"""
		if date1 is None or not re.match("[0-9]{4}-[0-9]{2}-[0-9]{2}", date1):
			date1 = (datetime.date.today() - datetime.timedelta(1)).strftime("%Y-%m-%d")
		if date2 is None or not re.match("[0-9]{4}-[0-9]{2}-[0-9]{2}", date2):
			date2 = datetime.date.today().strftime("%Y-%m-%d")
		yren, monen, dayen = date1.split('-')
		yrst, monst, dayst = date2.split('-')
		print("[DB] calling INSPIRE-HEP OAI harvester between dates %s and %s"%(date1, date2))
		date1 = datetime.datetime(int(yren), int(monen), int(dayen))
		date2 = datetime.datetime(int(yrst), int(monst), int(dayst))
		entries = physBiblioWeb.webSearch["inspireoai"].retrieveOAIUpdates(date1, date2)
		for e in entries:
			try:
				key = e["bibkey"]
				print(key)
				old = self.extractEntryByBibkey(key)
				if len(old) > 0:
					for [o, d] in physBiblioWeb.webSearch["inspireoai"].correspondences:
						if e[o] != old[0][d]:
							self.updateEntryField(key, d, e[o], 0)
			except:
				print("[DB][oai] something missing in entry %s"%e["id"])
		print("[DB] inspire OAI harvesting done!")

	def updateInfoFromOAI(self, inspireID, bibtex = None, verbose = 0):
		"""
		Use inspire OAI to retrieve the info for a single entry

		Parameters:
			inspireID: the id of the entry in inspires. If is not a number, assume it is the bibtex key
			bibtex: see physBiblio.webimport.inspireoai.retrieveOAIData
			verbose: increase level of verbosity

		Output:
			True if successful, or False if there were errors
		"""
		if not inspireID.isdigit(): #assume it's a key instead of the inspireID
			inspireID = self.getField(inspireID, "inspire")
			try:
				inspireID.isdigit()
			except AttributeError:
				pBErrorManager("[DB] wrong value/format in inspireID: %s"%inspireID)
				return False
		result = physBiblioWeb.webSearch["inspireoai"].retrieveOAIData(inspireID, bibtex = bibtex, verbose = verbose)
		if verbose > 1:
			print(result)
		if result is False:
			pBErrorManager("[DB][oai] empty record looking for recid:%s!"%inspireID)
			return False
		try:
			key = result["bibkey"]
			old = self.getByBibkey(key, saveQuery = False)
			if verbose > 1:
				print("%s, %s"%(key, old))
			if len(old) > 0:
				for [o, d] in physBiblioWeb.webSearch["inspireoai"].correspondences:
					try:
						if verbose > 0:
							print("%s = %s (%s)"%(d, result[o], old[0][d]))
						if result[o] != old[0][d]:
							if o == "bibtex" and result[o] is not None:
								self.updateField(key, d, self.rmBibtexComments(self.rmBibtexACapo(result[o].strip())), verbose = 0)
							else:
								self.updateField(key, d, result[o], verbose = 0)
					except:
						pBErrorManager("[DB][oai] key error: (%s, %s)"%(o,d), traceback, priority = 0)
			if verbose > 0:
				print("[DB] inspire OAI info for %s saved."%inspireID)
		except:
			pBErrorManager("[DB][oai] something missing in entry %s"%inspireID, traceback, priority = 1)
			return False
		return True
	
	def updateFromOAI(self, entry, verbose = 0):
		"""
		Update an entry from inspire OAI. If inspireID is missing, look for it before

		Parameters:
			entry: the inspire ID or an identifier of the entry to consider (also a list is accepted)
			verbose: increase level of verbosity

		Output:
			for a single entry, the output of self.updateInfoFromOAI
		"""
		if type(entry) is list:
			for e in entry:
				self.updateFromOAI(e, verbose = verbose)
		elif entry.isdigit():
			return self.updateInfoFromOAI(entry, verbose = verbose)
		else:
			inspireID = self.getField(entry, "inspire")
			if inspireID is not None:
				return self.updateInfoFromOAI(inspireID, verbose = verbose)
			else:
				inspireID = self.updateInspireID(entry, entry)
				return self.updateInfoFromOAI(inspireID, verbose = verbose)

	def replaceInBibtex(self, old, new):
		"""
		Replace a string with a new one, in all the matching bibtex entries of the table

		Parameters:
			old: the old string
			new: the new string

		Output:
			the list of keys of the matching bibtex entries or False if self.connExec failed
		"""
		self.lastQuery = "SELECT * FROM entries WHERE bibtex LIKE :match"
		self.lastVals  = {"match": "%"+old+"%"}
		self.cursExec(self.lastQuery, self.lastVals)
		self.lastFetched = self.completeFetched(self.curs.fetchall())
		keys = [k["bibkey"] for k in self.lastFetched]
		print("[DB] Replacing text in entries: ", keys)
		if self.connExec("UPDATE entries SET bibtex = replace( bibtex, :old, :new ) WHERE bibtex LIKE :match", {"old": old, "new": new, "match": "%"+old+"%"}):
			return keys
		else:
			return False

	def replace(self, fiOld, fiNews, old, news, entries = None, regex = False):
		"""
		Replace a string with a new one, in the given field of the (previously) selected bibtex entries

		Parameters:
			fiOld: the field where the string to match is taken from
			fiNews: the new fields where to insert the replaced string
			old: the old string to replace
			news: the list of new strings
			entries (None or a list): the entries to consider. If None, use self.getAll
			regex (boolean, default False): whether to use regular expression for matching and replacing

		Output:
			success, changed, failed: the lists of entries that were successfully processed, changed or produced errors
		"""
		def myReplace(line, new, previous = None):
			"""
			Replace the old with the new string in the given line

			Parameters:
				line: the string where to match and replace
				new: the new string
				previous (default None): the previous content of the field (useful when using regex and complex replaces)

			Output:
				the processed line or previous (if regex and no matches are found)
			"""
			if regex:
				reg = re.compile(old)
				if reg.match(line):
					line = reg.sub(new, line)
				else:
					line = previous
			else:
				line = line.replace(old, new)
			return line
		if entries is None:
			entries = self.getAll(saveQuery = False)
		success = []
		changed = []
		failed = []
		for entry in entries:
			try:
				if not fiOld in entry["bibtexDict"].keys() and not fiOld in entry.keys():
					raise KeyError("Field %s not found in entry %s"%(fiOld, entry["bibkey"]))
				if fiOld in entry["bibtexDict"].keys():
					before = entry["bibtexDict"][fiOld]
				elif fiOld in entry.keys():
					before = entry[fiOld]
				bef = []
				aft = []
				for fiNew, new in zip(fiNews, news):
					if not fiNew in entry["bibtexDict"].keys() and not fiNew in entry.keys():
						raise KeyError("Field %s not found in entry %s"%(fiNew, entry["bibkey"]))
					if fiNew in entry["bibtexDict"].keys():
						bef.append(entry["bibtexDict"][fiNew])
						after  = myReplace(before, new, previous = entry["bibtexDict"][fiNew])
						aft.append(after)
						entry["bibtexDict"][fiNew] = after
						db = bibtexparser.bibdatabase.BibDatabase()
						db.entries = []
						db.entries.append(entry["bibtexDict"])
						entry["bibtex"] = self.rmBibtexComments(self.rmBibtexACapo(pbWriter.write(db).strip()))
						self.updateField(entry["bibkey"], "bibtex", entry["bibtex"], verbose = 0)
					if fiNew in entry.keys():
						bef.append(entry[fiNew])
						after  = myReplace(before, new, previous = entry[fiNew])
						aft.append(after)
						self.updateField(entry["bibkey"], fiNew, after, verbose = 0)
			except KeyError:
				pBErrorManager("[DB] something wrong in replace", traceback)
				failed.append(entry["bibkey"])
			else:
				success.append(entry["bibkey"])
				if any(b != a for a,b in zip(aft, bef)):
					changed.append(entry["bibkey"])
		return success, changed, failed

	def rmBibtexComments(self, bibtex):
		"""
		Remove comments and empty lines from a bibtex

		Parameters:
			bibtex: the bibtex to process

		Output:
			the processed bibtex
		"""
		output = ""
		for l in bibtex.splitlines():
			lx = l.strip()
			if len(lx) > 0 and lx[0] != "%":
				output += l + "\n"
		return output.strip()

	def rmBibtexACapo(self, bibtex):
		"""
		Remove line breaks in the fields of a bibtex

		Parameters:
			bibtex: the bibtex to process

		Output:
			the processed bibtex
		"""
		output = ""
		db = bibtexparser.bibdatabase.BibDatabase()
		tmp = {}
		for k,v in bibtexparser.loads(bibtex).entries[0].items():
			tmp[k] = v.replace("\n", " ")
		db.entries = [tmp]
		return pbWriter.write(db)

	def getFieldsFromArxiv(self, bibkey, fields):
		"""
		Use arxiv.org to retrieve more fields for the entry

		Parameters:
			bibkey: the bibtex key of the entry
			fields: the fields to be updated using information from arxiv.org

		Output:
			False or the error message (used in the GUI part) if some error occurred,
			True if a single entry has been successfully processed
			or
			the lists of successfully processed entryes and failures when considering a list
		"""
		if type(bibkey) is list:
			tot = len(bibkey)
			self.getArxivFieldsFlag = True
			success = []
			fail = []
			print("[DB] thread_fieldsArxiv will process %d entries."%tot)
			for ix, k in enumerate(bibkey):
				arxiv = str(self.getField(k, "arxiv"))
				if self.getArxivFieldsFlag and arxiv.strip() != "":
					print("\n[DB] %5d / %d (%5.2f%%) - processing: arxiv:%s\n"%(ix+1, tot, 100.*(ix+1)/tot, arxiv))
					result = self.getFieldsFromArxiv(k, fields)
					if result is True:
						success.append(k)
					else:
						fail.append(k)
			print("\n\n[DB] thread_fieldsArxiv has finished!")
			print("%d entries processed, of which these %d generated errors:\n%s"%(len(success+fail), len(fail), fail))
			return success, fail
		bibtex = self.getField(bibkey, "bibtex")
		arxiv = str(self.getField(bibkey, "arxiv"))
		if arxiv.strip() == "":
			return False
		try:
			arxivBibtex, arxivDict = physBiblioWeb.webSearch["arxiv"].retrieveUrlAll(arxiv, fullDict = True)
			tmp = bibtexparser.loads(bibtex).entries[0]
			for k in fields:
				try:
					tmp[k] = arxivDict[k]
				except KeyError:
					pass
			if "authors" in fields:
				try:
					authors = tmp["authors"].split(" and ")
					if len(authors) > pbConfig.params["maxAuthorSave"]:
						start = 1 if "collaboration" in authors[0] else 0
						tmp["authors"] = " and ".join(authors[start:start+pbConfig.params["maxAuthorSave"]] + ["others"])
				except KeyError:
					pass
			db = bibtexparser.bibdatabase.BibDatabase()
			db.entries = [tmp]
			bibtex = self.rmBibtexComments(self.rmBibtexACapo(pbWriter.write(db).strip()))
			self.updateField(bibkey, "bibtex", bibtex)
			return True
		except Exception:
			return "Cannot get and save info from arXiv!\n" + traceback.format_exc()

	def loadAndInsert(self, entry, method = "inspire", imposeKey = None, number = None, returnBibtex = False, childProcess = False):
		"""
		Read a list of keywords and look for inspire contents, then load in the database all the info

		Parameters:
			entry: the bibtex key or a list
			method: "inspire" (default) or any other supported method from the webimport subpackage
			imposeKey (default None): if a string, the bibtex key to use with the imported entry
			number (default None): if not None, the index of the wanted entry in the list of results
			returnBibtex (boolean, default False): whether to return the bibtex of the entry
			childProcess (boolean, default False): if True, do not reset the self.lastInserted (used when recursively called)

		Output:
			False if some error occurred, True if successful but returnBibtex is False or entry is not a list, the bibtex field if entry is a single element and returnBibtex is True
		"""
		requireAll = False
		def printExisting(entry, existing):
			"""
			Print a message if the entry already exists, returns True or the bibtex field depending on the value of returnBibtex

			Parameters:
				entry: the entry key
				existing: the list of dictionaries returned by self.getByBibkey

			Output:
				the bibtex field if returnBibtex is True, True otherwise
			"""
			print("[DB] Already existing: %s\n"%entry)
			if returnBibtex:
				return existing[0]["bibtex"]
			else:
				return True
		def returnListIfSub(a, out):
			"""
			If the original list contains sublists, return a list with all the elements in the list and each sublist

			Parameters:
				a: the original list
				out: the previous output, which will be recursively increased

			Output:
				the output, increased with the new elements
			"""
			if type(a) is list:
				for el in a:
					out = returnListIfSub(el, out)
				return out
			else:
				out += [a]
				return out
		if not childProcess:
			self.lastInserted = []
		if entry is not None and not type(entry) is list:
			existing = self.getByBibkey(entry, saveQuery = False)
			if existing:
				return printExisting(entry, existing)
			if method == "bibtex":
				e = entry
			else:
				e = physBiblioWeb.webSearch[method].retrieveUrlAll(entry)
				if e.count('@') > 1:
					if number is not None:
						requireAll = True
					else:
						print(e)
						print("[DB] WARNING: possible mismatch. Specify the number of element to select with 'number'\n")
						return False
			if requireAll:
				data = self.prepareInsert(e, number = number)
			else:
				data = self.prepareInsert(e)
			key = data["bibkey"]
			if pbConfig.params["fetchAbstract"] and data["arxiv"] is not None:
				arxivBibtex, arxivDict = physBiblioWeb.webSearch["arxiv"].retrieveUrlAll(data["arxiv"], fullDict = True)
				data["abstract"] = arxivDict["abstract"]
			if imposeKey is not None:
				data["bibkey"] = imposeKey
				data["bibtex"] = data["bibtex"].replace(key, imposeKey)
				key = imposeKey
			if key.strip() == "":
				pBErrorManager("[DB] ERROR: impossible to insert an entry with empty bibkey!\n%s\n"%entry)
				return False
			existing = self.getByBibkey(key, saveQuery = False)
			if existing:
				return printExisting(key, existing)
			print("[DB] entry will have key\n'%s'"%key)
			try:
				self.insert(data)
			except:
				pBErrorManager("[DB] loadAndInsert(%s) failed in inserting entry\n"%entry)
				return False
			try:
				if method == "inspire":
					if not requireAll:
						eid = self.updateInspireID(entry, key)
					else:
						eid = self.updateInspireID(entry, key, number = number)
					self.updateInfoFromOAI(eid)
				elif method == "isbn":
					self.setBook(key)
				print("[DB] element successfully inserted.\n")
				self.lastInserted.append(key)
				if returnBibtex:
					return e
				else:
					return True
			except:
				pBErrorManager("[DB] loadAndInsertEntries(%s) failed in completing info\n"%entry)
				return False
		elif entry is not None and type(entry) is list:
			failed = []
			entry = returnListIfSub(entry, [])
			self.runningLoadAndInsert = True
			tot = len(entry)
			print("[DB] loadAndInsert will process %d total entries"%tot)
			ix = 0
			for e in entry:
				if type(e) is float:
					e = str(e)
				if self.runningLoadAndInsert:
					print("[DB] %5d / %d (%5.2f%%) - looking for string: '%s'\n"%(ix+1, tot, 100.*(ix+1)/tot, e))
					if not self.loadAndInsert(e, childProcess = True):
						failed.append(e)
					ix += 1
			if len(self.lastInserted) > 0:
				print("[DB] imported entries:\n%s"%", ".join(self.lastInserted))
			if len(failed) > 0:
				pBErrorManager("[DB] ERRORS!\nFailed to load and import entries:\n%s"%", ".join(failed))
			return True
		else:
			print("[DB] ERROR: invalid arguments to loadAndInsertEntries!")
			return False
			
	def loadAndInsertWithCats(self, entry, method = "inspire", imposeKey = None, number = None, returnBibtex = False, childProcess = False):
		"""
		Load the entries, then ask for their categories. Uses self.loadAndInsert and self.mainDB.catBib.askCats

		Parameters: see self.loadAndInsert
		"""
		self.loadAndInsert(entry, method = method, imposeKey = imposeKey, number = number, returnBibtex = returnBibtex, childProcess = childProcess)
		self.mainDB.catBib.askCats(self.lastInserted)

	def importFromBib(self, filename, completeInfo = True):
		"""
		Read a .bib file and add the contained entries in the database

		Parameters:
			filename: the name of the .bib file
			completeInfo (boolean, default True): use the bibtex key and other fields to look for more information online
		"""
		def printExisting(entry):
			"""
			Print a message when the entry is already present in the database

			Parameters:
				entry: the entry key
			"""
			print("[DB] Already existing: %s\n"%entry)
		self.lastInserted = []
		exist = []
		errors = []
		print("[DB] Importing from file bib: %s"%filename)
		with open(filename) as r:
			bibText = r.read()
		elements = bibtexparser.loads(bibText).entries
		db = bibtexparser.bibdatabase.BibDatabase()
		self.importFromBibFlag = True
		print("[DB] entries to be processed: %d"%len(elements))
		tot = len(elements)
		for ie, e in enumerate(elements):
			if self.importFromBibFlag:
				db.entries = [e]
				bibtex = self.rmBibtexComments(self.rmBibtexACapo(pbWriter.write(db).strip()))
				data = self.prepareInsert(bibtex)
				key = data["bibkey"]
				print("[DB] %5d / %d (%5.2f%%), processing entry %s"%(ie+1, tot, 100.*(ie+1.)/tot, key))
				existing = self.getByBibkey(key, saveQuery = False)
				if existing:
					printExisting(key)
					exist.append(key)
				elif key.strip() == "":
					pBErrorManager("[DB] ERROR: impossible to insert an entry with empty bibkey!\n")
					errors.append(key)
				else:
					if completeInfo and pbConfig.params["fetchAbstract"] and data["arxiv"] is not None:
						arxivBibtex, arxivDict = physBiblioWeb.webSearch["arxiv"].retrieveUrlAll(data["arxiv"], fullDict = True)
						data["abstract"] = arxivDict["abstract"]
					print("[DB] entry will have key\n'%s'"%key)
					if not self.insert(data):
						pBErrorManager("[DB] failed in inserting entry %s\n"%key)
						errors.append(key)
					else:
						self.mainDB.catBib.insert(pbConfig.params["defaultCategories"], key)
						try:
							if completeInfo:
								eid = self.updateInspireID(key)
								self.updateInfoFromOAI(eid)
							print("[DB] element successfully inserted.\n")
							self.lastInserted.append(key)
						except Exception as err:
							pBErrorManager("[DB] failed in completing info for entry %s\n"%key, priority = 1)
							print(err)
							errors.append(key)
		print("[DB] import completed.\n%d entries processed, of which %d existing, %d successfully inserted and %d errors."%(
			len(elements), len(exist), len(self.lastInserted), len(errors)))

	def setBook(self, key, value = 1):
		"""
		Set (or unset) the book field for an entry

		Parameters:
			key: the bibtex key
			value: 1 or 0

		Output:
			the output of self.updateField
		"""
		if type(key) is list:
			for q in key:
				self.setBook(q, value)
		else:
			return self.updateField(key, "book", value, 0)

	def setLecture(self, key, value = 1):
		"""
		Set (or unset) the Lecture field for an entry

		Parameters:
			key: the bibtex key
			value: 1 or 0

		Output:
			the output of self.updateField
		"""
		if type(key) is list:
			for q in key:
				self.setLecture(q, value)
		else:
			return self.updateField(key, "lecture", value, 0)

	def setPhdThesis(self, key, value = 1):
		"""
		Set (or unset) the PhD thesis field for an entry

		Parameters:
			key: the bibtex key
			value: 1 or 0

		Output:
			the output of self.updateField
		"""
		if type(key) is list:
			for q in key:
				self.setPhdThesis(q, value)
		else:
			return self.updateField(key, "phd_thesis", value, 0)

	def setProceeding(self, key, value = 1):
		"""
		Set (or unset) the proceeding field for an entry

		Parameters:
			key: the bibtex key
			value: 1 or 0

		Output:
			the output of self.updateField
		"""
		if type(key) is list:
			for q in key:
				self.setProceeding(q, value)
		else:
			return self.updateField(key, "proceeding", value, 0)

	def setReview(self, key, value = 1):
		"""
		Set (or unset) the review field for an entry

		Parameters:
			key: the bibtex key
			value: 1 or 0

		Output:
			the output of self.updateField
		"""
		if type(key) is list:
			for q in key:
				self.setReview(q, value)
		else:
			return self.updateField(key, "review", value, 0)

	def setNoUpdate(self, key, value = 1):
		"""
		Set (or unset) the noUpdate field for an entry

		Parameters:
			key: the bibtex key
			value: 1 or 0

		Output:
			the output of self.updateField
		"""
		if type(key) is list:
			for q in key:
				self.setNoUpdate(q, value)
		else:
			return self.updateField(key, "noUpdate", value, 0)
			
	def printAllBibtexs(self, entriesIn = None):
		"""
		Print the bibtex codes for all the entries (or for a given subset)

		Parameters:
			entriesIn: the list of entries to print. If None, use self.lastFetched or self.getAll.
		"""
		if entriesIn is not None:
			entries = entriesIn
		elif self.lastFetched is not None:
			entries = self.lastFetched
		else:
			entries = self.getAll(orderBy = "firstdate")
		for i, e in enumerate(entries):
			print("%4d - %s\n"%(i, e["bibtex"]))
		print("[DB] %d elements found"%len(entries))
			
	def printAllBibkeys(self, entriesIn = None):
		"""
		Print the bibtex keys for all the entries (or for a given subset)

		Parameters:
			entriesIn: the list of entries to print. If None, use self.lastFetched or self.getAll.
		"""
		if entriesIn is not None:
			entries = entriesIn
		elif self.lastFetched is not None:
			entries = self.lastFetched
		else:
			entries = self.getAll(orderBy = "firstdate")
		for i, e in enumerate(entries):
			print("%4d %s"%(i, e["bibkey"]))
		print("[DB] %d elements found"%len(entries))
			
	def printAllInfo(self, entriesIn = None, orderBy = "firstdate", addFields = None):
		"""
		Print a short resume for all the bibtex entries (or for a given subset)

		Parameters:
			entriesIn: the list of entries to print. If None, use self.lastFetched or self.getAll.
			orderBy (default "firstdate"): field to consider for ordering the entries (if using self.getAll)
			addFields: print additional fields in addition to the minimal info, default None
		"""
		if entriesIn is not None:
			entries = entriesIn
		elif self.lastFetched is not None:
			entries = self.lastFetched
		else:
			entries = self.getAll(orderBy = orderBy)
		for i, e in enumerate(entries):
			orderDate = "[%4d - %-11s]"%(i, e["firstdate"])
			bibKeyStr = "%-30s "%e["bibkey"]
			typeStr = ""
			moreStr = "%-20s %-20s"%(
				e["arxiv"] if e["arxiv"] is not None else "-",
				e["doi"] if e["doi"] is not None else "-"
				)
			if e["book"] == 1:
				typeStr = "(book)"
				moreStr = "%-20s"%e["isbn"]
			elif e["review"] == 1:
				typeStr = "(rev)"
			elif e["lecture"] == 1:
				typeStr = "(lect)"
			elif e["phd_thesis"] == 1:
				typeStr = "(PhDTh)"
				moreStr = "%-20s"%(e["arxiv"] if e["arxiv"] is not None else "-")
			elif e["proceeding"] == 1:
				typeStr = "(proc)"
			print(orderDate + "%7s "%typeStr + bibKeyStr + moreStr)
			if addFields is not None:
				try:
					if type(addFields) is list:
						for f in addFields:
							try:
								print("   %s: %s"%(f, e[f]))
							except:
								print("   %s: %s"%(f, e["bibtexDict"][f]))
					else:
						try:
							print("   %s: %s"%(addFields, e[addFields]))
						except:
							print("   %s: %s"%(addFields, e["bibtexDict"][addFields]))
				except:
					pass
		print("[DB] %d elements found"%len(entries))

	def fetchByCat(self, idCat, orderBy = "entries.firstdate", orderType = "ASC"):
		"""
		Fetch all the entries associated to a given category

		Parameters:
			idCat: the id of the category
			orderBy (default "entries.firstdate"): the "table.field" to use for ordering
			orderType: "ASC" (default) or "DESC"

		Output:
			self
		"""
		query = """
				select * from entries
				join entryCats on entries.bibkey=entryCats.bibkey
				where entryCats.idCat=?
				"""
		query += " order by " + orderBy + " " + orderType if orderBy else ""
		self.cursExec(query, (idCat,))
		fetched_in = self.curs.fetchall()
		fetched_out = []
		for el in fetched_in:
			tmp = {}
			for k in el.keys():
				tmp[k] = el[k]
			tmp["bibtexDict"] = bibtexparser.loads(el["bibtex"]).entries[0]
			fetched_out.append(tmp)
		self.lastFetched = fetched_out
		return self

	def getByCat(self, idCat, orderBy = "entries.firstdate", orderType = "ASC"):
		"""
		Use self.fetchByCat and returns the dictionary of fetched entries

		Parameters: see self.fetchByCat

		Output:
			a dictionary
		"""
		return self.fetchByCat(idCat, orderBy = orderBy, orderType = orderType).lastFetched

	def fetchByExp(self, idExp, orderBy = "entries.firstdate", orderType = "ASC"):
		"""
		Fetch all the entries associated to a given experiment

		Parameters:
			idExp: the id of the experiment
			orderBy (default "entries.firstdate"): the "table.field" to use for ordering
			orderType: "ASC" (default) or "DESC"

		Output:
			self
		"""
		query = """
				select * from entries
				join entryExps on entries.bibkey=entryExps.bibkey
				where entryExps.idExp=?
				"""
		query += " order by " + orderBy + " " + orderType if orderBy else ""
		self.cursExec(query, (idExp,))
		fetched_in = self.curs.fetchall()
		fetched_out = []
		for el in fetched_in:
			tmp = {}
			for k in el.keys():
				tmp[k] = el[k]
			tmp["bibtexDict"] = bibtexparser.loads(el["bibtex"]).entries[0]
			fetched_out.append(tmp)
		self.lastFetched = fetched_out
		return self

	def getByExp(self, idExp, orderBy = "entries.firstdate", orderType = "ASC"):
		"""
		Use self.fetchByExp and returns the dictionary of fetched entries

		Parameters: see self.fetchByExp

		Output:
			a dictionary
		"""
		return self.fetchByExp(idExp, orderBy = orderBy, orderType = orderType).lastFetched

	def cleanBibtexs(self, startFrom = 0, entries = None):
		"""
		Clean (remove comments, unwanted fields, newlines, accents) and reformat the bibtexs

		Parameters:
			startFrom (default 0): the index where to start from
			entries: the list of entries to be considered. If None, the output of self.getAll

		Output:
			num, err, changed: the number of considered entries, the number of errors, the list of keys of changed entries
		"""
		if entries is None:
			try:
				entries = self.getAll(saveQuery = False)[startFrom:]
			except TypeError:
				pBErrorManager("[DB] invalid startFrom in cleanBibtexs", traceback)
				return 0, 0, []
		num = 0
		err = 0
		changed = []
		tot = len(entries)
		self.runningCleanBibtexs = True
		print("[DB] cleanBibtexs will process %d total entries"%tot)
		db = bibtexparser.bibdatabase.BibDatabase()
		for ix,e in enumerate(entries):
			if self.runningCleanBibtexs:
				num += 1
				print("[DB] %5d / %d (%5.2f%%) - cleaning: '%s'\n"%(ix+1, tot, 100.*(ix+1)/tot, e["bibkey"]))
				try:
					element = bibtexparser.loads(e["bibtex"]).entries[0]
					db.entries = []
					db.entries.append(element)
					newbibtex  = self.rmBibtexComments(self.rmBibtexACapo(pbWriter.write(db).strip()))
					if e["bibtex"] != newbibtex and self.updateField(e["bibkey"], "bibtex", newbibtex):
						print("[DB] -- element changed!")
						changed.append(e["bibkey"])
				except ValueError:
					pBErrorManager("[DB] Error while cleaning entry '%s'"%e["bibkey"], traceback, priority = 0)
					err += 1
		print("\n[DB] %d entries processed"%num)
		print("\n[DB] %d errors occurred"%err)
		print("\n[DB] %d entries changed"%len(changed))
		return num, err, changed
	
	def searchOAIUpdates(self, startFrom = 0, entries = None, force = False):
		"""
		Select unpublished papers and look for updates using inspireOAI

		Parameters:
			startFrom (default 0): the index in the list of entries where to start updating
			entries: the list of entries to be considered or None (if None, use self.getAll)
			force (boolean, default False): force the update also of entries which already have journal information

		Output:
			num, err, changed: the number of processed entries, the list of errors and of changed entries
		"""
		if entries is None:
			try:
				entries = self.getAll(saveQuery = False)[startFrom:]
			except TypeError:
				pBErrorManager("[DB] invalid startFrom in searchOAIUpdates", traceback)
				return 0, [], []
		num = 0
		err = []
		changed = []
		tot = len(entries)
		self.runningOAIUpdates = True
		print("[DB] searchOAIUpdates will process %d total entries"%tot)
		for ix,e in enumerate(entries):
			if self.runningOAIUpdates \
				and e["proceeding"] == 0 \
				and e["book"] == 0 \
				and e["lecture"] == 0 \
				and e["phd_thesis"] == 0 \
				and e["noUpdate"] == 0 \
				and e["inspire"] is not None \
				and e["inspire"] != "" \
				and (force or ( e["doi"] is None or "journal" not in e["bibtexDict"].keys() ) ):
					num += 1
					print("[DB] %5d / %d (%5.2f%%) - looking for update: '%s'"%(ix+1, tot, 100.*(ix+1)/tot, e["bibkey"]))
					if not self.updateInfoFromOAI(e["inspire"], bibtex = e["bibtex"], verbose = 0):
						err.append(e["bibkey"])
					elif e != self.getByBibkey(e["bibkey"], saveQuery = False)[0]:
						print("[DB] -- element changed!")
						changed.append(e["bibkey"])
					print("")
		print("\n[DB] %d entries processed"%num)
		print("\n[DB] %d errors occurred"%len(err))
		if len(err)>0:
			print(err)
		print("\n[DB] %d entries changed"%len(changed))
		if len(changed)>0:
			print(changed)
		return num, err, changed

class utilities(physbiblioDBSub):
	"""
	Adds some more useful functions to the database management
	"""
	def cleanSpareEntries(self):
		"""
		Find and delete connections (bibtex-category, bibtex-experiment, category-experiment) where one of the parts is missing
		"""
		def deletePresent(ix1, ix2, join, func):
			"""
			Delete the connections if one of the two extremities are missing in the respective tables.

			Parameters:
				ix1, ix2: the lists of ids/bibkeys where to look for the indexes
				join: the list of pairs of connected elements
				func: the function that must be used to delete the connections
			"""
			for e in join:
				if e[0] not in ix1 or e[1] not in ix2:
					print("[DB] cleaning (%s, %s)"%(e[0], e[1]))
					func(e[0], e[1])

		bibkeys = [ e["bibkey"] for e in self.mainDB.bibs.getAll(saveQuery = False) ]
		idCats  = [ e["idCat"]  for e in self.mainDB.cats.getAll() ]
		idExps  = [ e["idExp"]  for e in self.mainDB.exps.getAll() ]
		
		deletePresent(bibkeys, idExps, [ [e["bibkey"], e["idExp"]] for e in self.mainDB.bibExp.getAll()], self.mainDB.bibExp.delete)
		deletePresent(idCats, bibkeys, [ [e["idCat"], e["bibkey"]] for e in self.mainDB.catBib.getAll()], self.mainDB.catBib.delete)
		deletePresent(idCats, idExps,  [ [e["idCat"], e["idExp"]]  for e in self.mainDB.catExp.getAll()], self.mainDB.catExp.delete)
	
	def cleanAllBibtexs(self, verbose = 0):
		"""
		Remove newlines, non-standard characters and comments from the bibtex of all the entries in the database

		Parameters:
			verbose: print more messages
		"""
		b = self.mainDB.bibs
		for e in b.getAll():
			t = e["bibtex"]
			t = b.rmBibtexComments(t)
			t = parse_accents_str(t)
			t = b.rmBibtexACapo(t)
			b.updateField(e["bibkey"], "bibtex", t, verbose = verbose)


def catString(idCat, db, withDesc = False):
	"""
	Return the string describing the category (id, name, description if required)

	Parameters:
		idCat: the id of the category
		withDesc (boolean, default False): if True, add the category description

	Output:
		the output string
	"""
	try:
		cat = db.cats.getByID(idCat)[0]
	except IndexError:
		pBErrorManager("[DB][catString] category '%s' not in database"%idCat)
		return ""
	if withDesc:
		return '%4d: %s - <i>%s</i>'%(cat['idCat'], cat['name'], cat['description'])
	else:
		return '%4d: %s'%(cat['idCat'], cat['name'])

def cats_alphabetical(listId, db):
	"""
	Sort the categories in the given list in alphabetical order

	Parameters:
		listId: the list of ids of the categories

	Output:
		the list of ids, ordered according to the category names.
	"""
	listIn = []
	for i in listId:
		try:
			listIn.append(db.cats.getByID(i)[0])
		except IndexError:
			pBErrorManager("[DB][cats_alphabetical] category '%s' not in database"%i)
	decorated = [ (x["name"].lower(), x) for x in listIn ]
	decorated.sort()
	return [ x[1]["idCat"] for x in decorated ]

def dbStats(db):
	"""
	Get statistics on the number of entries in the various database tables
	
	Parameters:
		db: the database (instance of physbiblioDB)
	"""
	db.stats = {}
	db.stats["bibs"] = len(db.bibs.getAll())
	db.stats["cats"] = len(db.cats.getAll())
	db.stats["exps"] = len(db.exps.getAll())
	db.stats["catBib"] = len(db.catBib.getAll())
	db.stats["catExp"] = len(db.catExp.getAll())
	db.stats["bibExp"] = len(db.bibExp.getAll())

pBDB=physbiblioDB()
