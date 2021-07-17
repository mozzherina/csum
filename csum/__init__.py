from pathlib import Path
from decouple import config

API_PORT = int(config('API_PORT'))
WORK_DIR = Path(__file__).parent
DATA_DIR = str(WORK_DIR.parent / 'data')
LOG_FILE = str(WORK_DIR / 'csum.log')
