# -----------------------------------------------------------------------------
# IMPORTS
# -----------------------------------------------------------------------------
from collections import OrderedDict
import pandas as pd
import os

from abc import ABC, abstractclassmethod
from nettoolkit import Juniper, STR, DIC, DifferenceDict



# ----------------------------------------------------------------------------------
# Text Config Comparisions
# ----------------------------------------------------------------------------------
def get_string_diffs(difference_dict, hn="", difference_dict_labels=None):	
	"""converts dictionary to string representation

	Args:
		difference_dict (dict): nested dictionary
		hn (str, optional): hostname for heading if any. Defaults to "".
		difference_dict_labels (dict, optional): top level key labels if want to print. Defaults to None.

	Returns:
		str: string representation of nested dictionary
	"""	
	s = hn + "\n"
	for key, value in difference_dict.items():
		if value == '': continue
		if (difference_dict_labels and 
			difference_dict_labels.get(key) and 
			isinstance(difference_dict_labels[key], str)):
			s += difference_dict_labels[key] + "\n"
		s += key + "\n"
		s += DIC.recursive_dic(value, 1)
	return s

class CompareText():
	"""Class to start comparing for two configs
	readfiles-> convert to lists, -> detects device/config tpyes, ->
	run appropriate comparetext object.
	change_type: str: either add/del (+, -)
	"""

	def __init__(self, file1, file2, change_type=''):
		"""Initialize Text Comparision object

		Args:
			file1 (str): file name of first file
			file2 (str): file name o second file
			change_type (str, optional): change type (Removals="- "; Adds="+ "). Defaults to ''.
		"""    		
		self.file1, self.file2 = file1.strip(), file2.strip()
		with open(self.file1, 'r') as f: lst1 = f.readlines()
		with open(self.file2, 'r') as f: lst2 = f.readlines()
		self.lst1, self.lst2 = lst1, lst2
		self.change_type = change_type
		self.detected_dev_types = {0:{'dev_type':'', 'config_type':''}, 1:{'dev_type':'', 'config_type':''}}
		self.detect_types()
		self.get_ct_object()

	def get_ct_object(self):
		"""Compare Text Object based on detected config device"""
		self.CTObj = None
		if self.is_cfg_match():
			kwargs = {'file1': self.file1 , 
				'file2': self.file2, 
				'config_type': self.cfg[0]['config_type'], 
				'change_type': self.change_type, 
				}
			# print(self.cfg[1]['dev_type'])
			if self.cfg[0]['dev_type'] == "Cisco":
				self.CTObj = Compare_Text_Cisco(**kwargs)
			elif self.cfg[0]['dev_type'] == "Juniper":
				self.CTObj = Compare_Text_Juniper(**kwargs)
			else:
				raise Exception("NotImplementedError")
		else:
			raise Exception(f"ConfigMismatchError - \nconfig0:\n{self.cfg[0]} \nconfig1\n{self.cfg[1]}")
		return self.CTObj

	@property
	def cfg(self): 
		"""gets configuration typpe

		Returns:
			str: device type
		"""		
		return self.detected_dev_types
	@cfg.setter
	def cfg(self, devconf): 
		"""sets configuration type

		Args:
			devconf (tuple):  should include (lineindex, dev_type, config_type) 
		"""		
		self.detected_dev_types[devconf[0]]['dev_type'] = devconf[1]
		self.detected_dev_types[devconf[0]]['config_type'] = devconf[2]

	def is_cfg_match(self):
		"""Boolean value for if configuration matched"""
		self.cfg_matched = True
		for k, v in self.cfg[0].items():
			if v != self.cfg[1][k]: 
				self.cfg_matched = False
				break
		return self.cfg_matched

	def detect_types(self):
		"""Detects Device and config Types for provided config files"""
		for i, lst in enumerate((self.lst1, self.lst2)):
			for line in lst:
				if STR.is_blank_line(line): continue
				if STR.ending(line, ";"): 
					self.cfg = i, 'Juniper', 'Expanded'
					break
				if STR.starting(line, "set"): 
					self.cfg = i, 'Juniper', 'Set'
					break
				if STR.starting(line, 'hostname') or STR.starting(line, 'host-nam'):
					self.cfg = i, 'Cisco', 'Expanded'
					break

