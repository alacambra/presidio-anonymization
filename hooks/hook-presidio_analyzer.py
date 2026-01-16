"""PyInstaller hook for presidio_analyzer - collect data files."""
from PyInstaller.utils.hooks import collect_data_files

datas = collect_data_files('presidio_analyzer', subdir='conf')
