import datetime
import time as pytime
from functools import reduce
from typing import Dict, Any

import requests  # make sure 'requests' is in your requirements.txt
from domain import TimeTable, Lesson, Timeslot, Room, generate_problem  # :contentReference[oaicite:2]{index=2}

# ---------------------------------------------------------------------------
# Placeholder: point this to your FastAPI-based remote solver
# e.g. "http://localhost:8000" or "https://my-solver.example.com"
# ---------------------------------------------------------------------------
REMOTE_SOLVER_BASE_URL = "http://localhost:8000"  # TODO: change this


# ---------------------------------------------------------------------------
# Existing timetable pretty-printer (unchanged from your original main.py)
# ---------------------------------------------------------------------------

def print_timetable(timetable: TimeTable):
    room_list = timetable.room_list
    lesson_list = timetable.lesson_list
    timeslot_room_lesson_triple_list = list(map(
        lambda the_lesson: (the_lesson.timeslot, the_lesson.room, the_lesson),
        filter(lambda the_lesson:
               the_lesson.timeslot is not None and
               the_lesson.room is not None,
               lesson_list)
    ))
    lesson_map = dict()
    for timeslot, room, lesson in timeslot_room_lesson_triple_list:
        if timeslot in lesson_map:
            if room in lesson_map[timeslot]:
                lesson_map[timeslot][room].append(lesson)
            else:
                lesson_map[timeslot][room] = [lesson]
        else:
            lesson_map[timeslot] = {room: [lesson]}

    print("|" + ("------------|" * (len(room_list) + 1)))
    print(reduce(lambda a, b: a + b + " | ",
                 map(lambda the_room: "{:<10}".format(the_room.name)[0:10], room_list),
                 "|            | "))
    print("|" + ("------------|" * (len(room_list) + 1)))
    for timeslot in timetable.timeslot_list:
        cell_list = list(map(lambda the_room: lesson_map.get(timeslot, {}).get(the_room, []),
                             room_list))
        out = "| " + (timeslot.day_of_week[0:3] + " " + str(timeslot.start_time))[0:10] + " | "
        for cell in cell_list:
            if len(cell) == 0:
                out += "           | "
            else:
                out += "{:<10}".format(reduce(lambda a, b: a + "," + b,
                                              map(lambda assigned_lesson: assigned_lesson.subject,
                                                  cell)))[0:10] + " | "
        print(out)
        out = "|            | "
        for cell in cell_list:
            if len(cell) == 0:
                out += "           | "
            else:
                out += "{:<10}".format(reduce(lambda a, b: a + "," + b,
                                              map(lambda assigned_lesson: assigned_lesson.teacher,
                                                  cell)))[0:10] + " | "
        print(out)
        out = "|            | "
        for cell in cell_list:
            if len(cell) == 0:
                out += "           | "
            else:
                out += "{:<10}".format(reduce(lambda a, b: a + "," + b,
                                              map(lambda assigned_lesson: assigned_lesson.student_group,
                                                  cell)))[0:10] + " | "
        print(out)
        print("|" + ("------------|" * (len(room_list) + 1)))
    unassigned_lessons = list(
        filter(lambda unassigned_lesson: unassigned_lesson.timeslot is None or unassigned_lesson.room is None,
               lesson_list))
    if len(unassigned_lessons) > 0:
        print()
        print("Unassigned lessons")
        for lesson in unassigned_lessons:
            print(" " + lesson.subject + " - " + lesson.teacher + " - " + lesson.student_group)


# ---------------------------------------------------------------------------
# JSON <-> domain conversion helpers for the unified solver API
# ---------------------------------------------------------------------------

def timetable_to_json(timetable: TimeTable) -> Dict[str, Any]:
    """
    Convert a TimeTable into the generic JSON 'solution' shape expected by
    your remote FastAPI solver:
      {
        "timeslot_list": [...],
        "room_list": [...],
        "lesson_list": [...]
      }
    with lesson.timeslot / room encoded as timeslot_id / room_id.
    """
    timeslot_list = []
    for ts in timetable.timeslot_list:
        timeslot_list.append({
            "id": ts.id,
            "day_of_week": ts.day_of_week,
            # Use ISO format for times; remote solver should parse these strings
            "start_time": ts.start_time.isoformat(),
            "end_time": ts.end_time.isoformat(),
        })

    room_list = []
    for r in timetable.room_list:
        room_list.append({
            "id": r.id,
            "name": r.name,
        })

    lesson_list = []
    for l in timetable.lesson_list:
        lesson_list.append({
            "id": l.id,
            "subject": l.subject,
            "teacher": l.teacher,
            "student_group": l.student_group,
            "timeslot_id": l.timeslot.id if l.timeslot is not None else None,
            "room_id": l.room.id if l.room is not None else None,
        })

    return {
        "timeslot_list": timeslot_list,
        "room_list": room_list,
        "lesson_list": lesson_list,
    }


