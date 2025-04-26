from pydantic import BaseModel
from typing import List, Optional, Union

class Attribute(BaseModel):
    key: str
    value: str
    type: str

class EntityInput(BaseModel):
    id: str
    entity_type: List[str]
    attributes: List[Attribute]

class ComputedAttribute(BaseModel):
    key: str
    value: Union[float, str]
    description: str

class EntityOutput(BaseModel):
    id: str
    entity_type: List[str]
    computed: List[ComputedAttribute] = []

class FormulaResult(BaseModel):
    entity_id: str
    formula: str
    resolved_formula: str
    result: Optional[Union[float, int, str]]
    result_type: Optional[str]
    error: Optional[str]
    success: bool

# Adicione estas classes
class InputData(BaseModel):
    entities: List[EntityInput]
    formulas: List[str]

class OutputData(BaseModel):
    direct_results: List[FormulaResult]
    aggregated_entities: List[EntityOutput]