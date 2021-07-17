import uvicorn
import logging
import sys

from fastapi import FastAPI, File, UploadFile
from fastapi.responses import FileResponse
from starlette.middleware.cors import CORSMiddleware

from csum import API_PORT, LOG_FILE, DATA_DIR


def setup_custom_logger(name):
    formatter = logging.Formatter(fmt='%(levelname)-8s %(asctime)s %(message)s',
                                  datefmt='%Y-%m-5d %H:%M:%S')
    handler = logging.FileHandler(LOG_FILE, mode='w')
    handler.setFormatter(formatter)
    screen_handler = logging.StreamHandler(stream=sys.stdout)
    screen_handler.setFormatter(formatter)
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    logger.addHandler(screen_handler)
    return logger


logger = setup_custom_logger('csum')

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*']
)


@app.get('/get_log')
async def get_log():
    return FileResponse(LOG_FILE)


@app.get('/health')
async def health():
    return {'status': 'success'}


@app.put('/load_data')
async def load_data(data: UploadFile = File(...)):
    local_file = open(DATA_DIR + '/' + data.filename, 'wb')
    local_file.write(data.file.read())
    local_file.close()
    return {'status': 'success'}


if __name__ == "__main__":
    uvicorn.run(app, port=API_PORT)
