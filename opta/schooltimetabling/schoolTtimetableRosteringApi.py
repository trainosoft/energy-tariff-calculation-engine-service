import uuid
from fastapi import APIRouter
from optapy import solver_factory_create, solver_manager_create
from optapy.types import Duration, SolverConfig
from config.logger import logger
from opta.schooltimetabling.constraints import define_constraints
from opta.schooltimetabling.domain import Lesson, TimeTable, generate_problem
schoolTimetableRosteringRouter = APIRouter()

solver_config = (
    SolverConfig()
        .withSolutionClass(TimeTable)
        .withEntityClasses(Lesson)
        .withConstraintProviderClass(define_constraints)
)

solver_manager = solver_manager_create(solver_config)

@schoolTimetableRosteringRouter.post("/solve")
async def resolveSchoolTimeTableRostering():
    logger.info("resolveSchoolTimeTableRostering invoked")

    problem_id = str(uuid.uuid4())
    logger.info(f"Problem id : {problem_id}")

    problem = generate_problem()
    logger.info("Problem generated: %s", problem)
    #problem_id = start_async_solve(problem, seconds_limit=30)

    solver_config = SolverConfig().withEntityClasses(Lesson) \
    .withSolutionClass(TimeTable) \
    .withConstraintProviderClass(define_constraints) \
    .withTerminationSpentLimit(Duration.ofSeconds(30))

    solver = solver_factory_create(solver_config).buildSolver()

    solution = solver.solve(problem)
    logger.info("Solution found: %s", solution)

    # solution = solver_manager.solve(problem_id, problem)
    # solver_status = solver_manager.getSolverStatus(problem_id)


    return {
        "problemId": problem_id, 
        "solution": solution
    }
    

@schoolTimetableRosteringRouter.post("/solve/async")
async def resolveSchoolTimeTableRostering():
    logger.info("resolveSchoolTimeTableRostering invoked")

    problem_id = str(uuid.uuid4())
    logger.info(f"Problem id : {problem_id}")

    problem = generate_problem()
    logger.info("Problem generated: %s", problem)
 

    solver_manager.solve(problem_id, problem)
    solver_status = solver_manager.getSolverStatus(problem_id)

    logger.info("Solver status: %s", solver_status)

    return {
        "problemId": problem_id, 
        "status": solver_status
    }








