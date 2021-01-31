import os

from redbot.core import data_manager
from tsutils import safe_read_json


def _data_file(file_name: str) -> str:
    return os.path.join(str(data_manager.cog_data_path(raw_name='padinfo')), file_name)


historic_lookups_file_path = _data_file('historic_lookups.json')
historic_lookups = safe_read_json(historic_lookups_file_path)

historic_lookups_file_path_id3 = _data_file('historic_lookups_id3.json')
historic_lookups_id3 = safe_read_json(historic_lookups_file_path_id3)
