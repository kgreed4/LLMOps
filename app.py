"""1. Define the tools our agent can use"""
import os
from langchain import hub
from langchain_openai.chat_models import ChatOpenAI
from langchain_community.utilities.polygon import PolygonAPIWrapper
from langchain_community.tools import PolygonLastQuote, PolygonTickerNews, PolygonFinancials, PolygonAggregates
from langchain_openai import OpenAI
from langchain.agents import AgentExecutor, create_react_agent
import gradio as gr
from flask import Flask, request, render_template, jsonify

app = Flask(__name__)

# # Custom prompt explicitly instructing the LLM to use tools
instructions = """
You are a helpful financial assistant that answers questions by invoking specific tools.
Available tools:

1. PolygonLastQuote
2. PolygonTickerNews
3. PolygonFinancials
4. PolygonAggregates

Each tool requires specific input fields:
- PolygonLastQuote: {'ticker': '<ticker symbol>'}
- PolygonTickerNews: {'ticker': '<ticker symbol>'}
- PolygonFinancials: {'ticker': '<ticker symbol>'}
- PolygonAggregates: {'ticker': '<ticker symbol>', 'timespan': '<timespan>', 'timespan_multiplier': <timespan_multiplier>, 'from_date': '<from_date>', 'to_date': '<to_date>'}

# Here is an example of how to use the tools:
# When a user asks a question, decide which tool to use based on the question and invoke it.
# Example question: "What has been ABNB's daily closing price between March 7, 2024, and March 14, 2024?"
# Appropriate tool to use: PolygonAggregates
# Function to call: polygon_aggregates({'ticker': 'ABNB', 'timespan': 'day', 'timespan_multiplier': 1, 'from_date': '2024-03-07', 'to_date': '2024-03-14'})
# """

base_prompt = hub.pull("langchain-ai/react-agent-template")
prompt = base_prompt.partial(instructions=instructions)

llm = ChatOpenAI(
    base_url="http://localhost:8080/v1", # "http://<Your api-server IP>:port"
    api_key = "sk-no-key-required"
)

polygon = PolygonAPIWrapper()
tools = [
    PolygonLastQuote(api_wrapper=polygon),
    PolygonTickerNews(api_wrapper=polygon),
    PolygonFinancials(api_wrapper=polygon),
    PolygonAggregates(api_wrapper=polygon),
]

# """2. Define agent and helper functions"""
from langchain_core.runnables import RunnablePassthrough
from langchain_core.agents import AgentFinish

# Define the agent
agent_runnable = create_react_agent(llm, tools, prompt)

agent = RunnablePassthrough.assign(
    agent_outcome = agent_runnable
)

# Define the function to execute tools
def execute_tools(data):
    agent_action = data.pop('agent_outcome')
    print('Agent action:', agent_action)

    tool_to_use = {t.name: t for t in tools}[agent_action.tool]
    if tool_to_use is None:
        print(f"Tool {agent_action.tool} not found in available tools.")
        return data
    
    print('Tool to use:', tool_to_use)
    tool_input = eval(agent_action.tool_input)  # Convert string representation to a dictionary

    observation = tool_to_use.invoke(tool_input)

    data['intermediate_steps'].append((agent_action, observation))
    print('Intermediate steps:', data['intermediate_steps'])
    return data

# """3. Define the LangGraph"""
from langgraph.graph import END, Graph

# Define logic that will be used to determine which conditional edge to go down
def should_continue(data):
    if isinstance(data['agent_outcome'], AgentFinish):
        return "exit"
    else:
        return "continue"

workflow = Graph()
workflow.add_node("agent", agent)
workflow.add_node("tools", execute_tools)
workflow.set_entry_point("agent")
workflow.add_conditional_edges(
    "agent",
    should_continue,
    {
        "continue": "tools",
        "exit": END
    }
)
workflow.add_edge('tools', 'agent')
chain = workflow.compile()

def financial_agent(input_text):
    result = chain.invoke({"input": input_text, "intermediate_steps": []})
    output = result['agent_outcome'].return_values["output"]
    return output

# iface = gr.Interface(
#     fn=financial_agent,
#     inputs=gr.Textbox(lines=2, placeholder="Enter your query here..."),
#     outputs=gr.Markdown(),
#     title="Financial Agent",
#     description="Financial Data Explorer: Leveraging Advanced API Tools for Market Insights"
# )

# iface.launch()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/query', methods=['POST'])
def query():
    input_text = request.form['input_text']
    output = financial_agent(input_text)
    return jsonify({"output": output})

if __name__ == '__main__':
    app.run(debug=True)