class Compare_Text_Papa(ABC):
	"""Parent class defining common methods for various vendors """

	def __init__(self, file1, file2, config_type, change_type):
		"""Initialize Parent object for various types of configuarations

		Args:
			file1 (str): file name for input file 1
			file2 (str): file name for input file 2
			config_type (str): configuration type
			change_type (str): add/del ("+ ", "- ")
		"""    		
		self.change_type = change_type
		self.config_type = config_type
		self.serialize_files(file1, file2)
		self.get_diff(self.serialized_config[0], self.serialized_config[1])

	@abstractclassmethod
	def serialize_files(self, file1, file2): pass

	@property
	def differences(self): return self.diff


class Compare_Text_Cisco(Compare_Text_Papa):    	
	"""Cisco type text configuration compare """

	def serialize_files(self, file1, file2):
		"""convert files to linear format

		Args:
			file1 (str): file name for input file 1
			file2 (str): file name for input file 2
		"""    		
		self.files = {0:file1, 1:file2}
		self.serialized_config = {}
		for i, file in self.files.items():
			with open(file, 'r') as f:
				self.serialized_config[i] = CiscoHierarchy(f, 0, "")

	def get_diff(self, conf0, conf1):
		"""Generate differences between two configs 

		Args:
			conf0 (list): serialized config 1
			conf1 (list): serialized config 2
		"""    		
		dd1 = DifferenceDict(self.serialized_config[0].config)
		dd2 = DifferenceDict(self.serialized_config[1].config)
		if self.change_type == "- ":
			self.diff = dd1 - dd2
		elif self.change_type == "+ ":
			self.diff = dd1 + dd2
		# print(self.diff)


class Compare_Text_Juniper(Compare_Text_Papa):
	"""Juniper style text configuration compare """

	def serialize_files(self, file1, file2):
		"""convert files to linear format (if need)

		Args:
			file1 (str): file name for input file 1
			file2 (str): file name for input file 2
		"""    		
		self.serialized_config = {}
		if self.config_type != 'Set':
			for i, file in enumerate((file1, file2)):
				self.serialized_config[i] = self.to_set(file)
		else:
			self.serialized_config[0], self.serialized_config[1] = file1, file2

	def to_set(self, file):
		"""Convert files to JSET format if not done /child"""
		j = Juniper(file)
		return j.convert_to_set(to_file=False)

	def check_diff(self, dst_config, sectLine):
		"""check line difference in destined config 

		Args:
			dst_config (list): destination config
			sectLine (str, tuple. list):  to check within destination config
		"""    		
		if isinstance(sectLine, str):
			if sectLine not in dst_config:
				self.diff[self.change_type + sectLine] = ''
		elif isinstance(sectLine, (tuple,list)):
			for item in sectLine:
				self.check_diff(dst_config, item)

	def get_diff(self, conf0, conf1):
		"""Generate differences between two configs 

		Args:
			conf0 (list): serialized config 1
			conf1 (list): serialized config 2
		"""  
		self.diff = {}
		for sectLine in conf0:
			self.check_diff(conf1, sectLine)

