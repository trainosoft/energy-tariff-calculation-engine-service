from typing import Any, Dict, List
from unicodedata import category
from pydantic import BaseModel

class TariffCalculationRequest(BaseModel):
    # customer_Id: int
    # category: str
    # subCategory: str
    # loadKW: float
    # units: float
    # exceededDemand: float
    # peakHRUnits: float
    # offPeakHRUnits: float

    # category: str
    # subcategory: str
    # units_consumed: float
    # contracted_load: float
    # connected_load: float
    # days: int
    # meter_rent: float
    # adjustment: float 

    # consumption_unit: float
    # Opening_Balance: float
    # Date: str

    DVC_provide_ECR: float
    DVC_provide_MVCA: float
    last_month_unit_consumption: float
    consumption_unit: float
    Opening_Balance: float
    Voucher: float
    Date: str

class BatchTariffCalculationRequest(BaseModel):
    requests: List[TariffCalculationRequest]
    
class TariffEvaluationSuccess(BaseModel):
    result: Any

class TariffEvaluationFailure(BaseModel):
    context: Dict[str, Any]
    error: str

class BatchTariffResponse(BaseModel):
    summary: Dict[str, int]
    success: List[TariffEvaluationSuccess]
    failed: List[TariffEvaluationFailure]

class EvaluateResponse(BaseModel):
    result: dict
