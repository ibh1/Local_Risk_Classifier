import csv
import json
import ollama
import argparse
import os  # NEW: Import the 'os' module for file system operations
from tqdm import tqdm

# line 58 has Model settings, default is Gemma3:12b, must already be running in Ollama

def get_analysis_prompt(file_name: str) -> str:
    """
    Generates the detailed prompt for the language model.
    This is the same prompt from your Google Apps Script.
    """
    # ... (This function remains exactly the same)
    return f"""
    You are a senior data security analyst at New York University. Your task is to analyze a file name and provide three pieces of information: a granular risk score, an official classification, and the likely data type.

    1.  **Risk Score (1-10):** First, provide a `risk_score` on a scale of 1-10 based on the *severity and potential impact* of a breach. Use this rubric:
        * **1-3 (Low):** Public data, negligible impact.
        * **4-6 (Moderate):** Internal data, could cause moderate operational disruption.
        * **7-9 (High):** Sensitive data (PII, financial, research), could cause significant harm.
        * **10 (Critical):** Extremely sensitive data like privileged credentials (passwords, API keys), where a breach could lead to severe and immediate harm.

    2.  **Classification (Level 1-3):** Second, provide the official `classification` by selecting the single best fit from the NYU Data Classification Schema below.

    3.  **Data Type:** Third, provide a `data_type` array with descriptive labels.

    --- NYU DATA CLASSIFICATION SCHEMA ---
    ### Low Risk Data (Level 1)
    - **Definition:** Publicly available data...
    - **Examples:** Job postings, Website content, Campus maps...
    ### Moderate Risk Data (Level 2)
    - **Definition:** Data where unauthorized disclosure could have adverse effects...
    - **Examples:** University ID numbers, Employee/HR records, FERPA records...
    ### High Risk Data (Level 3)
    - **Definition:** Data where unauthorized disclosure is likely to result in significant or severe Harm...
    - **Examples:** Passwords, PII, Social Security Numbers, HIPAA, GLBA, privileged credentials...
    --- END SCHEMA ---

    **Important:** The risk score reflects severity, while the classification is the category. For example, a file named 'server_passwords.txt' should receive a risk_score of 10 and a classification of 'High Risk (Level 3)'. A file named 'donor_contact_list.xlsx' is also 'High Risk (Level 3)' but might have a lower risk_score, like 8.

    Based ONLY on the file name below, respond ONLY with a valid JSON object in the format: {{"risk_score": <score>, "classification": "chosen_classification", "data_type": ["label1", "label2"]}}

    File Name to Analyze: "{file_name}"
    """

def analyze_file_name_local(client, file_name: str) -> dict:
    """
    Calls the local Ollama model to get the analysis.
    """
    # ... (This function remains exactly the same)
    if not file_name:
        return {"risk_score": "N/A", "classification": "Empty Filename", "data_type": []}

    prompt = get_analysis_prompt(file_name)
    
    try:
        response = client.chat(
            model='gemma3:12b', # Or another model you have pulled
            messages=[{'role': 'user', 'content': prompt}],
            format='json' # This forces the model to return valid JSON
        )
        analysis_data = json.loads(response['message']['content'])
        
        return {
            "risk_score": analysis_data.get("risk_score", "Parse Error"),
            "classification": analysis_data.get("classification", "Parse Error"),
            "data_type": analysis_data.get("data_type", [])
        }
    except Exception as e:
        print(f"Error processing '{file_name}': {e}")
        return {"risk_score": "Error", "classification": str(e), "data_type": []}

def main():
    """
    Main function to read CSV, process files, and write results in real-time.
    """
    parser = argparse.ArgumentParser(description="Analyze file names from a CSV using a local LLM.")
    parser.add_argument('input_csv', help="Path to the input CSV file.")
    parser.add_argument('output_csv', help="Path for the output CSV file.")
    parser.add_argument('filename_column', help="Name of the column header containing the file names.")
    
    args = parser.parse_args()

    # --- MODIFIED SECTION ---

    try:
        # First, count rows for an accurate progress bar (optional but good UX)
        with open(args.input_csv, mode='r', encoding='utf-8') as f:
            total_rows = sum(1 for row in f) - 1  # Subtract 1 for the header row

        # Open both files: input for reading, output for writing
        with open(args.input_csv, mode='r', encoding='utf-8') as infile, \
             open(args.output_csv, mode='w', encoding='utf-8', newline='') as outfile:
            
            reader = csv.DictReader(infile)
            
            if args.filename_column not in reader.fieldnames:
                print(f"Error: Column '{args.filename_column}' not found in the input CSV.")
                print(f"Available columns are: {reader.fieldnames}")
                return

            # Define output headers by adding new columns to the original ones
            output_fieldnames = reader.fieldnames + ['Risk Score', 'Classification', 'Data Type']
            writer = csv.DictWriter(outfile, fieldnames=output_fieldnames)
            writer.writeheader()

            client = ollama.Client()

            # Loop through the input file row-by-row
            for row in tqdm(reader, total=total_rows, desc="Analyzing files"):
                file_name = row.get(args.filename_column, "")
                analysis_result = analyze_file_name_local(client, file_name)
                
                # Add the new analysis data to the current row
                row['Risk Score'] = analysis_result['risk_score']
                row['Classification'] = analysis_result['classification']
                row['Data Type'] = ', '.join(analysis_result.get('data_type', []))
                
                # Write the single, updated row to the output file
                writer.writerow(row)
                
                # NEW: Force the write to the disk so it's visible immediately
                outfile.flush()
                os.fsync(outfile.fileno())

    except FileNotFoundError:
        print(f"Error: Input file not found at '{args.input_csv}'")
        return
    except Exception as e:
        print(f"\nAn unexpected error occurred during processing: {e}")
        return

    print(f"\n Analysis complete! Results saved to '{args.output_csv}'")


if __name__ == "__main__":
    main()
