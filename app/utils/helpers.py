from typing import List, Union
from app.models.schemas import EntityInput

# helpers.py
def get_attribute_value(entity: EntityInput, key: str) -> Union[float, int, str]:
    for attr in entity.attributes:
        if attr.key == key:
            if attr.type == 'number':
                # Verifica se o valor já é numérico
                if isinstance(attr.value, (int, float)):
                    return attr.value
                # Converte string para numérico
                return float(attr.value) if '.' in attr.value else int(attr.value)
            return attr.value
    raise ValueError(f"Attribute '{key}' not found in entity {entity.id}")

def find_related_entities(
    source: EntityInput,
    target_type: str,
    reference_attr: str,
    all_entities: List[EntityInput],
    target_reference_attr: str
) -> List[EntityInput]:
    source_values = [attr.value for attr in source.attributes if attr.key == reference_attr]
    return [
        e for e in all_entities
        if target_type in e.entity_type and
        any(attr.key == target_reference_attr and attr.value in source_values for attr in e.attributes)
    ]