"""水声定位仿真系统 — FastAPI 入口"""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import audio, simulation, reserved

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)

app = FastAPI(
    title="水声定位仿真系统 API",
    description="基于 GCC-PHAT 和 Chan 氏算法的声源定位仿真后端",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(audio.router)
app.include_router(simulation.router)
app.include_router(reserved.router)


@app.get("/")
async def root():
    return {"message": "水声定位仿真系统后端运行中", "version": "0.1.0"}
