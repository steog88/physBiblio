import bibtexparser

class MyBibTexWriter(bibtexparser.bwriter.BibTexWriter):
	def __init__(self):
		super(MyBibtexWriter, self).__init__()
		#use 13 characters for the field name:
		self._max_field_width=13
		#order of fields in output
		self.display_order=[
			'author','collaboration','title','publisher','journal','volume','year','pages',
			'russian',
			'archiveprefix','primaryclass','eprint','doi',
			'reportNumber']
		self.bracket_fields=['title','www','note','abstract','comment','article','url']
		self.excluded_fields=["adsnote", "adsurl", "slaccitation"]
		#Necessary to avoid a change of the ordering of the bibtex entries:
		self.order_entries_by=None
		self.comma_first = False

	#redefine the function that writes the entries in the bib file
	#adapted from bibtexparser.bwriter.BibTexWriter._entry_to_bibtex()
	def _entry_to_bibtex(self, entry):
		bibtex = ''
		# Write BibTeX key
		bibtex += '@' + entry['ENTRYTYPE'].capitalize() + '{' + entry['ID']

		# create display_order of fields for this entry
		# first those keys which are both in self.display_order and in entry.keys
		display_order = [i for i in self.display_order if i in entry]
		# then all the other fields sorted alphabetically
		display_order += [i for i in sorted(entry) if i not in self.display_order and i not in self.excluded_fields]

		# Write field = value lines
		for field in [i for i in display_order if i not in ['ENTRYTYPE', 'ID']]:
			try:
				bibtex += ",\n" + self.indent + "{0:>{1}}".format(field, self._max_field_width) + ' = "' + \
					("{"+entry[field]+"}" if field in self.bracket_fields else entry[field]) + '"'
			except TypeError:
				raise TypeError(u"The field %s in entry %s must be a string"
								% (field, entry['ID']))
		bibtex += ",\n}\n" + self.entry_separator
		return bibtex

pbWriter = MyBibTexWriter()
