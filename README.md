# Local Risk Classifier
Local Script to perform risk classification using Ollama + Python
It analyzes each file name, assigns a risk score, determines a data classification level based on a predefined schema, and identifies potential data types.

How to Run
Requirements:
Python
Ollama

Ollama Setup:
Download and run Gemma3:12b. [Ollama run Gemma3:12b]

In a new terminal navigate to the folder that contains the LocalRiskClassifier.py script + input_files.csv. 

Then run script: 

'''python
python3 LocalRiskClassifier.py input_files.csv output_results.csv "File Name"
'''

Wile the script is running, you can open output_results.csv with an application like Excel, Numbers, or a text editor. You will see new rows appearing in the file as soon as they are processed by the model.

