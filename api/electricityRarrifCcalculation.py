import asyncio
from concurrent.futures import ProcessPoolExecutor
import json
from fastapi import APIRouter, HTTPException
from config.logger import logger
from model.models import BatchTariffCalculationRequest, BatchTariffResponse, EvaluateResponse, TariffCalculationRequest, TariffEvaluationFailure, TariffEvaluationSuccess
from zen import ZenEngine

energyTariffCalculatorRouter = APIRouter()
executor = ProcessPoolExecutor(max_workers=8)

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

# ----------------------------
# Chunk helper
# ----------------------------

def chunk_list(data, size):
    for i in range(0, len(data), size):
        yield data[i:i + size]


# ----------------------------
# Chunk processor (runs in parallel)
# ----------------------------

async def process_chunk(chunk, decision):
    success = []
    failure = []

    for req_item in chunk:
        ctx = req_item.dict()
        try:
            res = decision.evaluate(ctx)
            success.append(TariffEvaluationSuccess(result=res))
        except Exception as e:
            failure.append(
                TariffEvaluationFailure(context=ctx, error=str(e))
            )

    return success, failure


# ----------------------------
# FINAL PARALLEL BATCH API
# ----------------------------

@energyTariffCalculatorRouter.post("/evaluate/batch/parallel")
async def evaluateTariffBatchparallel(req: BatchTariffCalculationRequest):

    logger.info(f"Batch tariff evaluation invoked, count={len(req.requests)}")

    # Load Zen rules
    try:
        with open("rules/energy_tariff_calculation.json") as f:
            model = json.load(f)
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="Rules file missing")

    # Initialize decision engine once
    engine = ZenEngine()
    decision = engine.create_decision(model)

    # Create chunks (e.g., 500 each)
    CHUNK_SIZE = 500  # adjust according to CPU/RAM
    chunks = list(chunk_list(req.requests, CHUNK_SIZE))

    logger.info(f"Total chunks: {len(chunks)}")

    # Run chunks in parallel
    tasks = [process_chunk(chunk, decision) for chunk in chunks]

    results = await asyncio.gather(*tasks)

    # Flatten results
    success_results = []
    failed_results = []

    for s, f in results:
        success_results.extend(s)
        failed_results.extend(f)

    return {
        "summary": {
            "total_requests": len(req.requests),
            "chunks_processed": len(chunks),
            "succeeded": len(success_results),
            "failed": len(failed_results),
        },
        "success": success_results,
        "failed": failed_results,
    }

def evaluate_single(decision_model, context):
    engine = ZenEngine()
    decision = engine.create_decision(decision_model)
    return decision.evaluate(context)

@energyTariffCalculatorRouter.post("/evaluate/batch/parallel/v2")
async def evaluateTariffBatchParallel(req: BatchTariffCalculationRequest):

    with open("rules/energy_tariff_calculation.json") as f:
        model = json.load(f)

    loop = asyncio.get_event_loop()

    tasks = [
        loop.run_in_executor(
            executor,
            evaluate_single,
            model,
            item.dict()
        )
        for item in req.requests
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    success = []
    failed = []

    for ctx, r in zip(req.requests, results):
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
            "total_requests": len(req.requests),
            "succeeded": len(success),
            "failed": len(failed),
        },
        "success": success,
        "failed": failed,
    }
