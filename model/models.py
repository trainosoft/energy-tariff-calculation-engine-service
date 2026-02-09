from typing import Any, Dict, List
from unicodedata import category
from pydantic import BaseModel
    
class TariffEvaluationSuccess(BaseModel):
    result: Any

class TariffEvaluationFailure(BaseModel):
    context: Dict[str, Any]
    error: str

class BatchTariffResponse(BaseModel):
    summary: Dict[str, int]
    success: List[TariffEvaluationSuccess]
    failed: List[TariffEvaluationFailure]
