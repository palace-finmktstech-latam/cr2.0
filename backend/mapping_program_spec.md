
# 📄 Trade Data Mapping Program Specification

## 🧭 Purpose

This specification defines a Python-based command-line program that transforms client-specific trade data (e.g., CSV or JSON) into a standardized nested JSON format. It uses bank-specific configuration files to:
- Map and rename fields
- Apply format and value transformations
- Normalize leg order
- Handle multiple trades per file
- Output a consistent, structured result

The tool is the first step in Ben Clark’s contract-to-trade comparison system for interest rate swaps (IRS), enabling standardized ingestion of trade data from multiple bank formats.

---

## ⚙️ Features

### ✅ Supported Features
- Field name mapping
- Field value transformations (e.g., enums, date formats, decimal separators)
- Leg ordering normalization (Receive = Leg 1, Pay = Leg 2)
- Trade type conditional logic (e.g., extra fields for cross-currency swaps)
- Nested JSON output structure
- Handling multiple trades in one input file
- Command-line interface (CLI)

---

## 🧪 Example CLI Usage

```bash
python mapping_program.py \
  --input ./client_data/itau_irs_2024-09.csv \
  --config ./configs/itau_config.yaml \
  --output ./standardized/output_itau_2024-09.json
```

---

## 🗃️ Input & Output

### Input
- Format: CSV or JSON
- Content: Multiple trades, possibly in raw or inconsistent formats
- Fields: Vary depending on the bank

### Output
- Format: JSON
- Content: A single file with a list of transformed trade objects
- Structure: Nested fields (contract-level + leg-level)

---

## 🧩 Output JSON Structure

```json
{
  "trades": [
    {
      "executionDate": "2024-09-15",
      "tradeType": "InterestRateSwap",
      "legs": [
        {
          "role": "Receive",
          "currency": "CLP",
          "notional": 47500000000,
          "rate": 6.25,
          "businessDayConvention": "ModFollow",
          "calendar": ["USNY"]
        },
        {
          "role": "Pay",
          "currency": "USD",
          "notional": 50000000,
          "rate": 5.10,
          "businessDayConvention": "ModFollow",
          "calendar": ["USNY"]
        }
      ],
      "terminationDate": "2027-09-15"
    }
  ]
}
```

---

## 🛠️ Configuration File Format

The config file is written in YAML (or JSON) and contains:

### 🔗 Field Mappings

```yaml
field_mappings:
  TradeDate: executionDate
  Termination: terminationDate
  ReceiveNotional: legs[0].notional
  PayNotional: legs[1].notional
```

### 🔀 Leg Reordering Rules

Ensure leg[0] is always the receiving leg (asset leg), and leg[1] is always the paying leg (liability leg), using keywords in field names or logic like:

```yaml
leg_order:
  identify_by_field: role
  normalize_order:
    - Receive
    - Pay
```

### 🔄 Value Transformations

```yaml
value_transformations:
  business_centers:
    NY: USNY
    SCL: CLSA
    NY-SCL: [USNY, CLSA]
  business_day_conventions:
    Modified_Following: ModFollow
    Following: Foll
  decimal_separator: comma_to_point
  date_format:
    input: "%d/%m/%Y"
    output: "%Y-%m-%d"
```

### 🧠 Trade-Type Specific Logic

```yaml
trade_type_rules:
  CrossCurrencySwap:
    optional_fields:
      - fxResettingNotional
      - foreignCurrencyRate
```

### 🪜 Nesting Instructions (Optional)

Only if flat source data needs to be nested:

```yaml
nesting_structure:
  root: trade
  fields:
    executionDate: trade.executionDate
    leg1.currency: trade.legs[0].currency
    leg2.currency: trade.legs[1].currency
```

---

## 🔁 Processing Flow

1. **Parse CLI arguments**
2. **Load configuration file**
3. **Read input file**
4. **Iterate over trades**
    - Map and rename fields
    - Normalize leg order
    - Transform field values (e.g., enums, dates)
    - Apply trade-type rules
    - Build nested JSON object
5. **Write all trades to a single output JSON file**

---

## 🧪 Future Enhancements

- API endpoint (FastAPI or Flask) to replace CLI
- GUI wrapper for local teams
- Schema validation for JSON output
- Integration with Palace Knowledge Graph for label/enum mapping

---

## 🏁 Example Output Filename Convention

```text
output_<bankname>_<YYYY-MM-DD>.json
e.g. output_itau_2025-09-19.json
```

---

## 📝 Notes

- The config system is designed to evolve as new clients/banks are added.
- Reusability is a core design principle: one core Python engine, many lightweight config files.

---
