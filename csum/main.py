import uvicorn
import logging
import sys

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from starlette.middleware.cors import CORSMiddleware

from csum import API_PORT, LOG_FILE, SHOW_ORIGIN, EXCLUDED_PREFIX
from csum.meta import MetaGraph


def setup_custom_logger(name):
    formatter = logging.Formatter(fmt='%(levelname)-8s %(asctime)s %(message)s',
                                  datefmt='%Y-%m-5d %H:%M:%S')
    handler = logging.FileHandler(LOG_FILE, mode='w+')
    handler.setFormatter(formatter)
    screen_handler = logging.StreamHandler(stream=sys.stdout)
    screen_handler.setFormatter(formatter)
    _logger = logging.getLogger(name)
    _logger.setLevel(logging.INFO)
    _logger.addHandler(handler)
    _logger.addHandler(screen_handler)
    return _logger


logger = setup_custom_logger('csum')
graph = MetaGraph(logger)

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


@app.put('/load_data', response_class=JSONResponse)
async def load_data(original: bool = SHOW_ORIGIN,
                    excluded: str = None,
                    data: UploadFile = File(...)):
    excluded = excluded.split(',') if excluded else EXCLUDED_PREFIX
    if graph.load_data(data.file, original, excluded):
        graph_json = graph.visualize()
        if graph_json:
            return JSONResponse(content=graph_json)
    return JSONResponse(content={'Error': 'Not able to parse the graph'},
                        status_code=400)


def apply_meta(function_name):
    if not graph.data:
        logger.warning('No data for processing. Use /load_data first')
        raise HTTPException(status_code=428, detail='No data loaded')
    graph_json = function_name()
    if graph_json:
        return JSONResponse(content=graph_json)
    return JSONResponse(content={'Error': 'Not able to parse the graph'},
                        status_code=400)


@app.post('/plus', response_class=JSONResponse)
async def plus():
    return apply_meta(graph.plus)


@app.post('/minus', response_class=JSONResponse)
async def minus():
    return apply_meta(graph.minus)

"""
@app.post('/unfold', response_class=JSONResponse)
async def unfold():
    return
"""

if __name__ == "__main__":
    uvicorn.run(app, port=API_PORT, host='0.0.0.0')
