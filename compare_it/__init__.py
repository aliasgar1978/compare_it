__doc__ = '''Compare IT Utility'''

__all__ = [ "CompareText", "CompareExcelData" ]

__version__ = "0.0.5"

from .diff import CompareText, CompareExcelData, get_string_diffs