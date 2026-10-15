"""Writes tests/outputs.json and the instruction's output-contract section from one schema."""
import json
import sys
from pathlib import Path

T = Path(sys.argv[1])
sys.path.insert(0, str(T / "tests"))
from _arena_runtime.contracts import public_contract  # noqa: E402

OUT = "cover_matrix_check.json"


def count(desc, maximum=10000):
    return {"type": "integer", "minimum": 0, "maximum": maximum, "description": desc}


def obj(props, desc):
    return {"type": "object", "additionalProperties": False, "required": list(props), "properties": props,
            "description": desc}


SUBS = [("hard_suitcases", "Чемоданы пластиковые"), ("soft_suitcases", "Чемоданы тканевые"), ("travel_bags", "Дорожные сумки"),
        ("backpacks", "Рюкзаки дорожные"), ("luggage_scales", "Багажные весы"), ("accessories", "Аксессуары для путешествий")]
schema = obj({
    "matrix_sku_count": count("SKUs in the suitcase-cover launch matrix"),
    "designs": {"type": "array", "minItems": 1, "maxItems": 200, "uniqueItems": True, "unordered": True,
                "items": {"type": "string", "minLength": 1, "maxLength": 200}, "description": "the matrix's distinct designs, one name per design"},
    "design_count": count("distinct designs in the matrix (entries in designs)"),
    "skus_by_body": obj({"hard": count("SKUs for hard-body suitcases"), "soft": count("SKUs for soft-body suitcases")},
                        "matrix SKUs per suitcase body material"),
    "skus_by_colour_cluster": obj({"dark": count("SKUs in Тёмные базовые"), "neutral": count("SKUs in Светлые нейтральные"),
                                   "bright": count("SKUs in Яркие")}, "matrix SKUs per colour cluster"),
    "skus_by_size": obj({k: count(f"SKUs in size band {k}") for k in ("S", "M", "L", "XL")},
                        "matrix SKUs per size band of the size grid"),
    "skus_by_price_segment": obj({"base": count("SKUs in the базовый price segment"), "mid": count("SKUs in the средний price segment"),
                                  "top": count("SKUs in the верхний price segment")}, "matrix SKUs per price segment of the passport"),
    "slide1": obj({
        "active_skus_before": count("active SKUs in the category on the intern's first day", 100000),
        "active_skus_after_by_subcategory": obj({k: count(f"active SKUs now in {ru}", 100000) for k, ru in SUBS},
                                                "active SKUs in the category now, per subcategory"),
        "active_skus_after": {"type": "integer", "minimum": 1, "maximum": 100000, "description": "sum of the six subcategory figures"},
        "ru_skus_after": count("of the active SKUs now, those with Russia as supplier country", 100000),
        "ru_share_after_pct": count("ru_skus_after as a percentage of active_skus_after, as slide 1 shows it", 100),
    }, "figures for slide 1"),
}, "figures for the defence deck")
outputs = [{"file": OUT, "step": "01-task", "schema": schema}]
(T / "tests" / "outputs.json").write_text(json.dumps({"outputs": outputs}, ensure_ascii=False, indent=2) + "\n")
head = (T / "authoring" / "instruction_head.md").read_text()
(T / "steps" / "01-task").mkdir(parents=True, exist_ok=True)
(T / "steps" / "01-task" / "instruction.md").write_text(head.rstrip("\n") + public_contract(outputs, "01-task") + "\n")
print("ok")
