from pydantic import BaseModel
from typing import Any, Dict, List, Optional
from datetime import time
 
class RoomDTO(BaseModel):
    id: int
    name: str
 
class TimeslotDTO(BaseModel):
    id: int
    day_of_week: str
    start_time: time
    end_time: time
 
class LessonDTO(BaseModel):
    id: int
    subject: str
    teacher: str
    student_group: str
    timeslot: Optional[int] = None
    room: Optional[int] = None
 
class TimeTableDTO(BaseModel):
    timeslot_list: List[TimeslotDTO]
    room_list: List[RoomDTO]
    lesson_list: List[LessonDTO]

class SolveRequest(BaseModel):
    problemType: str
    problemData: Dict[str, Any]