def json_to_timetable(solution_json: Dict[str, Any]) -> TimeTable:
    """
    Convert the remote solver's JSON solution back into a TimeTable
    with real Timeslot/Room/Lesson objects.
    """
    # Rebuild timeslots
    timeslot_objs = []
    timeslot_by_id: Dict[int, Timeslot] = {}
    for ts in solution_json.get("timeslot_list", []):
        start_time = datetime.time.fromisoformat(ts["start_time"])
        end_time = datetime.time.fromisoformat(ts["end_time"])
        print(f"start_time : {start_time}")
        print(f"end_time : {end_time}")

        ts_obj = Timeslot(ts["id"], ts["day_of_week"], start_time, end_time)
        timeslot_objs.append(ts_obj)
        print(f"ts_obj : {ts_obj}")
        timeslot_by_id[ts_obj.id] = ts_obj

    # Rebuild rooms
    room_objs = []
    room_by_id: Dict[int, Room] = {}
    for r in solution_json.get("room_list", []):
        print(f"rooms {r}")
        r_obj = Room(r["id"], r["name"])
        print(f"r_obj : {r_obj}")
        room_objs.append(r_obj)
        room_by_id[r_obj.id] = r_obj

    # Rebuild lessons with references
    lesson_objs = []
    for l in solution_json.get("lesson_list", []):
        lesson = Lesson(
            l["id"],
            l["subject"],
            l["teacher"],
            l["student_group"],
            timeslot=None,
            room=None,
        )
        #ts_id = l.get("timeslot_id")
        ts_id = l.get("timeslot").get("id")
        print(f"ts_id ===========: {ts_id}")
        if ts_id is not None:
            lesson.timeslot = timeslot_by_id[ts_id]
        room_id = l.get("room").get("id")
        print(f"room id =========: {room_id}")
        if room_id is not None:
            lesson.room = room_by_id[room_id]
        
        print(f"lesson : {lesson}")
        lesson_objs.append(lesson)

    # Score is optional; we don't need it for printing, so pass None
    return TimeTable(timeslot_objs, room_objs, lesson_objs, score=None)


# ---------------------------------------------------------------------------
# Remote async solver client helpers
# ---------------------------------------------------------------------------

def start_async_solve(timetable: TimeTable, seconds_limit: int = 30) -> str:
    """
    POST /solve/async to start solving on the remote FastAPI solver.
    Expects the remote API to follow the contract:
      POST {REMOTE_SOLVER_BASE_URL}/solve/async
      body: { "solution": {...}, "options": {"secondsSpentLimit": <int>} }
      resp: { "problemId": "<uuid>", "status": "PENDING" | "SOLVING" | ... }
    """
    url = f"{REMOTE_SOLVER_BASE_URL}/optapy/solve/async"
    payload = timetable_to_json(timetable)
    resp = requests.post(url, json=payload)
    resp.raise_for_status()
    data = resp.json()
    print("response data from start_async_solve: %s", data)
    problemId = data["problem_id"]
    print(f"problem id : {problemId}")
    return problemId


def poll_status(problem_id: str, poll_interval_seconds: int = 2) -> str:
    """
    Poll GET /solve/{problemId}/status until FINISHED / ERROR / NOT_FOUND.
    """
    print("poll_status invoked")
    status_url = f"{REMOTE_SOLVER_BASE_URL}/optapy/solve/status/{problem_id}"

    while True:
        resp = requests.get(status_url)
        resp.raise_for_status()
        status = resp.json().get("status")
        print(f"[{problem_id}] status = {status}")
        if status in ("NOT_SOLVING", "FINISHED", "ERROR", "NOT_FOUND"):
            return status
        pytime.sleep(poll_interval_seconds)


def fetch_solution(problem_id: str) -> TimeTable:
    """
    GET /solve/{problemId}/solution and convert JSON solution back to TimeTable.
    Expects remote API:
      GET {BASE}/solve/{id}/solution -> { "solution": { ... } }
      202 Accepted if not ready.
    """
    url = f"{REMOTE_SOLVER_BASE_URL}/optapy/solution/{problem_id}"
    resp = requests.get(url)

    print(f"resp.status_code : {resp.status_code}")
    if resp.status_code != 200:
        raise RuntimeError("Solution not ready yet (HTTP 202). Call this only after FINISHED.")
    resp.raise_for_status()

    print(f"resp : {resp}")
    data = resp.json()
    solution = data["solution"]
    print(f"solution : {solution}")
    return json_to_timetable(data["solution"])


# ---------------------------------------------------------------------------
# Main entrypoint: build problem -> async solve remotely -> fetch & print
# ---------------------------------------------------------------------------

def main():
    # 1) Build the initial unsolved problem locally
    problem = generate_problem()

    # 2) Start solving asynchronously on the remote solver
    print("Starting async solve on remote solver...")
    problem_id = start_async_solve(problem, seconds_limit=30)
    print(f"Started solve with problemId={problem_id}")

    # 3) Poll until the remote solver finishes
    final_status = poll_status(problem_id)
    if final_status != "NOT_SOLVING":
        print(f"Solving did not finish successfully. Final status = {final_status}")
        return

    # 4) Fetch the final solution and print it
    solved_timetable = fetch_solution(problem_id)
    print("\n=== Solved timetable ===")
    print_timetable(solved_timetable)


if __name__ == "__main__":
    main()
