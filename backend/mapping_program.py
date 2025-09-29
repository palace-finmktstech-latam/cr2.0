#!/usr/bin/env python3
"""
Trade Data Mapping Program

Transforms bank-specific CSV data into standardized JSON format for trade comparison.
"""

import csv
import json
import yaml
import argparse
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path


class TradeDataMapper:
    """Core mapping engine for transforming trade data."""

    def __init__(self, config_file: str, source: str = "banco"):
        """Initialize mapper with configuration file and source type."""
        self.config = self._load_config(config_file)
        self.source = source
        self.logger = self._setup_logging()

    def _load_config(self, config_file: str) -> Dict[str, Any]:
        """Load YAML configuration file."""
        with open(config_file, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    def _setup_logging(self) -> logging.Logger:
        """Setup logging configuration."""
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.INFO)

        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)

        return logger

    def transform_csv_to_json(self, input_file: str, output_file: str) -> None:
        """
        Main transformation function.
        Reads CSV, applies mappings, and writes standardized JSON.
        """
        self.logger.info(f"Starting transformation: {input_file} -> {output_file}")

        # Read CSV data
        trades_data = self._read_csv(input_file)

        # Transform each trade
        transformed_trades = []
        for trade_row in trades_data:
            transformed_trade = self._transform_single_trade(trade_row)
            if transformed_trade:
                transformed_trades.append(transformed_trade)

        # Write output JSON
        self._write_json(transformed_trades, output_file)

        self.logger.info(f"Transformation completed. Processed {len(transformed_trades)} trades.")

    def _read_csv(self, input_file: str) -> List[Dict[str, str]]:
        """Read CSV file and return list of dictionaries."""
        trades = []
        with open(input_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                trades.append(row)
        return trades

    def _transform_single_trade(self, trade_row: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """Transform a single trade from CSV row to standardized JSON format."""
        try:
            # Determine leg ordering based on rp fields
            leg_assignments = self._determine_leg_assignments(trade_row)

            # Build header section
            header = self._build_header(trade_row, leg_assignments)

            # Build legs section
            legs = self._build_legs(trade_row, leg_assignments)

            # Construct final trade object
            trade = {
                "header": header,
                "legs": legs
            }

            return trade

        except Exception as e:
            deal_number = trade_row.get('deal_number', 'No deal number')
            self.logger.error(f"Error transforming trade {deal_number}: {e}")
            return None

    def _determine_leg_assignments(self, trade_row: Dict[str, str]) -> Dict[str, Any]:
        """
        Determine which input leg becomes which output leg based on YAML config.
        Output leg[0] = bank receives (counterparty pays)
        Output leg[1] = bank pays (counterparty receives)
        """
        leg_assignment = self.config.get('leg_assignment', {})
        role_field_template = leg_assignment.get('role_field', 'legs[{idx}].leg_generator.rp')
        roles = leg_assignment.get('roles', {'receive': 'A', 'pay': 'P'})

        assignments = {
            'receive_leg_source': None,  # Which input leg index (0 or 1) is the receive leg
            'pay_leg_source': None,      # Which input leg index (0 or 1) is the pay leg
        }

        # Check both legs
        for leg_idx in [0, 1]:
            role_field = role_field_template.format(idx=leg_idx)
            leg_role_value = trade_row.get(role_field)

            if leg_role_value == roles['receive']:
                assignments['receive_leg_source'] = leg_idx
            elif leg_role_value == roles['pay']:
                assignments['pay_leg_source'] = leg_idx

        return assignments

    def _build_header(self, trade_row: Dict[str, str], leg_assignments: Dict[str, Any]) -> Dict[str, Any]:
        """Build the header section of the output JSON from YAML config."""
        header_mappings = self.config.get('header_mappings', {})
        header = {}

        receive_leg_idx = leg_assignments['receive_leg_source']

        for field_name, field_config in header_mappings.items():
            header[field_name] = self._process_field_mapping(
                field_config, trade_row, leg_assignments, receive_leg_idx=receive_leg_idx
            )

        return header

    def _process_field_mapping(self, field_config: Any, trade_row: Dict[str, str],
                             leg_assignments: Dict[str, Any], **context) -> Any:
        """Process a field mapping configuration to extract/transform data."""

        # Handle static values
        if isinstance(field_config, dict) and 'static_value' in field_config:
            return field_config['static_value']

        # Handle dynamic values (like source parameter)
        if isinstance(field_config, dict) and 'dynamic_value' in field_config:
            if field_config['dynamic_value'] == 'source_parameter':
                return self.source

        # Handle simple source field mapping (but not if fallback_source is also present)
        if isinstance(field_config, dict) and 'source_field' in field_config and 'fallback_source' not in field_config:
            source_field = field_config['source_field']
            # Handle template variables
            source_field = self._resolve_field_template(source_field, leg_assignments, **context)

            value = trade_row[source_field]

            # Apply transformation if specified
            if 'transformation' in field_config:
                value = self._apply_transformation(value, field_config['transformation'])

            return value

        # Handle source_fields with primary/fallback
        if isinstance(field_config, dict) and 'source_fields' in field_config:
            source_fields = field_config['source_fields']

            # Handle calculation type (for period calculations)
            if 'calculation_type' in field_config:
                return self._calculate_period_value(
                    source_fields, field_config['calculation_type'], trade_row, **context
                )

            # Handle primary/fallback pattern
            if isinstance(source_fields, dict) and 'primary' in source_fields:
                primary_field = self._resolve_field_template(source_fields['primary'], leg_assignments, **context)

                try:
                    value = trade_row[primary_field]
                    if value:  # If primary value exists and is not empty
                        if 'transformation' in field_config:
                            value = self._apply_transformation(value, field_config['transformation'])
                        return value
                except KeyError:
                    pass

                # Try fallback
                if 'fallback' in source_fields:
                    fallback_field = self._resolve_field_template(source_fields['fallback'], leg_assignments, **context)
                    value = trade_row[fallback_field]
                    if 'transformation' in field_config:
                        value = self._apply_transformation(value, field_config['transformation'])
                    return value

        # Handle fallback_source
        if isinstance(field_config, dict) and 'fallback_source' in field_config:
            # Try primary source field first
            if 'source_field' in field_config:
                try:
                    source_field = self._resolve_field_template(field_config['source_field'], leg_assignments, **context)
                    value = trade_row.get(source_field)
                    if value:  # If value exists and is not empty
                        return value
                except (KeyError, TypeError):
                    pass

            # Use fallback
            fallback_field = self._resolve_field_template(field_config['fallback_source'], leg_assignments, **context)
            return trade_row[fallback_field]

        # Handle reference_field (referencing other output fields)
        if isinstance(field_config, dict) and 'reference_field' in field_config:
            ref_path = field_config['reference_field']
            leg_object = context.get('leg_object', {})

            # Navigate the reference path
            current = leg_object
            for part in ref_path.split('.'):
                if isinstance(current, dict) and part in current:
                    current = current[part]
                else:
                    # Return default if reference not found
                    return ["CLSA"]

            return current

        # Handle nested object mappings
        if isinstance(field_config, dict) and not any(key in field_config for key in
                                                     ['source_field', 'static_value', 'dynamic_value', 'source_fields']):
            result = {}
            for sub_field, sub_config in field_config.items():
                result[sub_field] = self._process_field_mapping(sub_config, trade_row, leg_assignments, **context)
            return result

        # Handle leg role-based values
        if isinstance(field_config, dict) and 'receive_leg' in field_config:
            leg_idx = context.get('leg_idx')
            is_receive = context.get('is_receive', False)

            if is_receive:
                return field_config.get('receive_leg')
            else:
                return field_config.get('pay_leg')

        return field_config

    def _resolve_field_template(self, field_template: str, leg_assignments: Dict[str, Any], **context) -> str:
        """Resolve template variables in field names."""
        if '{receive_leg_idx}' in field_template:
            receive_leg_idx = leg_assignments.get('receive_leg_source', 0)
            field_template = field_template.replace('{receive_leg_idx}', str(receive_leg_idx))

        if '{idx}' in field_template and 'leg_idx' in context:
            field_template = field_template.replace('{idx}', str(context['leg_idx']))

        return field_template

    def _calculate_period_value(self, source_fields: Dict[str, str], calc_type: str,
                              trade_row: Dict[str, str], **context) -> str:
        """Calculate period frequency values from years/months/days."""
        leg_idx = context.get('leg_idx', 0)

        # Resolve field templates
        years_field = self._resolve_field_template(source_fields['years'], {}, leg_idx=leg_idx)
        months_field = self._resolve_field_template(source_fields['months'], {}, leg_idx=leg_idx)
        days_field = self._resolve_field_template(source_fields['days'], {}, leg_idx=leg_idx)

        years = int(trade_row[years_field])
        months = int(trade_row[months_field])
        days = int(trade_row[days_field])

        # Apply existing calculation logic
        if years >= 25:  # Zero coupon threshold
            if calc_type == 'payment_frequency':
                return "ATMATURITY"
            return "TERM"

        total_months = years * 12 + months

        if total_months == 0 and days == 0:
            if calc_type == 'payment_frequency':
                return "ATMATURITY"
            return "TERM"

        # Try to determine if this period represents the entire trade duration
        if 'start_date' in source_fields and 'end_date' in source_fields:
            try:
                start_field = self._resolve_field_template(source_fields['start_date'], {}, leg_idx=leg_idx)
                end_field = self._resolve_field_template(source_fields['end_date'], {}, leg_idx=leg_idx)

                start_date_str = trade_row[start_field]
                end_date_str = trade_row[end_field]

                start_dt = datetime.strptime(start_date_str, '%Y-%m-%d')
                end_dt = datetime.strptime(end_date_str, '%Y-%m-%d')
                trade_months = (end_dt.year - start_dt.year) * 12 + (end_dt.month - start_dt.month)

                if total_months >= trade_months - 1:  # Allow 1 month tolerance
                    if calc_type == 'payment_frequency':
                        return "ATMATURITY"
                    return "TERM"
            except:
                pass

        # Convert to standard frequency format
        if years > 0:
            return f"{years}Y"
        elif months > 0:
            return f"{months}M"
        elif days > 0:
            return f"{days}D"
        else:
            if calc_type == 'payment_frequency':
                return "ATMATURITY"
            return "TERM"

    def _build_legs(self, trade_row: Dict[str, str], leg_assignments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Build the legs section of the output JSON from YAML config."""
        legs = []

        # Build receive leg (output leg[0]) - hardcoded as Pata-Activa
        receive_leg_idx = leg_assignments['receive_leg_source']
        if receive_leg_idx is not None:
            # Start with hardcoded leg mapping fields at the beginning
            receive_leg = {
                "legId": "Pata-Activa",
                "payerPartyReference": "OurCounterparty",
                "receiverPartyReference": "ThisBank"
            }
            # Add the rest of the leg configuration
            additional_fields = self._build_single_leg_from_config(trade_row, receive_leg_idx, True, leg_assignments)
            receive_leg.update(additional_fields)
            legs.append(receive_leg)

        # Build pay leg (output leg[1]) - hardcoded as Pata-Pasiva
        pay_leg_idx = leg_assignments['pay_leg_source']
        if pay_leg_idx is not None:
            # Start with hardcoded leg mapping fields at the beginning
            pay_leg = {
                "legId": "Pata-Pasiva",
                "payerPartyReference": "ThisBank",
                "receiverPartyReference": "OurCounterparty"
            }
            # Add the rest of the leg configuration
            additional_fields = self._build_single_leg_from_config(trade_row, pay_leg_idx, False, leg_assignments)
            pay_leg.update(additional_fields)
            legs.append(pay_leg)

        return legs

    def _build_single_leg_from_config(self, trade_row: Dict[str, str], leg_idx: int,
                                    is_receive: bool, leg_assignments: Dict[str, Any]) -> Dict[str, Any]:
        """Build a single leg object from YAML configuration."""
        leg_mappings = self.config.get('leg_mappings', {})
        leg = {}

        # Process all leg mappings
        for field_name, field_config in leg_mappings.items():
            leg[field_name] = self._process_field_mapping(
                field_config, trade_row, leg_assignments,
                leg_idx=leg_idx, is_receive=is_receive
            )

        # Process conditional mappings
        conditional_mappings = self.config.get('conditional_leg_mappings', {})
        for condition_name, condition_config in conditional_mappings.items():
            if self._check_condition(condition_config.get('condition', ''), trade_row, leg_idx):
                # Apply conditional fields
                conditional_fields = condition_config.get('fields', {})
                for field_name, field_config in conditional_fields.items():
                    leg[field_name] = self._process_field_mapping(
                        field_config, trade_row, leg_assignments,
                        leg_idx=leg_idx, is_receive=is_receive, leg_object=leg
                    )

        return leg

    def _check_condition(self, condition: str, trade_row: Dict[str, str], leg_idx: int) -> bool:
        """Check if a conditional mapping condition is met."""
        if not condition:
            return False

        # Handle the condition format: "legs[{idx}].type_of_leg in ['FIXED_RATE_MCCY', 'FIXED_RATE']"
        condition = condition.replace('{idx}', str(leg_idx))

        # Simple condition checking - can be enhanced
        if ' in [' in condition:
            field_part, values_part = condition.split(' in [')
            field_name = field_part.strip()
            values_str = values_part.rstrip(']')

            # Parse values list
            import re
            values = re.findall(r"'([^']*)'", values_str)

            field_value = trade_row.get(field_name)
            return field_value in values

        # Handle "is not empty" condition
        if ' is not empty' in condition:
            field_name = condition.replace(' is not empty', '').strip()
            field_value = trade_row.get(field_name)
            return field_value is not None and field_value != ''

        return False

    def _apply_transformation(self, value: Any, transformation_type: str) -> Any:
        """Apply a transformation to a value based on YAML config."""
        transformations = self.config.get('transformations', {})

        if transformation_type == 'date_format':
            return self._transform_date(value)
        elif transformation_type == 'integer':
            return int(value)
        elif transformation_type == 'float':
            return float(value)
        elif transformation_type == 'notional':
            return self._transform_notional(value)
        elif transformation_type == 'fx_fixing_lag':
            # Special handling for fx_fixing_lag which has custom logic
            mapping = transformations.get(transformation_type, {})
            if str(value) in mapping:
                return mapping[str(value)]
            else:
                return int(value) if value else 0
        elif transformation_type in transformations:
            mapping = transformations[transformation_type]
            if value not in mapping:
                raise ValueError(f"Unknown {transformation_type}: {value}")
            return mapping[value]
        else:
            raise ValueError(f"Unknown transformation type: {transformation_type}")

    # Note: Old _build_single_leg method removed - now using YAML-driven approach

    def _calculate_period_frequency(self, trade_row: Dict[str, str], leg_idx: int, period_type: str) -> str:
        """Calculate period frequency from years, months, and days."""
        years = int(trade_row[f'legs[{leg_idx}].leg_generator.{period_type}.agnos'])
        months = int(trade_row[f'legs[{leg_idx}].leg_generator.{period_type}.meses'])
        days = int(trade_row[f'legs[{leg_idx}].leg_generator.{period_type}.dias'])

        # Parse trade start and end dates to calculate actual term
        start_date_str = trade_row[f'legs[{leg_idx}].leg_generator.start_date.fecha']
        end_date_str = trade_row[f'legs[{leg_idx}].leg_generator.end_date.fecha']

        # If the period is longer than or equal to the trade term, it's a zero coupon (TERM)
        if years >= 25:  # Arbitrary threshold for zero coupon
            return "TERM"

        # Calculate total months to compare with trade term
        total_months = years * 12 + months

        # For very short periods or if the period spans the entire trade, use TERM
        if total_months == 0 and days == 0:
            return "TERM"

        # Try to determine if this period represents the entire trade duration
        if start_date_str and end_date_str:
            try:
                from datetime import datetime
                start_dt = datetime.strptime(start_date_str, '%Y-%m-%d')
                end_dt = datetime.strptime(end_date_str, '%Y-%m-%d')
                trade_months = (end_dt.year - start_dt.year) * 12 + (end_dt.month - start_dt.month)

                # If the period is close to the trade duration, it's likely TERM
                if total_months >= trade_months - 1:  # Allow 1 month tolerance
                    return "TERM"
            except:
                pass  # If date parsing fails, continue with normal logic

        # Convert to standard frequency format
        if years > 0:
            return f"{years}Y"
        elif months > 0:
            return f"{months}M"
        elif days > 0:
            return f"{days}D"
        else:
            return "TERM"

    # Value transformation methods
    def _transform_date(self, date_str: str) -> str:
        """Transform date based on input format specified in config to DD/MM/YYYY format."""
        if not date_str:
            return ""

        # Get input date format from config, default to YYYY-MM-DD
        input_date_format = self.config.get('date_format', 'YYYY-MM-DD')

        # Map config format to strptime format
        format_mapping = {
            'YYYY-MM-DD': '%Y-%m-%d',
            'DD/MM/YYYY': '%d/%m/%Y',
            'MM/DD/YYYY': '%m/%d/%Y',
            'YYYY/MM/DD': '%Y/%m/%d'
        }

        input_format = format_mapping.get(input_date_format, '%Y-%m-%d')

        try:
            from datetime import datetime
            dt = datetime.strptime(date_str, input_format)
            return dt.strftime('%d/%m/%Y')  # Always output DD/MM/YYYY
        except ValueError:
            # Try alternative formats if the configured one fails
            alternative_formats = ['%d/%m/%Y', '%Y-%m-%d', '%m/%d/%Y', '%Y/%m/%d']
            for alt_format in alternative_formats:
                if alt_format != input_format:  # Don't retry the same format
                    try:
                        dt = datetime.strptime(date_str, alt_format)
                        self.logger.warning(f"Date {date_str} parsed with alternative format {alt_format} instead of configured {input_date_format}")
                        return dt.strftime('%d/%m/%Y')
                    except ValueError:
                        continue

            # If all parsing fails, log warning and return as-is
            self.logger.warning(f"Could not parse date: {date_str}")
            return date_str

    def _transform_business_centers(self, calendar_str: str) -> List[str]:
        """Transform business center codes to standard format."""
        if not calendar_str:
            return ["CLSA"]

        mapping = {
            "NY": "USNY",
            "SCL": "CLSA",
            "LON": "GBLO",
            "NY-SCL": ["USNY", "CLSA"],
            "LON-SCL": ["GBLO", "CLSA"],
            "NY-LON-SCL": ["USNY", "GBLO", "CLSA"]
        }

        if calendar_str not in mapping:
            raise ValueError(f"Unknown business center calendar: {calendar_str}")
        result = mapping[calendar_str]
        return result if isinstance(result, list) else [result]

    def _transform_business_day_convention(self, convention_str: str) -> str:
        """Transform business day convention codes."""
        mapping = {
            "MOD_FOLLOW": "MODFOLLOWING",
            "FOLLOW": "FOLLOWING",
            "DONT_MOVE": "NONE"
        }
        if convention_str not in mapping:
            raise ValueError(f"Unknown business day convention: {convention_str}")
        return mapping[convention_str]

    def _transform_rate_type(self, leg_type_str: str) -> str:
        """Transform leg type to rate type."""
        if leg_type_str in ["FIXED_RATE_MCCY", "FIXED_RATE"]:
            return "FIXED"
        elif leg_type_str in ["OVERNIGHT_INDEX_MCCY", "OVERNIGHT_INDEX"]:
            return "FLOATING"
        else:
            return "FIXED"  # Default

    def _transform_day_count_fraction(self, day_count_str: str) -> str:
        """Transform day count fraction codes."""
        mapping = {
            "LIN_ACT/360": "ACT/360"
        }
        if day_count_str not in mapping:
            raise ValueError(f"Unknown day count fraction: {day_count_str}")
        return mapping[day_count_str]

    def _transform_floating_rate_index(self, index_str: str) -> str:
        """Transform floating rate index codes."""
        mapping = {
            "ICPCLP": "CLP-ICP"
        }
        if index_str not in mapping:
            raise ValueError(f"Unknown floating rate index: {index_str}")
        return mapping[index_str]

    def _transform_settlement_type(self, settlement_str: str) -> str:
        """Transform settlement mechanism codes."""
        mapping = {
            "C": "CASH",
            "E": "PHYSICAL"
        }
        if settlement_str not in mapping:
            raise ValueError(f"Unknown settlement mechanism: {settlement_str}")
        return mapping[settlement_str]

    def _transform_fx_rate_index(self, fx_index_str: str) -> str:
        """Transform FX rate index codes."""
        mapping = {
            "USDOBS": "CLP_DOLAR_OBS_CLP10"
        }
        if fx_index_str not in mapping:
            raise ValueError(f"Unknown FX rate index: {fx_index_str}")
        return mapping[fx_index_str]

    def _transform_fx_fixing_lag(self, lag_str: str) -> int:
        """Transform FX fixing lag."""
        if lag_str == "1":
            return -2  # As specified in the mapping rules
        return int(lag_str) if lag_str else 0

    def _transform_fx_fixing_pivot(self, pivot_str: str) -> str:
        """Transform FX fixing pivot."""
        mapping = {
            "SETTLEMENT_DATE": "PAYMENT_DATES"
        }
        if pivot_str not in mapping:
            raise ValueError(f"Unknown FX fixing pivot: {pivot_str}")
        return mapping[pivot_str]

    def _transform_notional(self, notional_str: str) -> float:
        """Transform notional amount to float."""
        if not notional_str:
            raise ValueError("Notional amount cannot be empty")

        # Remove any thousands separators and convert to float
        clean_str = notional_str.replace(',', '').replace(' ', '')
        return float(clean_str)

    def _write_json(self, trades: List[Dict[str, Any]], output_file: str) -> None:
        """Write transformed trades to JSON file."""
        # Always wrap trades in a 'trades' object for consistency
        output_data = {"trades": trades}

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)


def main():
    """Main CLI function."""
    parser = argparse.ArgumentParser(
        description="Transform bank-specific CSV trade data to standardized JSON format"
    )
    parser.add_argument(
        "--input", "-i",
        required=True,
        help="Input CSV file path"
    )
    parser.add_argument(
        "--config", "-c",
        required=True,
        help="Configuration YAML file path"
    )
    parser.add_argument(
        "--output", "-o",
        required=True,
        help="Output JSON file path"
    )
    parser.add_argument(
        "--source", "-s",
        required=True,
        choices=["banco", "contrato"],
        help="Source type: banco or contrato"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )

    args = parser.parse_args()

    # Setup logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    try:
        # Initialize mapper
        mapper = TradeDataMapper(args.config, args.source)

        # Perform transformation
        mapper.transform_csv_to_json(args.input, args.output)

        print(f"Transformation completed successfully!")
        print(f"Output written to: {args.output}")

    except Exception as e:
        print(f"Error during transformation: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())