# Local Risk Classifier
Local Script to perform risk classification using Ollama + Python
It analyzes each file name, assigns a risk score, determines a data classification level based on a predefined schema, and identifies potential data types.

# How to Run
## Requirements:
Mac w/ M-series processor

Python

Ollama

# Ollama Setup:
https://ollama.com/search

Download Ollama and run Gemma3:12b. [Ollama run Gemma3:12b]

# Local Risk Classification Script
In a new terminal navigate to the folder that contains the LocalRiskClassifier.py and input_files.csv. 

Run script: 

```python
python3 LocalRiskClassifier.py input_files.csv output_results.csv "File Name"
```

Wile the script is running, you can open output_results.csv and should see new rows appearing in the file as soon as they are processed by the model.

