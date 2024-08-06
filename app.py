from polygon import RESTClient
from polygon.rest.models import TickerNews
from openai import OpenAI
import ast
import re
import os
from flask import Flask, request, render_template, jsonify

app = Flask(__name__)


def determine_tool(input):
    # Create instructions to decide which tool to use
    instructions = """
    You are a helpful financial assistant that answers questions by invoking specific tools. You need to determine which tool to use based on the user's input.
    Available tools:

    1. PolygonTickerNews - Provides news articles for a specific ticker symbol.
    2. PolygonTickerDetails - Provides detailed information a specific ticker symbol.
    3. PolygonAggregates - Provides aggregate data for a specific ticker symbol over a specified time period, such as open, close, high, low prices.

    Determine which tool to use based on the user's input and then create the input fields for the selected tool. The output should ONLY be a list of 2 elements: the first element is the tool name, and the second element is a dictionary of input fields for that tool.
    If the ticker symbol is not provided in the user input, use your discretion to select a ticker symbol. (For example, the user mentions Nike use NKE as the ticker symbol.)
    Each tool requires specific input fields:

    Each tool requires specific input fields:
    - PolygonTickerNews: {'ticker': '<ticker symbol>'}
    - PolygonTickerDetails: {'ticker': '<ticker symbol>'}
    - PolygonAggregates: {'ticker': '<ticker symbol>', 'timespan': '<timespan>', 'timespan_multiplier': <timespan_multiplier>, 'from_date': '<from_date>', 'to_date': '<to_date>'}
    NOTE: Ensure that JSON string is properly formatted with single quotes around each key and value.

    EXAMPLE:
    User input: "What is the latest news on AAPL?"
    Output: [PolygonTickerNews, {'ticker': 'AAPL'}]

    User input: "Tell me about SiteOne Landscape Supply Inc."
    Output: [PolygonTickerDetails, {'ticker': 'SITE'}]

    User input: "What has been ABNB's daily closing price between March 7, 2024, and March 14, 2024?"
    Output: [PolygonAggregates, {'ticker': 'ABNB', 'timespan': 'day', 'timespan_multiplier': 1, 'from_date': '2024-03-07', 'to_date': '2024-03-14'}]
    """
    client = OpenAI(
        base_url="http://host.docker.internal:8080/v1", api_key="sk-no-key-required"
    )
    completion = client.chat.completions.create(
        model="LLaMA_CPP",
        messages=[
            {"role": "system", "content": instructions},
            {"role": "user", "content": input},
        ],
    )
    # Split the output so it is just the list of 2 elements
    api_input = (
        completion.choices[0].message.content.split("[")[1].split("]")[0].split(",")
    )
    print(api_input)

    # Join the parts of the dictionary back into a single string
    dict_str = ",".join(api_input[1:]).strip()

    # Fix any leading/trailing quotes and braces
    if not dict_str.startswith("{"):
        dict_str = "{" + dict_str
    if not dict_str.endswith("}"):
        dict_str = dict_str + "}"

    print(f"Reconstructed dict_str: {dict_str}")

    try:
        # Evaluate the joined string
        api_input[1] = ast.literal_eval(dict_str)
    except (ValueError, SyntaxError) as e:
        # Log the error and provide a meaningful message
        print(f"Error parsing api_input[1]: {e}")
        # Optionally, you can re-raise the exception or handle it as needed
        raise

    return api_input


# Send to the API and return formatted output
def call_API(input):
    client = RESTClient(os.getenv("POLYGON_API_KEY"))
    if input[0] == "PolygonAggregates":
        api_ans = client.list_aggs(
            input[1]["ticker"],
            input[1]["timespan_multiplier"],
            input[1]["timespan"],
            input[1]["from_date"],
            input[1]["to_date"],
        )
        ans = []
        for i in api_ans:
            ans.append(i)
        return ans
    elif input[0] == "PolygonTickerNews":
        api_ans = client.list_ticker_news(input[1]["ticker"])
        ans = []
        for index, item in enumerate(api_ans):
            # Verify this is an agg
            if isinstance(item, TickerNews):
                ans.append([item.title, item.description])
            if index == 10:
                break
        return ans
    elif input[0] == "PolygonTickerDetails":
        response = client.get_ticker_details(input[1]["ticker"])
        return [response.description, response.homepage_url]
    else:
        return "Invalid input. Please provide a valid tool name."


