# pylint: disable=import-error
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from app.endpoints import app as endpoints_app

app = FastAPI()


@app.get("/", name="home", description="get home HTML")
async def home():
    with open("./index.html", "rb") as file:
        return HTMLResponse(file.read())


app.mount("/assets/", StaticFiles(directory="assets"), name="assets")

app.mount("/", endpoints_app, name="api")
