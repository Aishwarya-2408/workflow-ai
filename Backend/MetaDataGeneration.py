import pandas as pd
import re
import os.path
import openpyxl
from typing import List, Dict, Set, Tuple


class ConditionParser:
    """
    A class to parse Excel files containing condition strings and transform them
    into a structured format with unique field-value pairs.
    """
    
    def __init__(self, input_file_path: str):
        """
        Initialize the ConditionParser with the input file path.
        
        Args:
            input_file_path: Path to the input Excel file
        """
        self.input_file_path = input_file_path
        self.input_data = None
        self.output_data = []
        self.unique_pairs = set()
        
    def load_data(self) -> None:
        """Load the input Excel file into a pandas DataFrame."""
        try:
            self.input_data = pd.read_excel(self.input_file_path)
            print(f"Successfully loaded data from {self.input_file_path}")
        except Exception as e:
            raise Exception(f"Error loading input file: {str(e)}")
        
    def parse_condition(self, condition: str) -> List[Dict[str, str]]:
        """
        Parse a condition string into key-value pairs.
        
        Args:
            condition: The condition string to parse
            
        Returns:
            A list of dictionaries with field name and value
        """
        if pd.isna(condition):
            return []
        
        # Split the condition string by &&
        condition_parts = condition.split('&&')
        results = []
        
        for part in condition_parts:
            part = part.strip()
            # Find the first occurrence of '=' to split into key-value
            equal_pos = part.find('=')
            if equal_pos != -1:
                field_name = part[:equal_pos].strip()
                value = part[equal_pos+1:].strip()
                results.append({
                    'Field Name': field_name,
                    'Type of Master': value,
                    'Line Level / Header': ''
                })
                
        return results
    
    def process_data(self) -> None:
        """Process all conditions in the input data."""
        if self.input_data is None:
            raise Exception("Input data not loaded. Call load_data() first.")
        
        for _, row in self.input_data.iterrows():
            if 'Condition' in row:
                parsed_conditions = self.parse_condition(row['Condition'])
                for condition in parsed_conditions:
                    pair = (condition['Field Name'], condition['Type of Master'])
                    # Only add if we haven't seen this field-value pair before
                    if pair not in self.unique_pairs:
                        self.output_data.append(condition)
                        self.unique_pairs.add(pair)

        # Sort the output data first by Field Name, then by Type of Master
        self.output_data.sort(key=lambda x: (x['Field Name'], x['Type of Master']))
    
    def save_output(self, output_file_path: str) -> None:
        """
        Save the processed data to an Excel file with proper formatting:
        - Auto-adjusted column widths
        - Headers centered and middle-aligned
        - Data middle-aligned vertically with left text alignment
        
        Args:
            output_file_path: Path where the output Excel file will be saved
        """
        if not self.output_data:
            print("No data to save. Process data first.")
            return
            
        output_df = pd.DataFrame(self.output_data)
        
        try:
            # Create a Pandas Excel writer using openpyxl as the engine
            with pd.ExcelWriter(output_file_path, engine='openpyxl') as writer:
                output_df.to_excel(writer, index=False, sheet_name='Sheet1')
                
                # Get the openpyxl workbook and worksheet objects
                workbook = writer.book
                worksheet = writer.sheets['Sheet1']
                
                # Auto-adjust column width
                for col_idx, col in enumerate(worksheet.columns, 1):
                    max_length = 0
                    col_letter = openpyxl.utils.get_column_letter(col_idx)
                    for cell in col:
                        try:
                            if cell.value:
                                max_length = max(max_length, len(str(cell.value)))
                        except:
                            pass
                    adjusted_width = (max_length + 2)
                    worksheet.column_dimensions[col_letter].width = adjusted_width
                
                # Style headers (bold, center align horizontally and vertically)
                header_font = openpyxl.styles.Font(bold=True)
                header_alignment = openpyxl.styles.Alignment(horizontal='center', vertical='center')
                
                for cell in worksheet[1]:
                    cell.font = header_font
                    cell.alignment = header_alignment
                
                # Style data cells (middle vertical align with left text alignment)
                data_alignment = openpyxl.styles.Alignment(vertical='center', horizontal='left')
                
                for row in worksheet.iter_rows(min_row=2):  # Start from row 2 (after header)
                    for cell in row:
                        cell.alignment = data_alignment
                
                print(f"Successfully saved output to {output_file_path} with formatted columns")
        except Exception as e:
            raise Exception(f"Error saving output file: {str(e)}")
    
    def run(self, output_file_path: str) -> None:
        """
        Run the complete parsing process.
        
        Args:
            output_file_path: Path where the output Excel file will be saved
        """
        self.load_data()
        self.process_data()
        self.save_output(output_file_path)


def main():
    """Main function to execute the condition parsing process."""
    # Set input and output file paths directly in the code
    input_file_path = r"C:\Users\shreyash.salunke\OneDrive - Zycus\Projects\Workflow\data\Output\MUFG\Final\mufg_isource_qs_publish_wcm.xlsx"
    output_file_path = r"C:\Users\shreyash.salunke\OneDrive - Zycus\Projects\Workflow\data\Output\MUFG\Final\mufg_isource_qs_publish_metadata.xlsx"
    
    try:
        condition_parser = ConditionParser(input_file_path)
        condition_parser.run(output_file_path)
        print("Processing completed successfully.")
    except Exception as e:
        print(f"Error: {str(e)}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())