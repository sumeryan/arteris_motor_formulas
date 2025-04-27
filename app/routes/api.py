from fastapi import APIRouter
from app.models.schemas import InputData, OutputData
from app.services.calculator import FormulaProcessor

router = APIRouter()

@router.post(
    "/calculate",
    response_model=OutputData,
    response_model_exclude_none=True
)
async def calculate(input_data: InputData):
    processor = FormulaProcessor(input_data.entities)
    # gera direct_results e aggregated_outputs internamente
    processor.process(input_data.formulas)
    # formata para o shape enxuto que você quer
    return OutputData(
        direct_results=processor.summarize(),
        aggregated_entities=processor.get_aggregated_output()
    )
