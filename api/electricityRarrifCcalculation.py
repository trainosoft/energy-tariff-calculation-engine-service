import asyncio
from concurrent.futures import ProcessPoolExecutor
import json
from typing import Any
from fastapi import APIRouter, HTTPException, Request, Body
from config.logger import logger
from model.models import TariffEvaluationFailure, TariffEvaluationSuccess
from zen import ZenEngine

energyTariffCalculatorRouter = APIRouter()
executor = ProcessPoolExecutor(max_workers=8)

@energyTariffCalculatorRouter.post("/evaluate")
async def evaluateTarrifCalcaulationRules(request: Request, decision_table_key: str | None = None):
    context = await request.json()
    logger.info("evaluateTarrifCalcaulationRules invoked, req: %s", context)

    try:
        with open("rules/"+decision_table_key) as f:
            model = json.load(f)
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="Rules file not found")

    try:
        engine = ZenEngine()
        decision = engine.create_decision(model)

        result = decision.evaluate(context)
        logger.info(f"Tariff calculation result: {result}")
        return result

    except Exception as e:
        logger.exception("Error evaluating tariff rules")
        raise HTTPException(status_code=500, detail=str(e))


def evaluate_single(decision_model, context):
    engine = ZenEngine()
    decision = engine.create_decision(decision_model)
    return decision.evaluate(context)



@energyTariffCalculatorRouter.post("/evaluate/batch/parallel/v2")
async def evaluateTariffBatchParallel(payload: Any = Body(...), decision_table_key: str | None = None):
    if not isinstance(payload, list):
        raise HTTPException(
            status_code=400,
            detail="Payload must be an array of request objects"
        )

    try:
        with open("rules/"+decision_table_key) as f:
            model = json.load(f)
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="Rules file not found")

    loop = asyncio.get_event_loop()

    tasks = [
        loop.run_in_executor(
            executor,
            evaluate_single,
            model,
            item
        )
        for item in payload
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    success = []
    failed = []

    for ctx, r in zip(payload, results):
        if isinstance(r, Exception):
            failed.append(
                TariffEvaluationFailure(context=ctx.dict(), error=str(r))
            )
        else:
            success.append(
                TariffEvaluationSuccess(result=r)
            )

    return {
        "summary": {
            "total_requests": len(payload),
            "succeeded": len(success),
            "failed": len(failed),
        },
        "success": success,
        "failed": failed,
    }

