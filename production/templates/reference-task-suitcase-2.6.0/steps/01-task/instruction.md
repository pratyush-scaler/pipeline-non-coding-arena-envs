# Figures check for an internship defence deck

You are the category analyst for «Чемоданы и аксессуары для путешествий» (suitcases and travel accessories) at the Орбита retail chain. Polina Krylova, a summer intern in the category, defends her internship this week. Her mentor, Anna Lebedeva, has asked you to check the figures in Polina's draft deck against the working files and to send back the correct figures in one file, which Polina will copy onto her slides.

As of Monday 12 October 2026, work out the figures below. Every file you need is in /app/environment/files (the working files are in Russian). Use the subcategory passport's definitions and the company's presentation guide wherever they apply.

Write one JSON file with these fields:

- `matrix_sku_count`: the number of SKUs in Polina's launch matrix for suitcase covers.
- `designs`: the distinct designs in that matrix, one entry per design, each written as the design's name, in any order.
- `design_count`: the number of distinct designs in that matrix, which is the number of entries in `designs`.
- `skus_by_body`: the matrix's SKUs per suitcase body material of the passport: `hard` (жёсткий корпус) and `soft` (мягкий корпус).
- `skus_by_colour_cluster`: the matrix's SKUs per colour cluster of the passport: `dark` (Тёмные базовые), `neutral` (Светлые нейтральные) and `bright` (Яркие).
- `skus_by_size`: the matrix's SKUs per size band of the passport's size grid: `S`, `M`, `L` and `XL`.
- `skus_by_price_segment`: the matrix's SKUs per price segment of the passport: `base` (базовый), `mid` (средний) and `top` (верхний).
- `slide1`: the figures for slide 1 ("what it was when I arrived and what it became"), about the whole suitcases and travel accessories category and counting active SKUs only:
  - `active_skus_before`: the category's active SKUs as the category stood on Polina's first day of the internship;
  - `active_skus_after_by_subcategory`: the category's active SKUs as the category stands now, per subcategory: `hard_suitcases` (Чемоданы пластиковые), `soft_suitcases` (Чемоданы тканевые), `travel_bags` (Дорожные сумки), `backpacks` (Рюкзаки дорожные), `luggage_scales` (Багажные весы) and `accessories` (Аксессуары для путешествий);
  - `active_skus_after`: the sum of those six figures;
  - `ru_skus_after`: how many of those `active_skus_after` SKUs have Russia as their supplier country;
  - `ru_share_after_pct`: `ru_skus_after` as a percentage of `active_skus_after`, as it will appear on slide 1. It is graded against your own `ru_skus_after` and `active_skus_after`.

Write every count and percentage as a JSON integer.

Output contract

Inputs: every supplied source file is in /app/environment/files (read-only). A bare file name in this assignment that is not a deliverable is relative to /app/environment/files. Leave every supplied source file byte-for-byte unchanged.

Outputs: write each deliverable as UTF-8 JSON, without Markdown fences, to /app/deliverables/<file>. This step writes: /app/deliverables/cover_matrix_check.json. These schemas define the required fields and types. Produce only files declared by this task; declared artifacts from other steps may coexist. Undeclared files, unrelated directories and symlinks earn zero for this step. Duplicate keys and nonfinite numbers are invalid. An invalid or missing required file earns zero for this step. Array order is compared as written, except for an array whose schema says "unordered": true or that the assignment says may be in any order.

Equality and set comparisons ignore letter case, repeated whitespace, smart quotes/dashes, leading Markdown heading/list/quote markers and trailing heading hashes. Numeric strings ignore thousands separators. These comparison rules do not relax schema constraints. A list that must not repeat an entry is checked by these same rules: a whole number and the same number written with a decimal point, or two texts that differ only in letter case, are one entry.

