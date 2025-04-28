from typing import List, Dict, Any
from asteval import Interpreter
import re

from app.models.schemas import EntityInput, EntityOutput, ComputedAttribute
from app.utils.helpers import get_attribute_value

class FormulaProcessor:
    """
    Processa fórmulas diretas e agregações (SUM, AVG, COUNT, MAX, MIN) em entidades.
    """
    AGG_PATTERN = re.compile(
            r"^(?P<fn>SUM|AVG|COUNT|MAX|MIN)\("
            r"(?P<prefix>[A-Za-z0-9_]+\.[A-Za-z0-9_]+)\.(?P<left>\w+)\s*\*\s*"
            r"(?P=prefix)\.(?P<right_path>[A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+)*)"
            r"\)$"
        )
    AGG_REF_PATTERN = re.compile(
        r"^(?P<fn>SUM|AVG|COUNT|MAX|MIN)\("
        r"(?P<prefix>[A-Za-z0-9_]+\.[A-Za-z0-9_]+)\.(?P<left>\w+)\s*\*\s*"
        r"@?(?P<ref_attr>\w+)\.(?P<right_attr>\w+)"
        r"\)$"
    )
    DIRECT_PATTERN = re.compile(r"\b([A-Za-z]+)\.([A-Za-z_][A-Za-z0-9_]*)\b")

    def __init__(self, entities: List[EntityInput]):
        self.entities = {e.id: e for e in entities}
        self.aeval = Interpreter()
        for fn in ('len', 'sum', 'max', 'min'):
            self.aeval.symtable[fn] = __builtins__[fn]
        self.direct_results: List[Dict[str, Any]] = []
        self.aggregated_outputs: Dict[str, EntityOutput] = {
            e.id: EntityOutput(id=e.id, entity_type=e.entity_type, computed=[])
            for e in entities
        }

    def _get_related_by_value(self, src_id: str, tgt_type: str) -> List[EntityInput]:
        related = []
        for ent in self.entities.values():
            if tgt_type not in ent.entity_type:
                continue
            for attr in ent.attributes:
                if attr.value == src_id:
                    related.append(ent)
                    break
        return related

    def process(self, formulas: List[str]) -> None:
        tributo_formulas = [f for f in formulas if 'TotalDosServicos' in f]
        for formula in formulas:
            if self.AGG_PATTERN.match(formula):
                self._process_aggregation(formula)
            elif self.AGG_REF_PATTERN.match(formula):
                self._process_ref_aggregation(formula)
            else:
                self._process_direct(formula)
        for formula in tributo_formulas:
            self._process_tributo(formula)

    def _process_aggregation(self, formula: str) -> None:
        match = self.AGG_PATTERN.match(formula)
        if not match:
            return
        fn = match.group('fn')
        prefix = match.group('prefix')
        left_attr = match.group('left')
        right_path = match.group('right_path')
        parent_type, child_type = prefix.split('.')
    # Extrai os tipos de entidade da hierarquia
        grand_type, right_attr = right_path.split('.', 1)  # Ex: ("Contract_Item_Work_Role", "Valor_por_hora")
            
        for parent in self.entities.values():
            if parent_type not in parent.entity_type:
                continue
            aggregated_values = []
            children = self._get_related_by_value(parent.id, child_type)
            for child in children:
                ref_entity = None
                grandchildren = self._get_related_by_value(child.id, grand_type)
                v1 = float(get_attribute_value(child, left_attr) or 0)
                values = [v1 * float(get_attribute_value(gc, right_attr) or 0) for gc in grandchildren]
                res = self._apply_aggregation(fn, values)
                desc = f"{fn}({left_attr} * {right_attr})"
                self._record_result(child.id, formula, desc, res)
                for attr in child.attributes:
                    candidate_entity = self.entities.get(attr.value)
                    if candidate_entity and grand_type in candidate_entity.entity_type:
                        ref_entity = candidate_entity
                        break
                if not ref_entity:
                    continue  # Se não encontrar, pula para a próxima child
                # Passo 2: Coleta os valores
                try:
                    left_val = float(get_attribute_value(child, left_attr) or 0)
                    right_val = float(get_attribute_value(ref_entity, right_attr) or 0)
                    aggregated_values.append(left_val * right_val)
                except (TypeError, ValueError):
                    continue
                    # Passo 3: Aplica a função de agregação nos valores acumulados
        result = self._apply_aggregation(fn, aggregated_values)
        
        # Passo 4: Registra o resultado no pai (Contract_Measurement)
        desc = f"{fn}({child_type}.{left_attr} * {grand_type}.{right_attr})"
        self._record_result(parent.id, formula, desc, result)
        
            

    def _process_ref_aggregation(self, formula: str) -> None:
        match = self.AGG_REF_PATTERN.match(formula)
        if not match:
            return
        fn = match.group('fn')
        prefix = match.group('prefix')
        left_attr = match.group('left')
        ref_attr = match.group('ref_attr')
        right_attr = match.group('right_attr')
        parent_type, child_type = prefix.split('.')
        
        for parent in self.entities.values():
            if parent_type not in parent.entity_type:
                continue
            children = self._get_related_by_value(parent.id, child_type)
            values = []
            for child in children:
                left_val = get_attribute_value(child, left_attr)
                if left_val is None:
                    continue
                ref_id = get_attribute_value(child, ref_attr)
                if not ref_id:
                    continue
                ref_entity = self.entities.get(ref_id)
                if not ref_entity:
                    continue
                right_val = get_attribute_value(ref_entity, right_attr)
                if right_val is None:
                    continue
                try:
                    product = float(left_val) * float(right_val)
                    values.append(product)
                except (ValueError, TypeError):
                    continue
            res = self._apply_aggregation(fn, values)
            desc = f"{fn}({child_type}.{left_attr} * @{ref_attr}.{right_attr})"
            self._record_result(parent.id, formula, desc, res)

    def _apply_aggregation(self, fn: str, values: List[float]) -> float:
        if not values:
            return 0.0
        if fn == 'SUM':
            return sum(values)
        elif fn == 'AVG':
            return sum(values) / len(values)
        elif fn == 'COUNT':
            return len(values)
        elif fn == 'MAX':
            return max(values)
        elif fn == 'MIN':
            return min(values)
        else:
            return 0.0

    def _record_result(self, entity_id: str, formula: str, desc: str, result: float) -> None:
        self.direct_results.append({
            'entity_id': entity_id,
            'formula': formula,
            'resolved_formula': desc,
            'result': float(result),
            'result_type': 'float',
            'success': True,
            'error': None
        })
        self.aggregated_outputs[entity_id].computed.append(
            ComputedAttribute(key=desc, value=result, description=desc)
        )

    def _process_tributo(self, formula: str) -> None:
        for contract in self.entities.values():
            if 'Contract' not in contract.entity_type:
                continue
            services = self._get_related_by_value(contract.id, 'Servico')
            total = sum(
                next((c.value for c in self.aggregated_outputs[s.id].computed if c.key.startswith('SUM')), 0.0)
                for s in services
            )
            iss = float(get_attribute_value(contract, 'ISS') or 0)
            trib = iss * total
            desc = f"ISS ({iss}) * TotalDosServicos ({total})"
            self._record_result(contract.id, formula, desc, trib)

    # _process_direct, summarize, get_aggregated_output mantidos sem alterações

    def _process_direct(self, formula: str) -> None:
        refs = self.DIRECT_PATTERN.findall(formula)
        for entity_type, _ in set(refs):
            for entity in self.entities.values():
                if entity_type not in entity.entity_type:
                    continue
                resolved = formula
                for etype, attr in refs:
                    if etype != entity_type:
                        continue
                    val = get_attribute_value(entity, attr)
                    token = f'"{val}"' if isinstance(val, str) else str(val)
                    resolved = resolved.replace(f"{etype}.{attr}", token)
                try:
                    res = eval(resolved)
                    self.direct_results.append({
                        'entity_id': entity.id,
                        'formula': formula,
                        'resolved_formula': resolved,
                        'result': float(res) if isinstance(res, (int, float)) else res,
                        'result_type': type(res).__name__,
                        'success': True,
                        'error': None
                    })
                except Exception as e:
                    self.direct_results.append({
                        'entity_id': entity.id,
                        'formula': formula,
                        'resolved_formula': resolved,
                        'result': None,
                        'result_type': None,
                        'success': False,
                        'error': str(e)
                    })

    def summarize(self) -> List[Dict[str, Any]]:
        seen = set()
        summary = []
        for res in self.direct_results:
            key = (res['entity_id'], res['formula'], res['resolved_formula'])
            if key in seen:
                continue
            seen.add(key)
            val = res['result']
            if isinstance(val, (int, float)):
                val = float(val)
            summary.append({
                'entity_id': res['entity_id'],
                'formula': res['formula'],
                'resolved_formula': res['resolved_formula'],
                'result': val,
                'result_type': res.get('result_type'),
                'error': res.get('error'),
                'success': res.get('success', False)
            })
        return summary

    def get_aggregated_output(self) -> List[EntityOutput]:
        return [o for o in self.aggregated_outputs.values() if o.computed]

