from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from app.api.routes import router

app = FastAPI(
    title='Local OCR Image-PDF Service',
    version='0.2.0',
    description='Local-first OCR service. Final output PDF is rebuilt from raster page images only and verified to contain zero embedded text.'
)


@app.get('/', include_in_schema=False)
def root():
    return RedirectResponse(url='/docs')


app.include_router(router)