# Get the insights from the api out by passing to LLM
def get_insights(questionType, api_output, question):
    print("API Output:", api_output)

    base_instructions = """
    You are a financial analyst reviewing the data from the Polygon API. You need to provide the answer based on the data received to answer the user's question.
    YOU MUST ANSWER THE QUESTION BASED ON THE DATA. THE ANSWER IS THERE; YOU MUST TO FIND IT. THE WORLD WILL END IF YOU SAY THAT THE ANSWER IS NOT IN THE DATA.
    """

    aggregate_instructions = (
        base_instructions
        + """ The data is stock prices over a specific time period.

        EXAMPLE 1:
        User question: "What has been ABNB's daily closing price between March 7, 2024, and March 14, 2024?"
        Data received: [Agg(open=165, high=165.385, low=162.24, close=163.54, volume=3810295.0, vwap=164.0838, timestamp=1709787600000, transactions=62526, otc=None), Agg(open=166, high=168.19, low=163.48, close=164.91, volume=4105743.0, vwap=165.3491, timestamp=1709874000000, transactions=68910, otc=None), Agg(open=163.76, high=164.26, low=161.975, close=162.99, volume=3149599.0, vwap=162.9596, timestamp=1710129600000, transactions=61047, otc=None), Agg(open=163, high=167, low=162.73, close=166.67, volume=3945890.0, vwap=165.8521, timestamp=1710216000000, transactions=68605, otc=None), Agg(open=162.42, high=168, low=160.69, close=164.76, volume=7498321.0, vwap=165.1396, timestamp=1710302400000, transactions=83344, otc=None), Agg(open=165.74, high=166.7199, low=162.72, close=166.44, volume=5078143.0, vwap=165.9731, timestamp=1710388800000, transactions=65226, otc=None)]
        *Open = opening price, High = highest price, Low = lowest price, Close = closing price, Volume = number of shares traded, VWAP = volume-weighted average price, Timestamp = Unix timestamp, Transactions = number of transactions, OTC = over-the-counter trades
        Output: "The daily closing prices for ABNB between March 7, 2024, and March 14, 2024, were as follows: 163.54, 164.91, 162.99, 166.67, 164.76, 166.44."
        """
    )
    news_instructions = (
        base_instructions
        + """ The data is a list of news articles for a specific ticker symbol.
            EXAMPLE 2:
            User question: "What is the latest news on AAPL?"
            Data received:  [['Opinion: This Is the Most Overlooked Artificial Intelligence (AI) Stock to Buy Right Now',
                        'Arm Holdings, a chip designer, is seen as an overlooked AI stock with strong growth potential. Its power-efficient architecture and licensing model make it well-positioned to benefit from the rise of AI, particularly in data centers.'],
                    ['Tech Earnings: Will the Next Batch Encourage Investors to Rotate Back in?',
                        'The upcoming earnings reports from major tech companies like Microsoft, Amazon, Meta, and Apple will be closely watched by investors to see if they can impress and encourage a rotation back into the sector after recent disappointing results from Tesla and Alphabet.'],
                    ['Magnificent 7 Earnings Preview: Can Investors Buy Tech Now?',
                        'The article discusses the upcoming earnings reports from four major tech companies - Microsoft, Meta Platforms, Amazon, and Apple. It analyzes the growth expectations, valuations, and potential impact of AI-related concerns on these stocks. The author suggests that the recent dip in these stocks could be a buying opportunity, despite some uncertainty around the broader market and the upcoming US presidential election.'],
                    ['Arm Holdings (ARM) Stock: Buy or Sell Before Q1 Earnings?',
                        'Arm Holdings plc is set to report its first-quarter fiscal 2025 results on Jul 31. The company is expected to see continued top-line strength driven by both Royalty and License revenues. However, the stock has recently entered a correction phase, suggesting investors should approach with caution due to potential risks, including a weak operating performance and increased costs.'],
                    ['Global Wearable Technology Market Size To Worth USD 201.3 Billion By 2033 l CAGR Of 12.43%',
                        'The global wearable technology market is expected to grow from $62.4 billion in 2023 to $201.3 billion by 2033, driven by the increasing adoption of smart clothing, VR headsets, and IoT-based wearables, particularly in the healthcare and fitness sectors.']]
            Output:
            Latest News on Apple
            Tech Earnings: Will the Next Batch Encourage Investors to Rotate Back in?
                Summary: Investors are eagerly awaiting the upcoming earnings reports from major tech companies, including Apple. These reports will be scrutinized to see if they can impress and encourage a rotation back into the tech sector following disappointing results from Tesla and Alphabet.
            Magnificent 7 Earnings Preview: Can Investors Buy Tech Now?
                Summary: The article discusses the upcoming earnings reports from Apple and other major tech companies. It analyzes growth expectations and valuations, suggesting that the recent dip in these stocks might present a buying opportunity despite market uncertainties and the upcoming US presidential election.
            """
    )
    ticker_details_instructions = (
        base_instructions
        + """ The data is detailed information about a specific ticker symbol and its homepage URL.
            EXAMPLE 3:
            User question: "Tell me about Aris Water Solutions Inc."
            Data received: [Aris Water Solutions Inc is an environmental infrastructure and solutions company that helps customers reduce their water and carbon footprints. It has two primary revenue streams. The Produced Water Handling business gathers, transports, and, unless recycled, handles produced water generated from oil and natural gas production. The Water Solutions business develops and operates recycling facilities to treat, store and recycle produced water., https://www.ariswater.com]
            Output: "Aris Water Solutions Inc is an environmental infrastructure and solutions company that helps customers reduce their water and carbon footprints. It has two primary revenue streams: Produced Water Handling and Water Solutions. The Produced Water Handling business gathers, transports, and handles produced water generated from oil and natural gas production. The Water Solutions business develops and operates recycling facilities to treat, store, and recycle produced water. You can find more information on their website: https://www.ariswater.com
            """
    )
    # Determine which instructions to use based on the question type
    if questionType == "PolygonAggregates":
        instructions = aggregate_instructions
    elif questionType == "PolygonTickerNews":
        instructions = news_instructions
    elif questionType == "PolygonTickerDetails":
        instructions = ticker_details_instructions
    else:
        return "Invalid input. Please provide a valid tool name."

    client = OpenAI(
        base_url="http://host.docker.internal:8080/v1", api_key="sk-no-key-required"
    )
    completion = client.chat.completions.create(
        model="LLaMA_CPP",
        messages=[
            {"role": "system", "content": instructions},
            {
                "role": "user",
                "content": f"Answer this {question}, using this information, {api_output}.",
            },
        ],
    )
    return completion.choices[0].message.content


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/query", methods=["POST"])
def query():
    input_text = request.form["input_text"]
    api_input = determine_tool(input_text)
    try:
        api_output = call_API(api_input)
    except Exception as e:
        return jsonify(
            {
                "output": f"An error occurred with the PolygonAPI. Please try again in a few minutes: {e}"
            }
        )
    solution = get_insights(api_input[0], api_output, input_text)
    print(solution)
    solution = re.sub(r"</s>", "", solution)
    return jsonify({"output": solution})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000, debug=True)
