# How to prepare a CSV dataset for QAlityDeep (Streamlit)

## Required column

| Column     | Description |
|-----------|-------------|
| **prompt** | The input question or instruction you send to your AI (required). |

## Optional columns

| Column               | Description |
|----------------------|-------------|
| **id**               | Row identifier (e.g. 1, 2, 3 or test_01). If missing, row index is used. |
| **expected_output**  | Ideal or acceptable model answer. Used for correctness/relevancy metrics. |
| **expected_tool_calls** | JSON array of tools that should be called. Used for tool_correctness. |
| **agent_trace** / **trace_json** | Pre-recorded trajectory (JSON). Optional; usually left empty when running evals. |

## CSV format rules

- **Encoding**: UTF-8.
- **Delimiter**: Comma (`,`).
- **Quotes**: Use double quotes (`"`) around any field that contains commas, newlines, or double quotes. Inside a quoted field, escape a double quote as `""`.
- **expected_tool_calls**: Must be a **JSON string** (one per row). Valid examples:
  - Empty / no tools: leave cell empty or `[]`
  - One tool: `[{"name": "search_policy", "input": {"query": "refund"}}]`
  - Several tools: `[{"name": "get_history", "input": {"id": "C001"}}, {"name": "check_policy", "input": {}}]`
  - Optional keys: `name` (required), `input` (object), `output` (optional).

## Example (minimal)

```csv
id,prompt,expected_output
1,"What is your refund policy?","We offer a 30-day full refund."
2,"How long does shipping take?","Standard shipping is 3-5 business days."
```

## Example (with tool correctness)

```csv
id,prompt,expected_output,expected_tool_calls
1,"Check returns for customer C001","Customer C001: 3 returns in 90 days; flag for review.","[{\"name\": \"get_return_history\", \"input\": {\"customer_id\": \"C001\"}}]"
2,"Risk level for order ORD-789","High risk: 2 policy violations.","[{\"name\": \"get_order_risk\", \"input\": {\"order_id\": \"ORD-789\"}}]"
```

## PinchAI-style example

```csv
id,prompt,expected_output,expected_tool_calls
1,"Did customer C001 misuse the return policy?","Yes. 12 returns in 6 months; recommend flag.","[{\"name\": \"get_return_history\", \"input\": {\"customer_id\": \"C001\"}}]"
2,"Return abuse signals for user@example.com","2 excessive returns; 1 late return; flag for review.","[]"
```

Save as `.csv`, then in Streamlit: **Datasets** → Upload file → (optional) name/description → **Save dataset**. Then **Current run** → select dataset → choose metrics → **Run evaluation**.
