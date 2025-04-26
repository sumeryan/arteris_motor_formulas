from fastapi import APIRouter
from app.models.schemas import InputData, OutputData
from app.services.calculator import FormulaProcessor

router = APIRouter()

@router.post("/calculate", response_model=OutputData)
async def calculate(input_data: InputData):
    processor = FormulaProcessor(input_data.entities)
    return processor.process(input_data.formulas)