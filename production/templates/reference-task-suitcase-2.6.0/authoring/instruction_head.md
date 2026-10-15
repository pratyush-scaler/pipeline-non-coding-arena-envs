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
