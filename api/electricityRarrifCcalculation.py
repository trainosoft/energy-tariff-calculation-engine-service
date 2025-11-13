import json
from fastapi import APIRouter, HTTPException
from config.logger import logger
from model.models import BatchTariffCalculationRequest, BatchTariffResponse, TariffCalculationRequest, TariffEvaluationFailure, TariffEvaluationSuccess
from zen import ZenEngine

energyTariffCalculatorRouter = APIRouter()

@energyTariffCalculatorRouter.post("/evaluate")
async def evaluateTarrifCalcaulationRules(req: TariffCalculationRequest):
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


@energyTariffCalculatorRouter.post("/evaluate/batch")
async def evaluateTariffBatch(req: BatchTariffCalculationRequest):
    logger.info(f"Batch tariff evaluation invoked, count: {len(req.requests)}")

    try:
        with open("rules/energy_tariff_calculation.json") as f:
            model = json.load(f)
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="Rules file not found")

    try:
        engine = ZenEngine()
        decision = engine.create_decision(model)
        logger.info(f"Batch evaluation decision created: {decision}")

        success_results = []
        failed_results = []
        for single_req in req.requests:
            context = single_req.dict()
            try:
                result = decision.evaluate(context)
                success_results.append(
                    TariffEvaluationSuccess(result=result)
                )
            except Exception as e:
                failed_results.append(
                    TariffEvaluationFailure(context=context, error=str(e))
                )
        summary = {
            "total_requests": len(req.requests),
            "succeeded": len(success_results),
            "failed": len(failed_results),
        }

        logger.info(f"Batch completed → {summary}")
        return BatchTariffResponse(
            summary=summary,
            success=success_results,
            failed=failed_results
        )

    except Exception as e:
        logger.exception("Error during batch evaluation")
        raise HTTPException(status_code=500, detail=str(e))
