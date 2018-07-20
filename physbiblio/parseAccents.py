# -*- coding: iso-8859-15 -*-
"""
This module tries to convert the unicode accented chars into latex strings.
Will be probably rewritten to use pylatexenc.

This file is part of the physbiblio package.
"""
import re
import sys
from pylatexenc.latexencode import utf8tolatex

try:
	from physbiblio.errors import pBLogger
except ImportError:
	print("Could not find physbiblio and its contents: configure your PYTHONPATH!")
	print(traceback.format_exc())
	raise

accents_changed = []

def parse_accents_str(string):
	"""
	Function that reads a string and translates all the known unicode characters into latex commands.

	Parameters:
		string: the string to be translated

	Output:
		the processed string
	"""
	if string is not None and string is not "":
		string = utf8tolatex(string, non_ascii_only=True)
	return string

def parse_accents_record(record):
	"""
	Function that reads the fields inside a bibtex dictionary and translates all the known unicode characters into latex commands.

	Parameters:
		record: the bibtex dictionary generated by bibtexparser

	Output:
		the dictionary after having processed all the fields
	"""
	for val in record:
		if val is not "ID" and len(record[val].strip()) > 0:
			tmp = utf8tolatex(record[val], non_ascii_only=True)
			if tmp != record[val]:
				pBLogger.info("    -> Converting bad characters in entry %s: "%record["ID"])
				pBLogger.info("         -- "+tmp.encode("utf-8"))
				accents_changed.append(record["ID"])
			record[val] = tmp
	return record

latex2Html_commands = [
	["textit","i"],
	["textbf","b"],
]
latex2Html_strings = [
	["\%","%"],
	["~"," "],
	["\ "," "],
]
latex_replace = [
	["text", "rm"],
]

def texToHtml(text):
	"""
	Function that converts some Latex commands into HTML commands.

	Parameters:
		text: the string to be processed

	Output:
		the processed string
	"""
	for tex, html in latex2Html_commands:
		match = re.compile('\\\\%s\{(.*| |\n)?\}'%tex, re.MULTILINE)
		for t in match.finditer(text):
			text = text.replace(t.group(), "<{html}>{cont}</{html}>".format(html = html, cont = t.group(1)))
	for tex, html in latex2Html_strings:
		text = text.replace(tex, html)
	for tex, new in latex_replace:
		match = re.compile('\\\\%s\{(.*| |\n)?\}'%tex, re.MULTILINE)
		for t in match.finditer(text):
			text = text.replace(t.group(), "\\%s{%s}"%(new, t.group(1)))
	return text