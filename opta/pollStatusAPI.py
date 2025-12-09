from fastapi import APIRouter
from optapy import solver_manager_create
from optapy.types import Duration, SolverConfig
from config.logger import logger
from opta.schooltimetabling.constraints import define_constraints
from opta.schooltimetabling.domain import Lesson, TimeTable


pollStatusRouter = APIRouter()

solver_config = (
    SolverConfig()
        .withSolutionClass(TimeTable)
        .withEntityClasses(Lesson)
        .withSolutionClass(TimeTable)
        .withConstraintProviderClass(define_constraints)
    )

solver_manager = solver_manager_create(solver_config)


@pollStatusRouter.get("/solve/{problem_id}/status")
async def pollStatus(problem_id: str):
    logger.info(f"Problem id : {problem_id}")

    solver_status = solver_manager.getSolverStatus(problem_id)

    logger.info("Solver status: %s", solver_status)
    return {
        "problemId": problem_id, 
        "status": solver_status.toString(), 
    }