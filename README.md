# Fi-Guy: Wall Street in your Pocket
the financial assistant you didn't know you needed

![CI/CD Status](https://github.com/kgreed4/llmops/actions/workflows/cicd.yml/badge.svg)

### Designed for AIPI 561: LLMops
Fi-Guy is a financial assistant designed to answer questions about daily stock performance (ie. open, close, high, low price), recent ticker news, and detailed ticker information. It uses the Polygon.io API to gather information and then processes it through your local .llamafile. 

## Demo Video

## Project Purpose
The purpose of this project is to enhance financial literacy and give power to everyday investors. Understanding Wall Street is not rocket science, all it takes is getting the right information from the right source. The project uses the Polygon.io API to gather the most accurate and up to date information available before processing it locally (keeping everything secure) and outputting the best answer possible. Fi-Guy has three main features: 
- Aggregating Stock Data
- Delivering Recent Ticker News
- Conducting Background Research
Each of these features can be done for any ticker—making life for the user that much easier! Well what are you still doing reading…let’s get investing!

## Architecture Diagram
![Alt text](https://github.com/kgreed4/LLMOps/blob/main/arch_llmops.png?raw=true)

## Set up
Initial set-up steps:
1. Create Polygon.io account 
2. Set Up API Key by setting `POLYGON_API_KEY`=`""` in `.env`
3. Clone the repository 
`git clone https://github.com/kgreed4/LLMOps.git`
`cd your-repo`
4. Set up virtual environment
`python3 -m venv env source env/bin/activate`
5. Install dependencies
`pip install requirements.txt`
6. Download [Mistral 7b Instruct Llamafile](https://huggingface.co/Mozilla/Mistral-7B-Instruct-v0.2-llamafile/resolve/main/mistral-7b-instruct-v0.2.Q4_0.llamafile?download=true)
7. If on macOS, Linux, or BSD, grant permission to execute the file:
`chmod +x mistral-7b-instruct-v0.2.Q4_0.llamafile`
(If on Windows, rename the file by adding ".exe" on the end)

Running the App:
1. Run the llamafile: `./mistral-7b-instruct-v0.2.Q4_0.llamafile`
2. Build Docker Image: `docker build -t llmops .`
3. Run Docker Container: `docker run -p 3000:3000 llmops`
![Alt text](https://github.com/kgreed4/LLMOps/blob/main/running-locally.png?raw=true)
4. Access the app via browser and link http://127.0.0.1:3000
5. Ask away, learn, & become a financial expert!

Example questions: Tell me about Nike. 
                    OR
What were Apple's daily closing prices from July 8, 2024 to July 12, 2024?
                    OR
What is the most recent news about NVIDIA?

![Alt text](https://github.com/kgreed4/LLMOps/blob/main/quest-ex.png?raw=true)

Testing the App:
1. Run the testing script: `python -m pytest`

## Evaluation