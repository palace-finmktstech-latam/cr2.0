import json
import pandas as pd
from typing import Any, Dict, List, Tuple, Union, Optional
import os
import re
from datetime import datetime
import argparse
import glob
from pathlib import Path

# For PDF generation
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.platypus.tableofcontents import TableOfContents
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.pdfgen import canvas

class JSONComparator:
    def __init__(self, translations_file: Optional[str] = None):
        self.differences = []
        self.stats = {
            'added': 0,
            'removed': 0,
            'modified': 0,
            'type_changed': 0
        }
        self.translations = self.load_translations(translations_file) if translations_file else {}
    
    def flatten_json(self, data: Any, parent_key: str = '', sep: str = '.') -> Dict[str, Any]:
        """
        Flatten a nested JSON structure into dot-notation keys
        """
        items = []
        
        if isinstance(data, dict):
            for key, value in data.items():
                new_key = f"{parent_key}{sep}{key}" if parent_key else key
                if isinstance(value, (dict, list)):
                    items.extend(self.flatten_json(value, new_key, sep=sep).items())
                else:
                    items.append((new_key, value))
        elif isinstance(data, list):
            for i, value in enumerate(data):
                new_key = f"{parent_key}[{i}]"
                if isinstance(value, (dict, list)):
                    items.extend(self.flatten_json(value, new_key, sep=sep).items())
                else:
                    items.append((new_key, value))
        else:
            return {parent_key: data}
        
        return dict(items)
    
    def load_translations(self, translations_file: str) -> Dict[str, str]:
        """
        Load path translations from JSON file
        Expected format: {"path.to.field": "User Friendly Description", ...}
        """
        try:
            with open(translations_file, 'r', encoding='utf-8') as f:
                translations = json.load(f)
                print(f"Loaded {len(translations)} path translations")
                return translations
        except FileNotFoundError:
            print(f"Warning: Translation file not found: {translations_file}")
            return {}
        except json.JSONDecodeError as e:
            print(f"Warning: Invalid JSON in translation file {translations_file}: {e}")
            return {}
    
    def get_friendly_description(self, path: str) -> str:
        """
        Get friendly description for a path, with fallback logic for partial matches
        """
        # Try exact match first
        if path in self.translations:
            return self.translations[path]
        
        # Replace specific array indices with [*] for generic matching
        import re
        generic_path = re.sub(r'\[\d+\]', '[*]', path)
        if generic_path in self.translations:
            return self.translations[generic_path]
        
        # Try without array notation entirely
        no_array_path = re.sub(r'\[\d+\]', '', path)
        if no_array_path in self.translations:
            return self.translations[no_array_path]
        
        # Look for partial matches (longest match wins)
        best_match = ""
        best_description = ""
        for trans_path, description in self.translations.items():
            if trans_path in path and len(trans_path) > len(best_match):
                best_match = trans_path
                best_description = description
        
        return best_description if best_description else path
    
    def compare_values(self, key: str, val1: Any, val2: Any) -> str:
        """
        Compare two values and return the type of difference
        """
        if val1 is None and val2 is not None:
            return 'added'
        elif val1 is not None and val2 is None:
            return 'removed'
        elif type(val1) != type(val2):
            return 'type_changed'
        elif val1 != val2:
            return 'modified'
        else:
            return 'same'
    
    def compare_jsons(self, json1: Dict[str, Any], json2: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Compare two JSON objects and return list of differences
        """
        # Reset stats for this comparison
        self.stats = {'added': 0, 'removed': 0, 'modified': 0, 'type_changed': 0}
        
        # Flatten both JSONs
        flat1 = self.flatten_json(json1)
        flat2 = self.flatten_json(json2)
        
        # Get all unique keys from both JSONs
        all_keys = set(flat1.keys()) | set(flat2.keys())
        
        differences = []
        
        # Path to suppress - this is expected to always differ and not useful for users
        suppressed_path = "trade.tradeIdentifier[0].assignedIdentifier[0].identifier.value"
        
        for key in sorted(all_keys):
            # Skip the suppressed path
            if key == suppressed_path:
                continue
                
            val1 = flat1.get(key)
            val2 = flat2.get(key)
            
            diff_type = self.compare_values(key, val1, val2)
            
            if diff_type != 'same':
                self.stats[diff_type] += 1
                friendly_desc = self.get_friendly_description(key)
                differences.append({
                    'path': key,
                    'friendly_description': friendly_desc,
                    'difference_type': diff_type,
                    'su_input_valor': str(val1) if val1 is not None else "No registrado",
                    'contrato_input_valor': str(val2) if val2 is not None else "No registrado",
                    'su_input_tipo': type(val1).__name__ if val1 is not None else None,
                    'contrato_input_tipo': type(val2).__name__ if val2 is not None else None
                })
        
        return differences
    
    def load_json_file(self, filepath: str) -> Dict[str, Any]:
        """
        Load JSON from file with error handling
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"File not found: {filepath}")
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in file {filepath}: {e}")

