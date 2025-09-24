import csv
import json
import ollama
import argparse
import os
import re # NEW: Import the regular expression module
from tqdm import tqdm

# --- CONFIGURATION ---
# ▼▼▼ EDIT THIS LINE TO CHANGE THE OLLAMA MODEL ▼▼▼
OLLAMA_MODEL = "gemma3:12b"
# ▲▲▲ EDIT THIS LINE TO CHANGE THE OLLAMA MODEL ▲▲▲
# ---------------------

# MODIFIED: Now accepts a 'reasoning' flag
def get_analysis_prompt(file_name: str, reasoning: bool = True) -> str:
    """Generates the detailed prompt for the language model."""
    
    reasoning_instructions = ""
    if reasoning:
        reasoning_instructions = """
First, provide a step-by-step reasoning analysis of the filename. Explain which keywords you identified and how they map to the NYU Data Classification Schema and risk score rubric. This reasoning should be clear and concise.

After your reasoning is complete, provide the final JSON object enclosed in ```json markdown fences.
"""
    
    final_output_instructions = """
Based ONLY on the file name below, respond ONLY with a valid JSON object in the format: {{"risk_score": <score>, "classification": "chosen_classification", "data_type": ["label1", "label2"]}}
"""

    return f"""
    You are a senior data security analyst at New York University. Your task is to analyze a file name and provide three pieces of information: a granular risk score, an official classification, and the likely data type.
    {reasoning_instructions}
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

    {final_output_instructions if not reasoning else ""}
    File Name to Analyze: "{file_name}"
    """

def clean_and_parse_json(text: str) -> dict:
    """
    Cleans markdown fences from a string and parses it as JSON.
    Handles both reasoning and non-reasoning outputs.
    """
    # Use regex to find the JSON block, even if it has reasoning text before it
    match = re.search(r'```json\s*({.*?})\s*```', text, re.DOTALL)
    if match:
        json_str = match.group(1)
    else:
        # Fallback for models that just output raw JSON without fences
        json_str = text[text.find('{'):text.rfind('}')+1]

    return json.loads(json_str)

def analyze_file_name_local(client, file_name: str, verbose: bool = False, reasoning: bool = False) -> dict:
    """Calls the local Ollama model to get the analysis."""
    if not file_name:
        return {"risk_score": "N/A", "classification": "Empty Filename", "data_type": []}

    prompt = get_analysis_prompt(file_name, reasoning=reasoning)
    full_response = ""
    
    try:
        if verbose:
            print(f"\n--- Analyzing: {file_name} ---")
            stream = client.chat(
                model=OLLAMA_MODEL,
                messages=[{'role': 'user', 'content': prompt}],
                stream=True
            )
            for chunk in stream:
                content = chunk['message']['content']
                full_response += content
                print(content, end='', flush=True)
            print("\n---------------------------\n")
        else:
            response = client.chat(
                model=OLLAMA_MODEL,
                messages=[{'role': 'user', 'content': prompt}],
                # format='json' is best for non-streaming, non-reasoning mode
                format='json' if not reasoning else None
            )
            full_response = response['message']['content']

        analysis_data = clean_and_parse_json(full_response)
        
        return {
            "risk_score": analysis_data.get("risk_score", "Parse Error"),
            "classification": analysis_data.get("classification", "Parse Error"),
            "data_type": analysis_data.get("data_type", [])
        }
    except Exception as e:
        print(f"Error processing '{file_name}': {e}. Full response was:\n{full_response}")
        return {"risk_score": "Error", "classification": str(e), "data_type": []}

def main():
    parser = argparse.ArgumentParser(description="Analyze file names from a CSV using a local LLM.")
    parser.add_argument('input_csv', help="Path to the input CSV file.")
    parser.add_argument('output_csv', help="Path for the output CSV file.")
    parser.add_argument('filename_column', help="Name of the column header containing the file names.")
    parser.add_argument('--verbose', action='store_true', help="Stream the model's raw output to the console.")
    # NEW: Add a reasoning flag
    parser.add_argument('--reasoning', action='store_true', help="Prompt the model to provide a step-by-step reasoning trace.")
    
    args = parser.parse_args()

    # ... (The rest of the main function remains largely the same) ...
    try:
        with open(args.input_csv, mode='r', encoding='utf-8') as f: total_rows = sum(1 for row in f) - 1
        with open(args.input_csv, mode='r', encoding='utf-8') as infile, \
             open(args.output_csv, mode='w', encoding='utf-8', newline='') as outfile:
            reader = csv.DictReader(infile)
            if args.filename_column not in reader.fieldnames:
                print(f"Error: Column '{args.filename_column}' not found. Available: {reader.fieldnames}")
                return

            output_fieldnames = reader.fieldnames + ['Risk Score', 'Classification', 'Data Type']
            writer = csv.DictWriter(outfile, fieldnames=output_fieldnames)
            writer.writeheader()
            client = ollama.Client()
            iterator = reader if args.verbose else tqdm(reader, total=total_rows, desc=f"Analyzing files using {OLLAMA_MODEL}")
            if args.verbose: print("Verbose mode enabled. Streaming model output...")
            if args.reasoning: print("Reasoning mode enabled.")

            for row in iterator:
                file_name = row.get(args.filename_column, "")
                analysis_result = analyze_file_name_local(client, file_name, verbose=args.verbose, reasoning=args.reasoning)
                row['Risk Score'] = analysis_result['risk_score']
                row['Classification'] = analysis_result['classification']
                row['Data Type'] = ', '.join(analysis_result.get('data_type', []))
                writer.writerow(row)
                outfile.flush()
                os.fsync(outfile.fileno())
    except FileNotFoundError: print(f"Error: Input file not found at '{args.input_csv}'")
    except Exception as e: print(f"\nAn unexpected error occurred: {e}")

    print(f"\n Analysis complete! Results saved to '{args.output_csv}'")

if __name__ == "__main__":
    main()
