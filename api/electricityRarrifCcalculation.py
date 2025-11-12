import json
from fastapi import APIRouter, HTTPException
from config.logger import logger
from model.models import TerifCalculationRequest
from zen import ZenEngine

energyTarrifCalculatorRouter = APIRouter()

@energyTarrifCalculatorRouter.post("/evaluate")
async def evaluateTarrifCalcaulationRules(req: TerifCalculationRequest):
    logger.info("evaluateTarrifCalcaulationRules invoked, req: %s", req.json())

    try:
        with open("rules/energy_tariff_calculation.json") as f:
            model = json.load(f)
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="Rules file not found")

    try:
        engine = ZenEngine()
        decision = engine.create_decision(model)

        context = req.dict()

        result = decision.evaluate(context)
        logger.info(f"Tariff calculation result: {result}")
        return result

    except Exception as e:
        logger.exception("Error evaluating tariff rules")
        raise HTTPException(status_code=500, detail=str(e))
