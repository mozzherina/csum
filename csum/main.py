import uvicorn
import logging
import sys

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.encoders import jsonable_encoder
from starlette.middleware.cors import CORSMiddleware

from csum import API_PORT, LOG_FILE
from csum.raplicator import RApplicator
from csum.graph import Graph


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
rules_applicator = RApplicator(logger)
graph = Graph(logger)

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
    graph.load_data(data.file)
    return {'status': 'success'} if graph.data else {'status': 'failure'}


@app.post('/visualize', response_class=FileResponse)
async def visualize():
    if not graph.data:
        logger.warning('No data for visualization. Use /load_data first')
        raise HTTPException(
            status_code=428,
            detail='No data loaded'
        )
    return graph.visualize()


@app.post('/apply_r1', response_class=JSONResponse)
async def apply_r1():
    if not graph.data:
        logger.warning('No data for processing. Use /load_data first')
        raise HTTPException(
            status_code=428,
            detail='No data loaded'
        )
    rules_applicator.apply_r1(graph)
    return JSONResponse(content=graph.to_json())
    # return graph.to_json()


if __name__ == "__main__":
    uvicorn.run(app, port=API_PORT)