class CiscoHierarchy(dict):
	"""Convert Cisco Normal Configuration to a Hierarchical model"""

	def __init__(self, f, indention, sect_pfx):
		"""Initialize object

		Args:
			f (str): file name of config file
			indention (str, int): indenting level of config
			sect_pfx (str, None): previous section name/prefix
		"""    		
		self.f = f
		self.indention = indention
		self.sect_pfx = sect_pfx
		self.dic = OrderedDict()
		# self.dic = {}
		self.prev_line = sect_pfx
		self.carry_over_line = ''
		self.section_conf()

	@property
	def config(self): return self.dic

	def mask_passwords(self, line):
		"""Masking of passwords on line
		valid pw characters defined are:  {" password ", " key ", " secret ", " authentication-key "}

		Args:
			line (str): config line

		Returns:
			str: updated line after masking pw if any
		"""    		
		pw_chars = {" password ", " key ", " secret ", " authentication-key "}
		for pw_char in pw_chars:
			pos = STR.foundPos(line, pw_char)
			if pos > 0: line = line[:pos].rstrip() + pw_char + "XXXXXXXX"
			return line

	def remarked_lines(self, line):
		"""checks if line is a remark or not and return boolean accordingly.

		Args:
			line (str): config line

		Returns:
			bool: if remark line, else previos line
		"""    		
		rem_line = line.lstrip().startswith("!")
		if rem_line: self.prev_line = self.sect_pfx
		return rem_line

	def exceptional_lines_maps(self, line):
		"""Some of Cisco commands are not following standard hierarchy or indention those are defined here.
		such lines will be identified and returned with modified line
		currently identified non-standard indentions are as below
		exc_maps = { ' auto qos ': 'auto qos ',}

		Args:
			line (str): input line

		Returns:
			str: modified line per map
		"""    		
		exc_maps = {
			' auto qos ': 'auto qos ',
		}
		return exc_maps[line] if exc_maps.get(line) else line

	def trailing_remarks_update(self, line):
		"""Some of cisco config contains trailing remoarks, such remarks will be removed before processing.

		Args:
			line (str): line string

		Returns:
			str: updated line after removing remark
		"""    		
		pos = STR.foundPos(line, "!")
		if pos > 0: line = line[:pos].rstrip()
		return line

	def add_line_to_dict(self, line): 
		"""adds line to self dictionary

		Args:
			line (str): config line
		"""		
		self.dic[line] = ""

	def indented_block(self, line_indention, line):
		"""process of indented block ahead

		Args:
			line_indention (int): indention of line
			line (str): line string
		"""    		
		sc = CiscoHierarchy(self.f, indention=line_indention, sect_pfx=line)
		# print(sc.prev_line)
		self.dic[self.prev_line] = {line: ''}
		self.dic[self.prev_line].update(sc.dic)

	def descent_block(self, line_indention, line):
		"""Descented from indention occur

		Args:
			line_indention (int): indention of line
			line (str): line string
		"""    		
		if self.indention_diff < -1:
			self.indention -= 1
		else:
			self.carry_over_line = line
		self.f.seek(self.prev_pos)

	def section_conf(self, test=False):
		"""section configuration to be serialzed

		Args:
			test (bool, optional): for test purpose only. Defaults to False.
		"""    		
		while True:
			self.prev_pos = self.f.tell()
			if self.prev_pos == os.fstat(self.f.fileno()).st_size: break  # EOF
			line = self.f.readline()
			if STR.is_blank_line(line): continue
			if self.remarked_lines(line): continue
			line = self.trailing_remarks_update(line)
			line = self.mask_passwords(line)
			line = line.rstrip()
			line = self.exceptional_lines_maps(line)
			line_indention = STR.indention(line)
			self.indention_diff = line_indention - self.indention

			if self.indention_diff == 0 : 
				self.add_line_to_dict(line)
			elif self.indention_diff > 0:
				self.indented_block(line_indention, line)
			elif self.indention_diff < 0 :
				self.descent_block(line_indention, line)
				break

			self.prev_line = line


class CompareExcelData():
	"""Two Excel comparisions engine
	"""    	

	def __init__(self, file1, file2, sheet_name, change_type):
		"""Initialize object by providing necessary inputs

		Args:
			file1 (str): First excel file name
			file2 (str): Second excel file name
			sheet_name (str): sheet/tab name from both files (should be same)
			change_type (str): Add/Del ("+ ", "- ")
		"""    		
		self.file1, self.file2, self.sheet_name = file1, file2, sheet_name
		self.change_type = change_type

	def diff(self, idx):
		"""differences

		Args:
			idx (index): str

		Returns:
			dict: difference of index
		"""    		
		self.get_df(idx)
		self.conv_df_to_dict()
		self.get_dict_diffs()
		return self._diff

	def get_df(self, idx):
		"""get the DataFrame by setting index column

		Args:
			idx (str): index column name
		"""    		
		self.df1 = pd.read_excel(self.file1, sheet_name=self.sheet_name, index=False).fillna("")
		self.df2 = pd.read_excel(self.file2, sheet_name=self.sheet_name, index=False).fillna("")
		# index_col = "FIND" if self.sheet_name == 'var' else "Unnamed: 0"
		self.df1 = self.df1.set_index(idx)
		self.df2 = self.df2.set_index(idx)

	def conv_df_to_dict(self):
		"""Converts DataFrame to Dictionary
		"""    		
		self.td1 = self.df1.to_dict()
		self.td2 = self.df2.to_dict()

	def get_dict_diffs(self):
		"""Execute for Dictionary differences
		stores difference within object
		"""    		
		dd1 = DifferenceDict(self.td1)
		dd2 = DifferenceDict(self.td2)
		if self.change_type == "- ":
			self._diff = dd1 - dd2
		elif self.change_type == "+ ":
			self._diff = dd2 + dd1


