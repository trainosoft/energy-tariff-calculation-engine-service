from datetime import timedelta
import json
from typing import Any
import uuid

from fastapi import APIRouter
from optapy import solver_factory_create, solver_manager_create
from optapy.types import Duration, SolverConfig
from starlette.responses import JSONResponse
from config.logger import logger
from opta.models.TimeTableProblemDTO import TimeTableDTO
from opta.schooltimetabling.constraints import define_constraints

from opta.schooltimetabling.domain import (
    Lesson,
    Room,
    TimeTable,
    Timeslot,
    generate_problem,
)

schoolTimetableRosteringRouter = APIRouter()

solver_config = SolverConfig().withEntityClasses(Lesson) \
    .withSolutionClass(TimeTable) \
    .withConstraintProviderClass(define_constraints) \
    .withTerminationSpentLimit(Duration.ofSeconds(30))

solver = solver_factory_create(solver_config).buildSolver()
solver_manager = solver_manager_create(solver_config)

SOLUTIONS = {}
SOLVER_STATUS = {}

@schoolTimetableRosteringRouter.post("/solve")
async def resolveSchoolTimeTableRostering(timeTableDTO: TimeTableDTO):
    logger.info("resolveSchoolTimeTableRostering invoked")

    #problem_id = str(uuid.uuid4())
    #logger.info(f"Problem id : {problem_id}")

    timeslot_map = {ts.id: Timeslot(ts.id, ts.day_of_week, ts.start_time, ts.end_time)
                    for ts in timeTableDTO.timeslot_list}
 
    logger.info("Timeslot map: %s", timeslot_map)
    room_map = {r.id: Room(r.id, r.name)
                for r in timeTableDTO.room_list}
 
    logger.info("Room map: %s", room_map)
 
    lesson_list = []
    for l in timeTableDTO.lesson_list:
        lesson = Lesson(
            l.id,
            l.subject,
            l.teacher,
            l.student_group,
            timeslot_map.get(l.timeslot),
            room_map.get(l.room)
        )
        lesson_list.append(lesson)
   
    logger.info("Lesson list: %s", lesson_list)
 
    problem = TimeTable(
        list(timeslot_map.values()),
        list(room_map.values()),
        lesson_list
    )

    #problem = generate_problem()
    logger.info("Problem generated: %s", json.dump(problem))
    solution = solver.solve(problem)
    logger.info("Solution found: %s", solution)

    return {
        "solution": solution,
        "status": "Completed"
    }
    

@schoolTimetableRosteringRouter.post("/solve/async")
async def resolveSchoolTimeTableRostering_async(timeTableDTO: TimeTableDTO):
    logger.info("resolveSchoolTimeTableRostering_async invoked")

    # --- Prepare problem ---
    timeslot_map = {ts.id: Timeslot(ts.id, ts.day_of_week, ts.start_time, ts.end_time)
                    for ts in timeTableDTO.timeslot_list}
    room_map = {r.id: Room(r.id, r.name) for r in timeTableDTO.room_list}

    lesson_list = []
    for l in timeTableDTO.lesson_list:
        lesson = Lesson(
            l.id,
            l.subject,
            l.teacher,
            l.student_group,
            timeslot_map.get(l.timeslot.id) if l.timeslot else None,
            room_map.get(l.room.id) if l.room else None
        )
        lesson_list.append(lesson)

    problem = TimeTable(
        list(timeslot_map.values()),
        list(room_map.values()),
        lesson_list
    )

    problem_id = str(uuid.uuid4())
    logger.info(f"Problem submitted: {problem_id}")

    # --- Callback to receive best solutions ---
    def on_solution(best_solution):
        logger.info(f"Intermediate solution received for {problem_id}")
        logger.info(f"best_solution : {best_solution}")
        SOLUTIONS[problem_id] = timetable_to_dict(best_solution)

    # --- Submit problem to SolverManager ---
    solver_manager.solveAndListen(problem_id, lambda pid: problem, on_solution)
    solver_status = solver_manager.getSolverStatus(problem_id)
    # --- Return problem ID immediately ---
    return JSONResponse(content={"problem_id": problem_id, "status": solver_status.toString()})


@schoolTimetableRosteringRouter.get("/solve/status/{problem_id}")
async def get_solver_status(problem_id: str):

    status = solver_manager.getSolverStatus(problem_id)
    status_str = status.toString() if status else "NOT_FOUND"
    SOLVER_STATUS[problem_id] = status_str

    # If we have intermediate or final solution stored
    solution_dict = SOLUTIONS.get(problem_id)

    return {
        "problem_id": problem_id,
        "status": status_str,
        "solution": solution_dict  # May be None if solver still running
    }

@schoolTimetableRosteringRouter.get("/solution/{problem_id}")
async def get_solution(problem_id: str):
    solution = SOLUTIONS.get(problem_id)
    logger.info(f"future : {solution}")
    if not solution:
        return JSONResponse({"solution": None, "status": "NOT_FOUND"})

    if solution:
        return JSONResponse({"solution": solution, "status": "COMPLETED"})
    else:
        return JSONResponse({"solution": None, "status": "SOLVING"})

# --- Serializer function ---
def timetable_to_dict(solution):
    return {
        "timeslot_list": [
            {
                "id": t.id,
                "day_of_week": t.day_of_week,
                "start_time": str(t.start_time),
                "end_time": str(t.end_time)
            } for t in solution.timeslot_list
        ],
        "room_list": [
            {
                "id": r.id,
                "name": r.name
            } for r in solution.room_list
        ],
        "lesson_list": [
            {
                "id": l.id,
                "subject": l.subject,
                "teacher": l.teacher,
                "student_group": l.student_group,
                "timeslot": {
                    "id": l.timeslot.id,
                    "day_of_week": l.timeslot.day_of_week,
                    "start_time": str(l.timeslot.start_time),
                    "end_time": str(l.timeslot.end_time)
                } if l.timeslot else None,
                "room": {
                    "id": l.room.id,
                    "name": l.room.name
                } if l.room else None
            } for l in solution.lesson_list
        ],
        "score": str(solution.score)
    }








