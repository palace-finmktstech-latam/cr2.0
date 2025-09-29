# Trade Data Mapping Program

A Python-based command-line tool that transforms bank-specific CSV trade data into standardized JSON format for trade comparison.

## Overview

This program implements a flexible mapping engine that can transform trade data from various banks into a consistent JSON structure. It uses YAML configuration files to define bank-specific mapping rules, making it easy to add support for new banks without modifying the core code.

## Features

- **Field Mapping**: Maps CSV columns to standardized JSON fields
- **Value Transformation**: Converts bank-specific enums and formats to standard values
- **Leg Ordering**: Ensures consistent leg ordering (Receive=Leg[0], Pay=Leg[1])
- **Multi-Currency Support**: Handles FX fixing and settlement currencies
- **Conditional Logic**: Applies different mappings based on trade characteristics
- **Extensible Configuration**: Easy to add new banks via YAML config files

## Installation

Ensure Python 3.7+ is installed and install the required dependency:

```bash
pip install pyyaml
```

## Usage

### Basic Usage

```bash
python mapping_program.py \
  --input path/to/input_data.csv \
  --config path/to/bank_config.yaml \
  --output path/to/output.json
```

### With Verbose Logging

```bash
python mapping_program.py \
  --input 20250911_analytics.current_operations.csv \
  --config banco_internacional_config.yaml \
  --output output.json \
  --verbose
```

### Command Line Parameters

- `--input` / `-i`: Path to input CSV file (required)
- `--config` / `-c`: Path to YAML configuration file (required)
- `--output` / `-o`: Path for output JSON file (required)
- `--verbose` / `-v`: Enable verbose logging (optional)

## Configuration

The program uses YAML configuration files to define bank-specific mapping rules. See `banco_internacional_config.yaml` for a complete example.

### Key Configuration Sections

1. **Field Mappings**: Direct CSV column to JSON field mappings
2. **Leg Assignment**: Rules for determining which input leg becomes which output leg
3. **Value Transformations**: Conversion rules for enums and formats
4. **Conditional Mappings**: Different mappings based on trade characteristics
5. **Ignored Fields**: CSV columns to exclude from output

## Input Data Format

The program expects CSV input with trade data containing:

- Header information (trade ID, dates, counterparty)
- Leg-specific data (notionals, rates, currencies, calendars)
- Multi-currency information (FX fixing details)

### Key Input Fields

- `deal_number`: Trade identifier
- `trade_date.fecha`: Trade execution date
- `counterparty.name`: Counterparty name
- `legs[N].leg_generator.rp`: Leg role (A=receive, P=pay)
- `legs[N].type_of_leg`: Rate type (FIXED_RATE_MCCY, OVERNIGHT_INDEX_MCCY)
- `settlement_mechanism`: Settlement type (C=cash, E=physical)

## Output Format

The program generates a standardized JSON structure with:

```json
{
  "header": {
    "tradeId": "7555",
    "tradeIdType": "INTERNAL",
    "tradeDate": { "date": "11/09/2025", ... },
    "party1": { "partyId": "ThisBank", ... },
    "party2": { "partyId": "OurCounterparty", ... }
  },
  "legs": [
    {
      "legId": "Pata-Activa",
      "payerPartyReference": "OurCounterparty",
      "receiverPartyReference": "ThisBank",
      "rateType": "FLOATING",
      ...
    },
    {
      "legId": "Pata-Pasiva",
      "payerPartyReference": "ThisBank",
      "receiverPartyReference": "OurCounterparty",
      "rateType": "FIXED",
      ...
    }
  ]
}
```

## Key Transformations

### Leg Ordering
- Input legs are reordered based on the `rp` field
- Output leg[0] = Bank receives (counterparty pays)
- Output leg[1] = Bank pays (counterparty receives)

### Value Transformations
- Business centers: `NY-SCL` → `["USNY", "CLSA"]`
- Business day conventions: `MOD_FOLLOW` → `MODFOLLOWING`
- Rate types: `FIXED_RATE_MCCY` → `FIXED`
- Settlement types: `C` → `CASH`
- Day count fractions: `LIN_ACT/360` → `ACT/360`

### Period Calculations
- Converts years/months/days to standard frequency formats
- Detects zero-coupon trades and sets frequency to `TERM`
- Payment frequency defaults to `ATMATURITY` for term frequencies

## Examples

### Example 1: Single Trade Processing

```bash
python mapping_program.py \
  --input single_trade.csv \
  --config banco_internacional_config.yaml \
  --output trade_7555.json
```

### Example 2: Multiple Trades

```bash
python mapping_program.py \
  --input daily_trades.csv \
  --config banco_internacional_config.yaml \
  --output daily_output.json
```

## Error Handling

The program includes comprehensive error handling:

- **Invalid CSV**: Reports parsing errors with line numbers
- **Missing Fields**: Logs warnings for missing mandatory fields
- **Transformation Errors**: Continues processing other trades if one fails
- **Configuration Errors**: Validates YAML config on startup

## Adding New Banks

To add support for a new bank:

1. Create a new YAML configuration file based on `banco_internacional_config.yaml`
2. Define the bank-specific field mappings and transformations
3. Test with sample data from the new bank
4. No code changes required in the main program

## Files Generated

- `mapping_program.py`: Main transformation engine
- `banco_internacional_config.yaml`: Configuration for Banco Internacional
- `test_output.json`: Example output from sample data
- `single_trade_test.csv`: Test input with single trade

## Logging

The program provides detailed logging:
- **INFO**: High-level processing status
- **DEBUG**: Detailed transformation steps (use `--verbose`)
- **ERROR**: Failed transformations and validation errors
- **WARNING**: Missing optional fields

## Future Enhancements

- Support for JSON input format
- Schema validation for output JSON
- Web API interface
- GUI for configuration management
- Integration with data validation tools

## Support

For questions or issues with the mapping program, refer to:
- The mapping rules documentation (`banco-internacional-mapping-rules.md`)
- The program specification (`mapping_program_spec.md`)
- Sample input/output files for testing