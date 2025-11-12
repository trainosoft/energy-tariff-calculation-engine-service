from unicodedata import category
from pydantic import BaseModel

class TerifCalculationRequest(BaseModel):
    category: str
    subCategory: str
    loadKW: float
    units: float

class TerifCalculationResponse(BaseModel):
    category: str
    subcategory: str
    load: float