class FilenameParsed:
    def __init__(self, filename: str):
        self.filename = filename
        self.parse_filename()

    def parse_filename(self):
        """
        Parse filename following the new conventions:

        For contrato files:
        Output_<counterparty_trade_id>_<this_bank>_<counterparty_name>_<date>_contrato_<filename_of_contract>.json
        Example: Output_61745_Banco-ABC_SCOTIABANK-CHILE_17092025_contrato_7557-61745.json

        For banco files:
        Output_<counterparty_trade_id>_<this_bank>_<counterparty_name>_<date>_banco.json
        Example: Output_7557_Banco-ABC_SCOTIABANK-CHILE_17092025_banco.json
        """
        basename = os.path.basename(self.filename)
        if not basename.startswith('Output_') or not basename.endswith('.json'):
            raise ValueError(f"Filename {basename} doesn't follow expected convention")

        # Remove Output_ prefix and .json suffix
        parts = basename[7:-5].split('_')  # Remove 'Output_' and '.json'

        if len(parts) < 5:
            raise ValueError(f"Filename {basename} doesn't have enough parts (minimum 5)")

        self.counterparty_trade_id = parts[0]
        self.this_bank = parts[1]
        self.counterparty_name = parts[2]
        self.date_str = parts[3]
        self.file_type = parts[4]  # banco or contrato

        # For contrato files, there may be additional parts for the contract filename
        if self.file_type == 'contrato' and len(parts) > 5:
            self.contract_filename = '_'.join(parts[5:])  # Join remaining parts
        else:
            self.contract_filename = "Unknown"

        # Parse date - expecting DDMMYYYY format
        try:
            self.date = datetime.strptime(self.date_str, '%d%m%Y')
        except ValueError:
            raise ValueError(f"Invalid date format in filename: {self.date_str}")

    def get_formatted_date(self) -> str:
        return self.date.strftime('%d/%m/%Y')

    def get_match_key(self) -> str:
        """Generate a key for matching banco and contrato files"""
        return f"{self.counterparty_trade_id}_{self.this_bank}_{self.counterparty_name}_{self.date_str}"

