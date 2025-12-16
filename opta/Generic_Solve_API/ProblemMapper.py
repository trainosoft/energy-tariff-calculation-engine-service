from datetime import time, timedelta
import datetime
from random import Random
from typing import Any, Dict

from config.logger import logger
from opta.Generic_Solve_API.domain import Availability, AvailabilityType, Employee, EmployeeSchedule, ScheduleState, Shift
from opta.schooltimetabling.domain import Lesson, Room, TimeTable, Timeslot



def build_school_problem(problem_data: Dict[str, Any]) -> TimeTable:
    timeslot_map = {
        ts["id"]: Timeslot(
            ts["id"],
            ts["day_of_week"],
            time.fromisoformat(ts["start_time"]),
            time.fromisoformat(ts["end_time"]),
        )
        for ts in problem_data["timeslot_list"]
    }

    room_map = {
        r["id"]: Room(r["id"], r["name"])
        for r in problem_data["room_list"]
    }

    lesson_list = [
        Lesson(
            l["id"],
            l["subject"],
            l["teacher"],
            l["student_group"],
            timeslot_map.get(l["timeslot"]),
            room_map.get(l["room"]),
        )
        for l in problem_data["lesson_list"]
    ]

    return TimeTable(
        list(timeslot_map.values()),
        list(room_map.values()),
        lesson_list
    )


def next_weekday(d, weekday):
    days_ahead = weekday - d.weekday()
    if days_ahead <= 0:  # Target day already happened this week
        days_ahead += 7
    return d + datetime.timedelta(days_ahead)

# FIRST_NAMES = ["Amy", "Beth", "Chad", "Dan", "Elsa", "Flo", "Gus", "Hugo", "Ivy", "Jay"]
# LAST_NAMES = ["Cole", "Fox", "Green", "Jones", "King", "Li", "Poe", "Rye", "Smith", "Watt"]
# REQUIRED_SKILLS = ["Doctor", "Nurse"]
# OPTIONAL_SKILLS = ["Anaesthetics"]
# LOCATIONS = ["Ambulatory care", "Critical care", "Pediatric care"]
# SHIFT_LENGTH = datetime.timedelta(hours=8)
# MORNING_SHIFT_START_TIME = datetime.time(hour=6)
# DAY_SHIFT_START_TIME = datetime.time(hour=9)
# AFTERNOON_SHIFT_START_TIME = datetime.time(hour=14)
# NIGHT_SHIFT_START_TIME = datetime.time(hour=22)

# SHIFT_START_TIME_COMBOS = (
#     (MORNING_SHIFT_START_TIME, AFTERNOON_SHIFT_START_TIME),
#     (MORNING_SHIFT_START_TIME, AFTERNOON_SHIFT_START_TIME, NIGHT_SHIFT_START_TIME),
#     (MORNING_SHIFT_START_TIME, DAY_SHIFT_START_TIME, AFTERNOON_SHIFT_START_TIME, NIGHT_SHIFT_START_TIME)
# )

location_to_shift_start_time_list_dict = dict()
id_generator = 0


def generate_demo_data(problem_data: Dict[str, Any]):
    global schedule
    INITIAL_ROSTER_LENGTH_IN_DAYS = 14
    START_DATE = next_weekday(datetime.date.today(), 0)  # next Monday

    schedule_state = ScheduleState()
    schedule_state.first_draft_date = START_DATE
    schedule_state.draft_length = INITIAL_ROSTER_LENGTH_IN_DAYS
    schedule_state.publish_length = 7
    schedule_state.last_historic_date = START_DATE

    random = Random(0)

    shift_template_index = 0
    for location in problem_data.get('locations'):
        location_to_shift_start_time_list_dict[location] = problem_data.get('shift_start_time_combos')[shift_template_index]
        shift_template_index = (shift_template_index + 1) % len(problem_data.get('shift_start_time_combos'))

    name_permutations = join_all_combinations(problem_data.get('first_names'), problem_data.get('last_names'))
    random.shuffle(name_permutations)

    employee_list = []
    for i in range(16):
        skills = pick_subset(problem_data.get('optional_skills'), random, 1, 3)
        skills.append(pick_random(problem_data.get('required_skills'), random))
        employee = Employee()
        employee.name = name_permutations[i]
        employee.skill_set = skills
        employee_list.append(employee)

    shift_list = []
    availability_list = []
    for i in range(INITIAL_ROSTER_LENGTH_IN_DAYS):
        employees_with_availabilities_on_day = pick_subset(employee_list, random, 4, 3, 2, 1)
        date = START_DATE + datetime.timedelta(days=i)
        for employee in employees_with_availabilities_on_day:
            availability_type = pick_random(AvailabilityType.list(), random)
            availability = Availability()
            availability.date = date
            availability.employee = employee
            availability.availability_type = availability_type
            availability_list.append(availability)
        shift_list.extend(generate_shifts_for_day(problem_data, date, random))
    return EmployeeSchedule(
        schedule_state,
        availability_list,
        employee_list,
        shift_list,
        None
    )

def join_all_combinations(*part_arrays: list[str]):
    if len(part_arrays) == 0:
        return []
    if len(part_arrays) == 1:
        return part_arrays[0]
    combinations = []
    for combination in join_all_combinations(*part_arrays[1:]):
        for item in part_arrays[0]:
            combinations.append(f'{item} {combination}')
    return combinations

def pick_subset(source: list, random: Random, *distribution: int):
    item_count = random.choices(range(len(distribution)), distribution)
    return random.sample(source, item_count[0])

def pick_random(source: list, random: Random):
    return random.choice(source)

def generate_shifts_for_day(problem_data: Dict[str, Any], date: datetime.date, random: Random):
    logger.info(f"problem_data is {problem_data}")
    out = []

    raw_shift_length = problem_data.get("shift_length", "08:00:00")
    shift_length = parse_shift_length(raw_shift_length)
    logger.info(f"shift_length is : {shift_length}")

    for location in problem_data.get("locations", []):
        shift_start_time_list = location_to_shift_start_time_list_dict[location]
        logger.info(f"shift_start_time_list is {shift_start_time_list}")

        for shift_start_time_str in shift_start_time_list:
            # ✅ Convert string → datetime.time
            shift_start_time = time.fromisoformat(shift_start_time_str)

            shift_start_date_time = datetime.datetime.combine(date, shift_start_time)
            shift_end_date_time = shift_start_date_time + shift_length

            out.append(
                generate_shift_for_timeslot(
                    problem_data,
                    shift_start_date_time,
                    shift_end_date_time,
                    location,
                    random
                )
            )

    return out

def generate_shift_for_timeslot(
    problem_data: Dict[str, Any], 
    timeslot_start: datetime.datetime, 
    timeslot_end: datetime.datetime,
    location: str, 
    random: Random
    ):

    global id_generator
    shift_count = random.choices([1, 2], [0.8, 0.2])[0]

    for i in range(shift_count):
        required_skill = None

        if random.randint(0, 1) == 1:
            required_skill = pick_random(problem_data.get('required_skills'), random)
        else:
            required_skill = pick_random(problem_data.get('optional_skills'), random)

        shift = Shift()
        shift.id = id_generator
        shift.start = timeslot_start
        shift.end = timeslot_end
        shift.required_skill = required_skill
        shift.location = location
        shift.employee = None
        id_generator += 1
        return shift

def parse_shift_length(value: str) -> timedelta:
    hours, minutes, seconds = map(int, value.split(":"))
    return timedelta(hours=hours, minutes=minutes, seconds=seconds)