import uvicorn
from app.core.config import LOCAL_HOST, LOCAL_PORT

if __name__ == '__main__':
    uvicorn.run('app.main:app', host=LOCAL_HOST, port=LOCAL_PORT, reload=False)