class PDFReportGenerator:
    def __init__(self, logo_path: Optional[str] = None):
        self.logo_path = logo_path
        self.styles = getSampleStyleSheet()
        self.setup_custom_styles()
    
    def setup_custom_styles(self):
        """Setup custom paragraph styles with Manrope font"""
        # Register Manrope font (fallback to Helvetica if not available)
        try:
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont
            # Try to register Manrope if available, otherwise use Helvetica
            font_name = 'Helvetica'  # Default fallback
        except:
            font_name = 'Helvetica'
        
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Title'],
            fontSize=16,
            spaceAfter=30,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#2c3e50'),
            fontName=font_name
        ))
        
        self.styles.add(ParagraphStyle(
            name='CustomHeading',
            parent=self.styles['Heading2'],
            fontSize=12,
            spaceAfter=12,
            textColor=colors.HexColor('#34495e'),
            fontName=font_name
        ))
        
        self.styles.add(ParagraphStyle(
            name='CustomBody',
            parent=self.styles['Normal'],
            fontSize=7,  # Smaller font size
            spaceAfter=6,
            alignment=TA_LEFT,
            fontName=font_name
        ))
        
        self.styles.add(ParagraphStyle(
            name='TableHeader',
            parent=self.styles['Normal'],
            fontSize=7,  # Smaller font size
            alignment=TA_CENTER,
            textColor=colors.white,  # White text
            fontName='Helvetica-Bold'  # Bold font
        ))
    
    def create_intro_text(self) -> str:
        return """
        A continuación, se encuentra un resumen de las operaciones procesadas por el Servicio de 
        Revisión de Contratos. Este servicio compara los contratos recibidos por el servicio con 
        los detalles de la operación registrada en su sistema y proporcionada al servicio de Palace.

        Se enumeran las diferencias detectadas para cada operación procesada:
        """
    
    def generate_pdf_report(self, trade_results: List[Dict], output_path: str):
        """Generate comprehensive PDF report"""
        
        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=3*cm,
            bottomMargin=2*cm
        )
        
        story = []
        
        # Logo (if provided)
        if self.logo_path and os.path.exists(self.logo_path):
            try:
                from PIL import Image as PILImage
                
                # Open image to get actual dimensions
                with PILImage.open(self.logo_path) as pil_img:
                    img_width, img_height = pil_img.size
                    
                    # Set target size - not too big to avoid quality loss
                    target_width = 5*cm  # Reduced from 6cm
                    target_height = 2.5*cm  # Reduced from 3cm
                    
                    # Calculate scaling factor to maintain aspect ratio
                    width_scale = target_width / (img_width * 72/300)  # Convert to points
                    height_scale = target_height / (img_height * 72/300)
                    scale = min(width_scale, height_scale)
                    
                    # Don't upscale if image is smaller - this preserves quality
                    if scale > 1:
                        scale = 1
                    
                    final_width = (img_width * 72/300) * scale
                    final_height = (img_height * 72/300) * scale
                
                logo = Image(self.logo_path, width=final_width, height=final_height)
                logo.hAlign = 'CENTER'
                story.append(logo)
                story.append(Spacer(1, 20))
                
            except ImportError:
                # Fallback if PIL not available
                logo = Image(self.logo_path, width=5*cm, height=2.5*cm)
                logo.hAlign = 'CENTER'
                story.append(logo)
                story.append(Spacer(1, 20))
            except Exception as e:
                print(f"Warning: Could not load logo from {self.logo_path}: {e}")
        
        # Title
        title = Paragraph("Reporte de Servicio de Revisión de Contratos", self.styles['CustomTitle'])
        story.append(title)
        story.append(Spacer(1, 20))
        
        # Report date
        report_date = Paragraph(
            f"<b>Fecha de generación del reporte:</b> {datetime.now().strftime('%d de %B de %Y a las %H:%M')}",
            self.styles['CustomBody']
        )
        story.append(report_date)
        story.append(Spacer(1, 20))
        
        # Introduction
        intro = Paragraph(self.create_intro_text(), self.styles['CustomBody'])
        story.append(intro)
        story.append(Spacer(1, 30))
        
        # Summary table
        if trade_results:
            # Create table data with logo blue headers and bold text
            table_data = [
                [
                    Paragraph('<b>Fecha de<br/>operación (Trade Date)</b>', self.styles['TableHeader']),
                    Paragraph('<b>Su<br/>referencia (Trade ID)</b>', self.styles['TableHeader']),
                    Paragraph('<b>Contraparte</b>', self.styles['TableHeader']),
                    Paragraph('<b>Archivo<br/>contrato</b>', self.styles['TableHeader']),
                    Paragraph('<b>Núm. de<br/>campos con<br/>diferencia</b>', self.styles['TableHeader']),
                    Paragraph('<b>Detalle diferencias</b>', self.styles['TableHeader'])
                ]
            ]
            
            for result in trade_results:
                differences_detail = self.format_differences_detail(result['differences'])
                
                row = [
                    Paragraph(result['processing_date'], self.styles['CustomBody']),
                    Paragraph(result['trade_id'], self.styles['CustomBody']),
                    Paragraph(result['counterparty'], self.styles['CustomBody']),
                    Paragraph(f"{result['contract_name']}.pdf", self.styles['CustomBody']),
                    Paragraph(str(result['num_differences']), self.styles['CustomBody']),
                    Paragraph(differences_detail, self.styles['CustomBody'])
                ]
                table_data.append(row)
            
            # Create table with better proportioned column widths
            table = Table(table_data, colWidths=[2.2*cm, 1.6*cm, 2.8*cm, 2.5*cm, 1.9*cm, 7*cm])
            
            # Style the table
            table.setStyle(TableStyle([
                # Header row with blue background
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0066CC')),  # Logo blue background
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 7),
                ('LEFTPADDING', (0, 0), (-1, -1), 4),
                ('RIGHTPADDING', (0, 0), (-1, -1), 4),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('ALIGN', (4, 1), (4, -1), 'CENTER'),  # Center the number column
                
                # Alternate row colors (skip header)
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
            ]))
            
            story.append(table)
        
        # Build PDF
        doc.build(story)
        print(f"PDF report generated: {output_path}")
    
    def format_differences_detail(self, differences: List[Dict]) -> str:
        """Format differences into readable Spanish text with proper line breaks"""
        if not differences:
            return "Sin diferencias encontradas"
        
        details = []
        for diff in differences:
            friendly_desc = diff['friendly_description']
            su_valor = diff['su_input_valor']
            contrato_valor = diff['contrato_input_valor']
            
            detail = f"• {friendly_desc}: El Banco registra '{su_valor}', Contraparte registra '{contrato_valor}'"
            details.append(detail)
        
        # Join with line breaks for proper formatting in PDF
        return '<br/>'.join(details)

