import uuid

from fastapi.responses import JSONResponse

from config.logger import logger
from fastapi import APIRouter

from optapy.types import Duration
from optapy.types import SolverConfig
from optapy import solver_factory_create, solver_manager_create

from opta.Generic_Solve_API.ProblemMapper import build_school_problem, generate_demo_data
from opta.Generic_Solve_API.constraints import employee_scheduling_constraints
from opta.Generic_Solve_API.domain import EmployeeSchedule, Shift
from opta.Generic_Solve_API.serializer import to_json
from opta.models.TimeTableProblemDTO import SolveRequest
from opta.schooltimetabling.constraints import define_constraints
from opta.schooltimetabling.domain import Lesson, TimeTable
from opta.schooltimetabling.schoolTtimetableRosteringApi import timetable_to_dict



genericSolveRosteringRouter = APIRouter()

SOLVER_REGISTRY = {}

solver_config = SolverConfig().withEntityClasses(Lesson) \
    .withSolutionClass(TimeTable) \
    .withConstraintProviderClass(define_constraints) \
    .withTerminationSpentLimit(Duration.ofSeconds(30))

employee_shift_config = (
    SolverConfig()
        .withEntityClasses(Shift)
        .withSolutionClass(EmployeeSchedule)
        .withConstraintProviderClass(employee_scheduling_constraints)
        .withTerminationSpentLimit(Duration.ofSeconds(30))
)

solver = solver_factory_create(solver_config).buildSolver()
solver_manager = solver_manager_create(solver_config)

SOLVER_REGISTRY["school-timetable"] = {
    "solver": solver_factory_create(solver_config).buildSolver(),
    "mapper": build_school_problem
}

SOLVER_REGISTRY["employee-shift"] = {
    "solver": solver_factory_create(employee_shift_config).buildSolver(),
    "mapper": generate_demo_data
}

SOLUTIONS = {}
SOLVER_STATUS = {}


@genericSolveRosteringRouter.post("/solve")
def solve_problem(request: SolveRequest):

    entry = SOLVER_REGISTRY[request.problemType]
    solver = entry["solver"]
    mapper = entry["mapper"]

    problem = mapper(request.problemData)
    solution = solver.solve(problem)

    return {
        "problemType": request.problemType,
        "status": "COMPLETED",
        "score": str(solution.score),
        "solution": to_json(solution)
    }


