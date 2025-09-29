import json
import pandas as pd
from typing import Any, Dict, List, Tuple, Union, Optional
import os
from datetime import datetime
import argparse

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
        
        # Try to find partial matches for array indices
        # e.g., if path is "payout[0].interestRatePayout.rateSpecification"
        # look for "payout[*].interestRatePayout.rateSpecification" or "payout.interestRatePayout.rateSpecification"
        normalized_path = path
        
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
        
        return best_description if best_description else ""
    
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
        # Flatten both JSONs
        flat1 = self.flatten_json(json1)
        flat2 = self.flatten_json(json2)
        
        # Get all unique keys from both JSONs
        all_keys = set(flat1.keys()) | set(flat2.keys())
        
        differences = []
        
        for key in sorted(all_keys):
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
                    'su_input_valor': str(val1) if val1 is not None else None,
                    'contrato_input_valor': str(val2) if val2 is not None else None,
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
    
    def generate_html_report(self, differences: List[Dict[str, Any]], 
                           file1_name: str, file2_name: str) -> str:
        """
        Generate an attractive HTML report
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Color coding for different types of changes
        color_map = {
            'added': '#d4edda',      # Light green
            'removed': '#f8d7da',    # Light red
            'modified': '#fff3cd',   # Light yellow
            'type_changed': '#d1ecf1' # Light blue
        }
        
        html_template = f'''
        <!DOCTYPE html>
        <html>
        <head>
            <title>JSON Comparison Report</title>
            <style>
                body {{
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    margin: 20px;
                    background-color: #f8f9fa;
                }}
                .header {{
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 20px;
                    border-radius: 10px;
                    margin-bottom: 20px;
                }}
                .summary {{
                    display: flex;
                    gap: 20px;
                    margin-bottom: 20px;
                }}
                .stat-card {{
                    background: white;
                    padding: 15px;
                    border-radius: 8px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                    text-align: center;
                    min-width: 120px;
                }}
                .stat-number {{
                    font-size: 24px;
                    font-weight: bold;
                    color: #333;
                }}
                .stat-label {{
                    color: #666;
                    font-size: 12px;
                    text-transform: uppercase;
                }}
                table {{
                    width: 100%;
                    border-collapse: collapse;
                    background: white;
                    border-radius: 8px;
                    overflow: hidden;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }}
                th {{
                    background: #495057;
                    color: white;
                    padding: 12px;
                    text-align: left;
                    font-weight: 600;
                }}
                td {{
                    padding: 8px 12px;
                    border-bottom: 1px solid #dee2e6;
                    font-family: 'Courier New', monospace;
                    font-size: 12px;
                }}
                .path {{
                    font-weight: bold;
                    color: #495057;
                    max-width: 300px;
                    word-break: break-all;
                }}
                .value {{
                    max-width: 200px;
                    word-wrap: break-word;
                }}
                .description {{
                    max-width: 250px;
                    word-wrap: break-word;
                    color: #495057;
                }}
                tr:hover {{
                    background-color: #f8f9fa;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>JSON Comparison Report</h1>
                <p><strong>File 1:</strong> {file1_name}</p>
                <p><strong>File 2:</strong> {file2_name}</p>
                <p><strong>Generated:</strong> {timestamp}</p>
            </div>
            
            <div class="summary">
                <div class="stat-card">
                    <div class="stat-number">{self.stats['added']}</div>
                    <div class="stat-label">Added</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{self.stats['removed']}</div>
                    <div class="stat-label">Removed</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{self.stats['modified']}</div>
                    <div class="stat-label">Modified</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{self.stats['type_changed']}</div>
                    <div class="stat-label">Type Changed</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{len(differences)}</div>
                    <div class="stat-label">Total Differences</div>
                </div>
            </div>
            
            <table>
                <thead>
                    <tr>
                        <th>Path</th>
                        <th>Description</th>
                        <th>Change Type</th>
                        <th>{file1_name}</th>
                        <th>{file2_name}</th>
                        <th>Types</th>
                    </tr>
                </thead>
                <tbody>
        '''
        
        for diff in differences:
            bg_color = color_map.get(diff['difference_type'], '#ffffff')
            types_info = f"{diff['su_input_tipo']} → {diff['contrato_input_tipo']}" if diff['su_input_tipo'] and diff['contrato_input_tipo'] else (diff['su_input_tipo'] or diff['contrato_input_tipo'] or '')
            
            # Show friendly description if available, otherwise show "Not defined"
            friendly_desc = diff['friendly_description'] or '<em style="color: #888;">Not defined</em>'
            
            html_template += f'''
                    <tr style="background-color: {bg_color};">
                        <td class="path">{diff['path']}</td>
                        <td class="description">{friendly_desc}</td>
                        <td><strong>{diff['difference_type'].replace('_', ' ').title()}</strong></td>
                        <td class="value">{diff['su_input_valor'] or 'None'}</td>
                        <td class="value">{diff['contrato_input_valor'] or 'None'}</td>
                        <td>{types_info}</td>
                    </tr>
            '''
        
        html_template += '''
                </tbody>
            </table>
        </body>
        </html>
        '''
        
        return html_template
    
    def save_to_csv(self, differences: List[Dict[str, Any]], output_path: str):
        """
        Save differences to CSV file
        """
        if not differences:
            print("No differences found to save.")
            return
            
        df = pd.DataFrame(differences)
        df.to_csv(output_path, index=False)
        print(f"CSV report saved to: {output_path}")
    
    def save_to_html(self, differences: List[Dict[str, Any]], 
                    output_path: str, file1_name: str, file2_name: str):
        """
        Save HTML report to file
        """
        html_content = self.generate_html_report(differences, file1_name, file2_name)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        print(f"HTML report saved to: {output_path}")

def main():
    parser = argparse.ArgumentParser(description='Compare two JSON files and generate difference reports')
    parser.add_argument('file1', help='Path to first JSON file')
    parser.add_argument('file2', help='Path to second JSON file')
    parser.add_argument('--output-dir', '-o', default='.', help='Output directory for reports (default: current directory)')
    parser.add_argument('--prefix', '-p', default='json_comparison', help='Prefix for output files')
    parser.add_argument('--translations', '-t', help='Path to JSON file with path translations')
    
    args = parser.parse_args()
    
    # Initialize comparator
    comparator = JSONComparator(args.translations)
    
    try:
        # Load JSON files
        print(f"Loading {args.file1}...")
        json1 = comparator.load_json_file(args.file1)
        
        print(f"Loading {args.file2}...")
        json2 = comparator.load_json_file(args.file2)
        
        # Compare JSONs
        print("Comparing JSON files...")
        differences = comparator.compare_jsons(json1, json2)
        
        if not differences:
            print("✅ No differences found! The JSON files are identical.")
            return
        
        print(f"Found {len(differences)} differences:")
        print(f"  - Added: {comparator.stats['added']}")
        print(f"  - Removed: {comparator.stats['removed']}")
        print(f"  - Modified: {comparator.stats['modified']}")
        print(f"  - Type Changed: {comparator.stats['type_changed']}")
        
        # Generate output files
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_output = os.path.join(args.output_dir, f"{args.prefix}_{timestamp}.csv")
        html_output = os.path.join(args.output_dir, f"{args.prefix}_{timestamp}.html")
        
        # Save reports
        comparator.save_to_csv(differences, csv_output)
        comparator.save_to_html(differences, html_output, 
                              os.path.basename(args.file1), 
                              os.path.basename(args.file2))
        
        print(f"\n📊 Reports generated successfully!")
        print(f"📁 HTML Report: {html_output}")
        print(f"📄 CSV Report: {csv_output}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1

if __name__ == "__main__":
    main()