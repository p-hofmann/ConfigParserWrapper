__author__ = 'Peter Hofmann'
__version__ = '0.1.0'

import os
from io import StringIO
from ConfigParser import SafeConfigParser
from scripts.loggingwrapper import DefaultLogging


class ConfigParserWrapper(DefaultLogging):
	_boolean_states = {
		'yes': True, 'true': True, 'on': True,
		'no': False, 'false': False, 'off': False,
		'y': True, 't': True, 'n': False, 'f': False}

	_label = "ConfigParserWrapper"

	def __init__(self, config_file, logfile=None, verbose=True):
		"""
			Wrapper for the SafeConfigParser class for easy use.

			@attention: config_file argument may be file path or stream.

			@param config_file: file handler or file path to a config file
			@type config_file: file | FileIO | StringIO
			@param logfile: file handler or file path to a log file
			@type logfile: file | FileIO | StringIO | None
			@param verbose: No stdout or stderr messages. Warnings and errors will be only logged to a file, if one is given
			@type verbose: bool

			@return: None
			@rtype: None
		"""
		assert isinstance(config_file, str) or self.is_stream(config_file)
		assert logfile is None or isinstance(logfile, str) or self.is_stream(logfile)

		super(ConfigParserWrapper, self).__init__(logfile=logfile, verbose=verbose)
		self._config = SafeConfigParser()

		if isinstance(config_file, str) and not os.path.isfile(config_file):
			self._logger.error("Config file does not exist: '{}'".format(config_file))
			raise Exception("File does not exist")

		if isinstance(config_file, str):
			self._config.read(config_file)
			self._config_file_path = config_file
		elif self.is_stream(config_file):
			self._config.readfp(config_file)
			self._config_file_path = config_file.name
		else:
			self._logger.error("Invalid config file argument '{}'".format(config_file))
			raise Exception("Unknown argument")

	def validate_sections(self, list_sections):
		"""
			Validate a list of section names for availability.

			@param list_sections: list of section names
			@type list_sections: list of str

			@return: None if all valid, otherwise list of invalid sections
			@rtype: None | list[str]
		"""
		assert isinstance(list_sections, list)
		invalid_sections = []
		for section in list_sections:
			if not self._config.has_section(section):
				invalid_sections.append(section)
		if len(invalid_sections) > 0:
			return invalid_sections
		return None

	def log_invalid_sections(self, list_sections):
		"""
			print out a list of invalid section names to log.

			@param list_sections: list of section names
			@type list_sections: list[str]

			@return: None
			@rtype: None
		"""
		assert isinstance(list_sections, list)
		for section in list_sections:
			self._logger.warning("Invalid section '{}'".format(section))

	def get_value(self, option, section=None, is_digit=False, is_boolean=False, is_path=False, silent=False):
		"""
			get a value of an option in a specific section of the config file.

			@attention: Set obligatory to False if a section or option that does not exist is no error.

			@param option: name of option in a section
			@type option: str
			@param section: name of section
			@type section: str
			@param is_digit: value is a number and will be returned as such
			@type is_digit: bool
			@param is_boolean: value is bool and will be returned as True or False
			@type is_boolean: bool
			@param is_path: value is a path and will be returned as absolute path
			@type is_path: bool
			@param silent: Error is given if error not available unless True
			@type silent: bool


			@return: None if not available or ''. Else: depends on given arguments
			@rtype: None | str | int | float | bool
		"""
		assert section is None or isinstance(section, str)
		assert isinstance(option, str)
		assert isinstance(is_digit, bool)
		assert isinstance(is_boolean, bool)
		assert isinstance(silent, bool)
		assert isinstance(is_path, bool)
		if section is None:
			section = self._get_section_of_option(option)
		if not self._config.has_section(section):
			if not silent:
				self._logger.error("Missing section '{}'".format(section))
			return None
		if not self._config.has_option(section, option):
			if not silent:
				self._logger.error("Missing option '{}' in section '{}'".format(option, section))
			return None

		value = self._config.get(section, option)
		if value == '':
			if not silent:
				self._logger.warning("Empty value in '{}': '{}'".format(section, option))
			return None

		if is_digit:
			return self._string_to_digit(value)

		if is_boolean:
			return self._is_true(value)

		if is_path:
			return self._get_full_path(value)
		return value

	def _get_section_of_option(self, option):
		"""
			get the section of a unique option

			@param option: name of option in a section
			@type option: str

			@return: Section name. None if not available
			@rtype: None | str
		"""
		assert isinstance(option, str)
		for section in self._config.sections():
			if self._config.has_option(section, option):
				return section
		return None

	def search_sections_of(self, option):
		"""
			get the section of a unique option

			@param option: name of option in a section
			@type option: str

			@return: Section name. None if not available
			@rtype: set[str]
		"""
		assert isinstance(option, str)
		result = set()
		for section in self._config.sections():
			if self._config.has_option(section, option):
				return result.add(section)
		return result

	def _string_to_digit(self, value):
		"""
			parse string to an int or float.

			@param value: some string to be converted
			@type value: str

			@return: None if invalid, otherwise int or float
			@rtype: None | int | float
		"""
		assert isinstance(value, str)
		try:
			if '.' in value:
				return float(value)
			return int(value)
		except ValueError:
			self._logger.error("Invalid digit value '{}'".format(value))
			return None

	def _is_true(self, value):
		"""
			parse string to True or False.

			@param value: some string to be converted
			@type value: str

			@return: None if invalid, otherwise True or False
			@rtype: None | bool
		"""
		assert isinstance(value, str)

		if value.lower() not in ConfigParserWrapper._boolean_states:
			self._logger.error("Invalid bool value '{}'".format(value))
			return None
		return ConfigParserWrapper._boolean_states[value.lower()]

	@staticmethod
	def _get_full_path(value):
		"""
			convert string to absolute normpath.

			@param value: some string to be converted
			@type value: str

			@return: absolute normpath
			@rtype: str
		"""
		assert isinstance(value, str)

		parent_directory, filename = os.path.split(value)

		if not parent_directory and not os.path.isfile(value):
			for path in os.environ["PATH"].split(os.pathsep):
				path = path.strip('"')
				exe_file = os.path.join(path, filename)
				if os.path.isfile(exe_file):
					value = exe_file
					break

		value = os.path.expanduser(value)
		value = os.path.normpath(value)
		value = os.path.abspath(value)
		return value
