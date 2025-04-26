from asteval import Interpreter
import re
from typing import List, Dict, Union, Optional
from app.models.schemas import EntityInput, EntityOutput, ComputedAttribute
from app.utils.helpers import get_attribute_value, find_related_entities

class FormulaProcessor:
    def __init__(self, entities: List[EntityInput]):
        self.entities = {e.id: e for e in entities}
        self.direct_results = []
        self.aggregated_results = {}
        self.computed_values = {}
        self.aeval = Interpreter()
        self.aeval.symtable['len'] = len
        self.pattern = re.compile(r'\b([A-Za-z]+\.[A-Za-z]+)\b')

    def process(self, formulas: List[str]) -> Dict:
        self._preprocess_entities()
        
        # Processamento em duas etapas independentes
        self._process_direct_formulas(formulas)
        self._process_aggregated_formulas(formulas)
        
        return {
            "direct_results": self.direct_results,
            "aggregated_entities": self._get_aggregated_entities()
        }

    def _preprocess_entities(self):
        for entity in self.entities.values():
            self.aggregated_results[entity.id] = EntityOutput(
                id=entity.id,
                entity_type=entity.entity_type,
                computed=[]
            )

    def _process_direct_formulas(self, formulas: List[str]):
        """Processa fórmulas simples com resultados diretos"""
        for formula in formulas:
            if not formula.startswith("SUM("):
                for entity in self.entities.values():
                    self._evaluate_direct_formula(entity, formula)

    def _evaluate_direct_formula(self, entity: EntityInput, formula: str):
        try:
            entity_type = formula.split('.')[0]
            if entity_type not in entity.entity_type:
                return

            resolved = formula
            matches = set(self.pattern.findall(formula))
            
            replacements = {}
            for match in matches:
                attr = match.split('.')[1]
                value = get_attribute_value(entity, attr)
                replacements[match] = f'"{value}"' if isinstance(value, str) else str(value)

            # Fazer todas as substituições de uma vez
            for key, value in replacements.items():
                resolved = resolved.replace(key, value)

            result = self.aeval(resolved)
            result_type = 'float' if isinstance(result, float) else \
                         'int' if isinstance(result, int) else 'string'

            self.direct_results.append({
                "entity_id": entity.id,
                "formula": formula,
                "resolved_formula": resolved,
                "result": result,
                "result_type": result_type,
                "error": None,
                "success": True
            })
        except Exception as e:
            self.direct_results.append({
                "entity_id": entity.id,
                "formula": formula,
                "resolved_formula": resolved,
                "result": None,
                "result_type": None,
                "error": str(e),
                "success": False
            })

    def _process_aggregated_formulas(self, formulas: List[str]):
        """Processa fórmulas complexas com agregações"""
        sum_formulas = [f for f in formulas if f.startswith("SUM(")]
        tributo_formulas = [f for f in formulas if "TotalDosServicos" in f]

        for formula in sum_formulas:
            self._process_sum_aggregation(formula)
            
        for formula in tributo_formulas:
            self._process_tributo_calculation()

    def _process_sum_aggregation(self, formula: str):
        match = re.search(r'SUM\(([^)]+)\)', formula)
        if not match:
            return

        try:
            expression = match.group(1)
            left_part, right_part = expression.split('*')
            left_path = [p.strip() for p in left_part.split('.')]
            right_path = [p.strip() for p in right_part.split('.')]
            
            parent_type = left_path[0]
            child_type = left_path[1]
            left_attr = left_path[2]
            right_attr = right_path[3]
        except Exception as e:
            return

        for contract in self.entities.values():
            if parent_type in contract.entity_type:
                services = find_related_entities(
                    source=contract,
                    target_type=child_type,
                    reference_attr='id',
                    all_entities=self.entities.values(),
                    target_reference_attr='contractId'
                )
                
                for service in services:
                    measurements = find_related_entities(
                        source=service,
                        target_type="Medicao",
                        reference_attr='id',
                        all_entities=self.entities.values(),
                        target_reference_attr='serviceId'
                    )
                    
                    service_total = sum(
                        get_attribute_value(service, left_attr) * 
                        get_attribute_value(m, right_attr)
                        for m in measurements
                    )
                    
                    self._store_aggregated_value(
                        service.id,
                        "TotalDosServicos",
                        service_total,
                        f"SUM({left_attr} * {right_attr})"
                    )

    def _process_tributo_calculation(self):
        for contract in self.entities.values():
            if "Contract" in contract.entity_type:
                try:
                    services = find_related_entities(
                        source=contract,
                        target_type="Servico",
                        reference_attr='id',
                        all_entities=self.entities.values(),
                        target_reference_attr='contractId'
                    )
                    
                    total_servicos = sum(
                        self.computed_values.get(s.id, {}).get("TotalDosServicos", 0)
                        for s in services
                    )
                    
                    iss = get_attribute_value(contract, "ISS")
                    tributo = iss * total_servicos
                    
                    self._store_aggregated_value(
                        contract.id,
                        "Tributo",
                        tributo,
                        f"ISS ({iss}) * TotalDosServicos ({total_servicos})"
                    )
                except Exception as e:
                    self._add_aggregated_error(contract.id, "Tributo", str(e))

    def _store_aggregated_value(self, entity_id: str, key: str, value: float, description: str):
        self.computed_values.setdefault(entity_id, {})[key] = value
        self.aggregated_results[entity_id].computed.append(
            ComputedAttribute(
                key=key,
                value=value,
                description=description
            )
        )

    def _add_aggregated_error(self, entity_id: str, key: str, error: str):
        self.aggregated_results[entity_id].computed.append(
            ComputedAttribute(
                key=key,
                value="ERRO",
                description=f"Erro: {error}"
            )
        )

    def _get_aggregated_entities(self) -> List[EntityOutput]:
        return [
            entity for entity in self.aggregated_results.values() 
            if any(attr.key in ["TotalDosServicos", "Tributo"] for attr in entity.computed)
        ]