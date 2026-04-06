from typing import TypedDict
from langchain_openai import ChatOpenAI

import os 
import re
from dotenv import load_dotenv
load_dotenv()

from langgraph.graph import StateGraph,END

class State(TypedDict):
    prompt:str
    code:str
    errors:str
    attempts:int
    debuger:str
    feedback:str
    
llm = ChatOpenAI(model='gpt-4o',temperature=0.1,api_key=os.getenv("OPENAI_API_KEY"))

def generate_code(state):
    '''Generate code from the prompt and if we have any existing feedback'''
    print(f"\nGenerating code......with the attempt of {state['attempts']+1}\n")
    
    system_msg = '''
    You are an expert Python developer. 
    Write ONLY raw Python code. 
    No markdown, 
    no backticks,
    no talk.'''
    
    user = f"Task: {state['prompt']}"   
    
    if state['feedback']:
        user = f"\n\n Task: {state['prompt']}, Your previous code failed. Follow this fix strategy: {state['feedback']}"
        
    response = llm.invoke([
        ("system",system_msg),
        ("user",user)
    ])
    code = re.sub(r"```python\n|```","",response.content).strip()

    return { "code": code,
            "attempts":state['attempts']+1 
            }

def test_code(state):
    print("----Existing Code----")
    try:
        local_env  = {}
        exec(state['code'],{},local_env)
        return {"errors":""}
    except Exception as e:
        print("Exception occures")
        return {"errors":str(e)}
        
def debug_code(state):
    print("----DEBUG----")
    prompt = [
        ("system","You are a senior debugger. Analyze the code and errors. Provide a 1-sentence fix strategy. Do NOT write code."),
        ('human',f"\n\nCode is {state['code']} and the errors is {state['errors']}")
    ]
    response  = llm.invoke(prompt)
    return {
        "feedback":response.content
    }

def conditional_loops(state):
    if not state['errors']:
        print("END")
        return "end"
    if state['attempts'] >=3:
        return "end"
    return 'debug'

graph = StateGraph(State)

graph.add_node("generate",generate_code)
graph.add_node("test",test_code)
graph.add_node("debug",debug_code)

graph.set_entry_point('generate') 
graph.add_edge("generate","test")

graph.add_conditional_edges(
    'test',
    conditional_loops,
    {
        "debug":"debug",
        "end":END
    }
)

graph.add_edge("debug","generate")
app = graph.compile()

if __name__ == "__main__":
    task = "Create a function 'calculate' that takes a list of numbers and returns their average. Call the function with [10, 20, 30] and print the result."
    
    inputs = {"prompt": task, "code": "", "errors": "", "feedback": "", "attempts": 0}
    result = app.invoke(inputs)
    
    print("\n" + "="*30)
    print("FINAL RECTIFIED CODE:")
    print("="*30)
    print(result["code"])
   