def find_matching_files(banco_dir: str, contrato_dir: str) -> List[Tuple[str, str]]:
    """
    Find matching pairs of Banco and Contrato files based on the new naming convention
    """
    banco_files = glob.glob(os.path.join(banco_dir, "Output_*_banco.json"))
    contrato_files = glob.glob(os.path.join(contrato_dir, "Output_*_contrato_*.json"))

    # Create a mapping based on the match key
    banco_map = {}
    for file in banco_files:
        try:
            parsed = FilenameParsed(file)
            match_key = parsed.get_match_key()
            banco_map[match_key] = file
        except Exception as e:
            print(f"Warning: Could not parse banco file {file}: {e}")

    matches = []
    for file in contrato_files:
        try:
            parsed = FilenameParsed(file)
            match_key = parsed.get_match_key()
            if match_key in banco_map:
                matches.append((banco_map[match_key], file))
            else:
                print(f"Warning: No matching banco file found for {os.path.basename(file)}")
        except Exception as e:
            print(f"Warning: Could not parse contrato file {file}: {e}")

    return matches

def main():
    parser = argparse.ArgumentParser(description='Generate PDF reports comparing JSON files')
    parser.add_argument('banco_dir', help='Directory containing Banco JSON files')
    parser.add_argument('contrato_dir', help='Directory containing Contrato JSON files')
    parser.add_argument('--output-dir', '-o', default='.', help='Output directory for PDF report')
    parser.add_argument('--translations', '-t', help='Path to JSON file with path translations')
    parser.add_argument('--logo', '-l', help='Path to logo image file')
    parser.add_argument('--report-name', '-r', default='reporte_comparativo', help='Base name for PDF report')
    
    args = parser.parse_args()
    
    # Validate directories
    if not os.path.isdir(args.banco_dir):
        print(f"Error: Banco directory not found: {args.banco_dir}")
        return 1
    
    if not os.path.isdir(args.contrato_dir):
        print(f"Error: Contrato directory not found: {args.contrato_dir}")
        return 1
    
    # Find matching file pairs
    print("Searching for matching file pairs...")
    file_pairs = find_matching_files(args.banco_dir, args.contrato_dir)
    
    if not file_pairs:
        print("No matching file pairs found!")
        return 1
    
    print(f"Found {len(file_pairs)} matching file pairs")
    
    # Initialize comparator and PDF generator
    comparator = JSONComparator(args.translations)
    pdf_generator = PDFReportGenerator(args.logo)
    
    trade_results = []
    
    # Process each file pair
    for banco_file, contrato_file in file_pairs:
        try:
            print(f"Processing: {os.path.basename(banco_file)} vs {os.path.basename(contrato_file)}")
            
            # Parse filenames
            banco_parsed = FilenameParsed(banco_file)
            contrato_parsed = FilenameParsed(contrato_file)
            
            # Load and compare JSONs
            json1 = comparator.load_json_file(banco_file)
            json2 = comparator.load_json_file(contrato_file)
            
            differences = comparator.compare_jsons(json1, json2)
            
            # Collect results
            trade_results.append({
                'processing_date': banco_parsed.get_formatted_date(),
                'trade_id': banco_parsed.counterparty_trade_id,
                'counterparty': banco_parsed.counterparty_name,
                'contract_name': contrato_parsed.contract_filename,
                'num_differences': len(differences),
                'differences': differences
            })
            
            print(f"  Found {len(differences)} differences")
            
        except Exception as e:
            print(f"Error processing {banco_file}: {e}")
            continue
    
    if trade_results:
        # Generate PDF report
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        pdf_output = os.path.join(args.output_dir, f"{args.report_name}_{timestamp}.pdf")
        
        pdf_generator.generate_pdf_report(trade_results, pdf_output)
        
        # Summary
        total_differences = sum(result['num_differences'] for result in trade_results)
        print(f"\n📊 Report Summary:")
        print(f"📁 Trades processed: {len(trade_results)}")
        print(f"🔍 Total differences found: {total_differences}")
        print(f"📄 PDF report generated: {pdf_output}")
    
    else:
        print("No successful comparisons completed.")
        return 1

if __name__ == "__main__":
    main()