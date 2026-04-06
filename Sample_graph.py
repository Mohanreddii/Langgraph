from typing import TypedDict
from langchain_openai import ChatOpenAI
import os
from dotenv import load_dotenv

from langgraph.graph import StateGraph

import re

def clean_code(code: str) -> str:
    code = code.strip()

    # Remove triple backticks ```python ... ```
    code = re.sub(r"```python", "", code, flags=re.IGNORECASE)
    code = re.sub(r"```", "", code)

    # Remove triple quotes ''' or """
    code = re.sub(r"'''", "", code)
    code = re.sub(r'"""', "", code)

    # Remove leading 'python' if present
    code = re.sub(r"^python", "", code.strip(), flags=re.IGNORECASE)

    return code.strip()

load_dotenv()
class State(TypedDict):
    prompt: str
    code:str
    status:str
    error:str
    attempts: int
    
llm = ChatOpenAI(model='gpt-4o',temperature=0.3,api_key=os.getenv("OPENAI_API_KEY"))

# Node 1 Create Code Generator

def generate_code(state):
    
    print("Code is generating......")
    
    prompt = f'''
    You are a python expert
    Task : {state['prompt']}
    
    previous error (if any):
    {state.get('error','')}
    
    Rules:
    - Return ONLY valid Python code
    - No explanations
    -No comments, Just code
    - Code must be executable
    '''
    response = llm.invoke(prompt)
    
    code  = clean_code(response.content)
    
    return {
        "code":code,
        "attempts":state["attempts"]+1
    }
# NODE 2 DEBUG STATE

def testcode(state):
    print("\n Testing Code...\n")
    print(state["code"])
    
    try:
        local_env = {}
        exec(state['code'],{},local_env)
        print("\n Code executed successfully")

        return {
            "status": "success",
            "error": ""
        }
    except Exception as e:
        print("Error in the code")
        return {
            "status":"error",
            "error":str(e)
        }
# Decision node

def decide_function(state):
    if state['status'] == 'error' and state['attempts'] <5:
        print("/Retrying....")
        return "retry"
    print("Finished.")
    return "end"

graph = StateGraph(State)

graph.add_node("generate",generate_code)
graph.add_node("test",testcode)
graph.add_edge("generate","test")

# Conditional Loop

graph.add_conditional_edges(
    "test",
    decide_function,
    {
        "retry":"generate",
        "end":"__end__"
        
    }
    
)

graph.set_entry_point("generate")

app = graph.compile()

print("\n Graph Diagram (Mermaid):\n")
print(app.get_graph().draw_mermaid())

if __name__ == "__main__":
    user_prompt = "Write a Python function to reverse a string and print result"
    result = app.invoke({
        "prompt":user_prompt,
        "code": "",
        "status": "",
        "error": "",
        "attempts": 0
        
    })
    print("\n Final Output:\n")
    print(result["code"])

      