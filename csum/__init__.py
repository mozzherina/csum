from pathlib import Path
from decouple import config

API_PORT = int(config('API_PORT'))
LANGUAGE = config('LANGUAGE')
LABEL_NAME = config('LABEL_NAME')
ANCESTOR_NAME = config('ANCESTOR_NAME')
PROPERTY_NAME = config('PROPERTY_NAME')
SUBCLASS_STROKE = int(config('SUBCLASS_STROKE'))
RDFTYPE_STROKE = int(config('RDFTYPE_STROKE'))
EXCLUDED_PREFIX = str(config('EXCLUDED_PREFIX')).split(',')

WORK_DIR = Path(__file__).parent
DATA_DIR = str(WORK_DIR.parent / 'data')
LOG_FILE = str(WORK_DIR / 'csum.log')
