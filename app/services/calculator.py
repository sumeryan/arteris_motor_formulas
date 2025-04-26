
from typing import List, Dict, Any
from asteval import Interpreter
import re

from app.models.schemas import EntityInput, EntityOutput, ComputedAttribute
from app.utils.helpers import get_attribute_value

class FormulaProcessor:
    
    AGG_PATTERN = re.compile(
        r"^(?P<fn>SUM|AVG|COUNT|MAX|MIN)\("  # função de agregação
        r"(?P<prefix>[A-Za-z]+\.[A-Za-z]+)\.(?P<left>\w+)\s*\*\s*"  # prefix.attr *
        r"(?P=prefix)\.(?P<right_path>[A-Za-z]+(?:\.[A-Za-z]+)*)"  # prefix.right_path
        r"\)$"
    )
    DIRECT_PATTERN = re.compile(r"\b([A-Za-z]+)\.([A-Za-z_][A-Za-z0-9_]*)\b")

    def __init__(self, entities: List[EntityInput]):
        self.entities = {e.id: e for e in entities}
        self.aeval = Interpreter()
        # expor built-ins
        for fn in ('len', 'sum', 'max', 'min'):
            self.aeval.symtable[fn] = __builtins__[fn]

        self.direct_results: List[Dict[str, Any]] = []
        self.aggregated_outputs: Dict[str, EntityOutput] = {
            e.id: EntityOutput(id=e.id, entity_type=e.entity_type, computed=[])
            for e in entities
        }

    def _get_related_by_value(self, src_id: str, tgt_type: str) -> List[EntityInput]:
        return [ent for ent in self.entities.values()
                if tgt_type in ent.entity_type and
                   any(attr.value == src_id for attr in ent.attributes)]

    def process(self, formulas: List[str]) -> Dict[str, Any]:
        tributo_formulas = [f for f in formulas if 'TotalDosServicos' in f]

        for formula in formulas:
            if self.AGG_PATTERN.match(formula):
                self._process_aggregation(formula)
            else:
                self._process_direct(formula)

        for formula in tributo_formulas:
            self._process_tributo(formula)

        return {
            'direct_results': self.direct_results,
            'aggregated_entities': [e for e in self.aggregated_outputs.values() if e.computed]
        }

    def _process_aggregation(self, formula: str):
        match = self.AGG_PATTERN.match(formula)
        fn = match.group('fn')
        prefix = match.group('prefix')
        left_attr = match.group('left')
        right_path = match.group('right_path')
        parent_type, child_type = prefix.split('.')
        grand_type, right_attr = right_path.split('.')

        for parent in self.entities.values():
            if parent_type not in parent.entity_type:
                continue
            children = self._get_related_by_value(parent.id, child_type)
            for child in children:
                grandchildren = self._get_related_by_value(child.id, grand_type)
                v1 = float(get_attribute_value(child, left_attr))
                values = [v1 * float(get_attribute_value(gc, right_attr)) for gc in grandchildren]

                if fn == 'SUM': res = sum(values)
                elif fn == 'COUNT': res = len(values)
                elif fn == 'AVG': res = sum(values)/len(values) if values else 0
                elif fn == 'MAX': res = max(values) if values else 0
                elif fn == 'MIN': res = min(values) if values else 0
                else: res = None

                desc = f"{fn}({left_attr} * {right_attr})"
                self.direct_results.append({
                    'entity_id': child.id,
                    'formula': formula,
                    'resolved_formula': desc,
                    'result': res,
                    'result_type': type(res).__name__,
                    'success': True,
                    'error': None
                })
                self.aggregated_outputs[child.id].computed.append(
                    ComputedAttribute(key=desc, value=res, description=desc)
                )

    def _process_tributo(self, formula: str):
        for contract in self.entities.values():
            if 'Contract' not in contract.entity_type:
                continue
            services = self._get_related_by_value(contract.id, 'Servico')
            total = sum(
                next((attr.value for attr in self.aggregated_outputs[s.id].computed
                      if attr.key.startswith('SUM')), 0.0)
                for s in services
            )
            iss = float(get_attribute_value(contract, 'ISS'))
            trib = iss * total
            desc = f"ISS ({iss}) * TotalDosServicos ({total})"
            self.direct_results.append({
                'entity_id': contract.id,
                'formula': formula,
                'resolved_formula': desc,
                'result': trib,
                'result_type': type(trib).__name__,
                'success': True,
                'error': None
            })
            self.aggregated_outputs[contract.id].computed.append(
                ComputedAttribute(key='Tributo', value=trib, description=desc)
            )

    def _process_direct(self, formula: str):
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
                        'result': res,
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
