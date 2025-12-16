from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.electricityRarrifCcalculation import energyTariffCalculatorRouter
from config.config import ALLOWED_ORIGINS
from config.logger import logger
from opta.Generic_Solve_API.genericSolveRosteringAPI import genericSolveRosteringRouter
from opta.pollStatusAPI import pollStatusRouter
from opta.schooltimetabling.schoolTtimetableRosteringApi import schoolTimetableRosteringRouter


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("lifespan invoked")

#app = FastAPI(lifespan=lifespan)
app = FastAPI()
@app.middleware("http")
async def log_origin(request, call_next):
    origin = request.headers.get("origin")
    logger.info(f"Request from origin: {origin}")
    logger.info(f"FASTAPI --> {request.method} {request.url.path}")

    return await call_next(request)

# ✅ Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS or ["*"],  # use from config
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(energyTariffCalculatorRouter, prefix="/calculate-tarrif", tags=["Calculate electricity tarrif"])
app.include_router(energyTariffCalculatorRouter, prefix="/calculate-tarrif/batch", tags=["Calculate electricity tarrif batch"])
app.include_router(schoolTimetableRosteringRouter, prefix="/optapy", tags=["Solve school time table rostering"])
app.include_router(pollStatusRouter, prefix="/pullstatus", tags=["Fetch Poll Status"])
app.include_router(genericSolveRosteringRouter, prefix="/optapy-generic", tags=["Solve employee scheduling rostering"])