/app/deliverables/cover_matrix_check.json:
```json
{
  "type": "object",
  "additionalProperties": false,
  "required": [
    "matrix_sku_count",
    "designs",
    "design_count",
    "skus_by_body",
    "skus_by_colour_cluster",
    "skus_by_size",
    "skus_by_price_segment",
    "slide1"
  ],
  "properties": {
    "matrix_sku_count": {
      "type": "integer",
      "minimum": 0,
      "maximum": 10000,
      "description": "SKUs in the suitcase-cover launch matrix"
    },
    "designs": {
      "type": "array",
      "minItems": 1,
      "maxItems": 200,
      "uniqueItems": true,
      "unordered": true,
      "items": {
        "type": "string",
        "minLength": 1,
        "maxLength": 200
      },
      "description": "the matrix's distinct designs, one name per design"
    },
    "design_count": {
      "type": "integer",
      "minimum": 0,
      "maximum": 10000,
      "description": "distinct designs in the matrix (entries in designs)"
    },
    "skus_by_body": {
      "type": "object",
      "additionalProperties": false,
      "required": [
        "hard",
        "soft"
      ],
      "properties": {
        "hard": {
          "type": "integer",
          "minimum": 0,
          "maximum": 10000,
          "description": "SKUs for hard-body suitcases"
        },
        "soft": {
          "type": "integer",
          "minimum": 0,
          "maximum": 10000,
          "description": "SKUs for soft-body suitcases"
        }
      },
      "description": "matrix SKUs per suitcase body material"
    },
    "skus_by_colour_cluster": {
      "type": "object",
      "additionalProperties": false,
      "required": [
        "dark",
        "neutral",
        "bright"
      ],
      "properties": {
        "dark": {
          "type": "integer",
          "minimum": 0,
          "maximum": 10000,
          "description": "SKUs in Тёмные базовые"
        },
        "neutral": {
          "type": "integer",
          "minimum": 0,
          "maximum": 10000,
          "description": "SKUs in Светлые нейтральные"
        },
        "bright": {
          "type": "integer",
          "minimum": 0,
          "maximum": 10000,
          "description": "SKUs in Яркие"
        }
      },
      "description": "matrix SKUs per colour cluster"
    },
    "skus_by_size": {
      "type": "object",
      "additionalProperties": false,
      "required": [
        "S",
        "M",
        "L",
        "XL"
      ],
      "properties": {
        "S": {
          "type": "integer",
          "minimum": 0,
          "maximum": 10000,
          "description": "SKUs in size band S"
        },
        "M": {
          "type": "integer",
          "minimum": 0,
          "maximum": 10000,
          "description": "SKUs in size band M"
        },
        "L": {
          "type": "integer",
          "minimum": 0,
          "maximum": 10000,
          "description": "SKUs in size band L"
        },
        "XL": {
          "type": "integer",
          "minimum": 0,
          "maximum": 10000,
          "description": "SKUs in size band XL"
        }
      },
      "description": "matrix SKUs per size band of the size grid"
    },
    "skus_by_price_segment": {
      "type": "object",
      "additionalProperties": false,
      "required": [
        "base",
        "mid",
        "top"
      ],
      "properties": {
        "base": {
          "type": "integer",
          "minimum": 0,
          "maximum": 10000,
          "description": "SKUs in the базовый price segment"
        },
        "mid": {
          "type": "integer",
          "minimum": 0,
          "maximum": 10000,
          "description": "SKUs in the средний price segment"
        },
        "top": {
          "type": "integer",
          "minimum": 0,
          "maximum": 10000,
          "description": "SKUs in the верхний price segment"
        }
      },
      "description": "matrix SKUs per price segment of the passport"
    },
    "slide1": {
      "type": "object",
      "additionalProperties": false,
      "required": [
        "active_skus_before",
        "active_skus_after_by_subcategory",
        "active_skus_after",
        "ru_skus_after",
        "ru_share_after_pct"
      ],
      "properties": {
        "active_skus_before": {
          "type": "integer",
          "minimum": 0,
          "maximum": 100000,
          "description": "active SKUs in the category on the intern's first day"
        },
        "active_skus_after_by_subcategory": {
          "type": "object",
          "additionalProperties": false,
          "required": [
            "hard_suitcases",
            "soft_suitcases",
            "travel_bags",
            "backpacks",
            "luggage_scales",
            "accessories"
          ],
          "properties": {
            "hard_suitcases": {
              "type": "integer",
              "minimum": 0,
              "maximum": 100000,
              "description": "active SKUs now in Чемоданы пластиковые"
            },
            "soft_suitcases": {
              "type": "integer",
              "minimum": 0,
              "maximum": 100000,
              "description": "active SKUs now in Чемоданы тканевые"
            },
            "travel_bags": {
              "type": "integer",
              "minimum": 0,
              "maximum": 100000,
              "description": "active SKUs now in Дорожные сумки"
            },
            "backpacks": {
              "type": "integer",
              "minimum": 0,
              "maximum": 100000,
              "description": "active SKUs now in Рюкзаки дорожные"
            },
            "luggage_scales": {
              "type": "integer",
              "minimum": 0,
              "maximum": 100000,
              "description": "active SKUs now in Багажные весы"
            },
            "accessories": {
              "type": "integer",
              "minimum": 0,
              "maximum": 100000,
              "description": "active SKUs now in Аксессуары для путешествий"
            }
          },
          "description": "active SKUs in the category now, per subcategory"
        },
        "active_skus_after": {
          "type": "integer",
          "minimum": 1,
          "maximum": 100000,
          "description": "sum of the six subcategory figures"
        },
        "ru_skus_after": {
          "type": "integer",
          "minimum": 0,
          "maximum": 100000,
          "description": "of the active SKUs now, those with Russia as supplier country"
        },
        "ru_share_after_pct": {
          "type": "integer",
          "minimum": 0,
          "maximum": 100,
          "description": "ru_skus_after as a percentage of active_skus_after, as slide 1 shows it"
        }
      },
      "description": "figures for slide 1"
    }
  },
  "description": "figures for the defence deck"
}
```
