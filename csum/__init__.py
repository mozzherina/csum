from pathlib import Path
from decouple import config

API_PORT = int(config('API_PORT'))

LANGUAGE = config('LANGUAGE')
LABEL_NAME = config('LABEL_NAME')
ANCESTOR_NAME = config('ANCESTOR_NAME')
PROPERTY_NAME = config('PROPERTY_NAME')
EXCLUDED_PREFIX = str(config('EXCLUDED_PREFIX')).split(',')
SHOW_ORIGIN = config('SHOW_ORIGIN') == 'True'

STROKE_SUBCLASS = int(config('STROKE_SUBCLASS'))
STROKE_RDFTYPE = int(config('STROKE_RDFTYPE'))
COLOUR_BASIC = config('COLOUR_BASIC')
COLOUR_ENDURANT1 = config('COLOUR_ENDURANT1')
COLOUR_ENDURANT2 = config('COLOUR_ENDURANT2')
COLOUR_RELATOR = config('COLOUR_RELATOR')
COLOUR_PREFIX1 = config('COLOUR_PREFIX1')
COLOUR_PREFIX2 = config('COLOUR_PREFIX2')


WORK_DIR = Path(__file__).parent
DATA_DIR = str(WORK_DIR.parent / 'data')
LOG_FILE = str(WORK_DIR / 'csum.log')
