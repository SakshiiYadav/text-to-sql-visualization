import json
from utils.llm import call_llm

def decide_graph(df, user_query):
    prompt = f"""
    You are a data visualization expert.

    User query: {user_query}

    Data sample:
    {df.head().to_dict()}

    Decide:
    - Should we plot? (yes/no)
    - Chart type (bar, line, pie)
    - X column
    - Y column

    Return STRICT JSON:
    {{
        "plot": "yes",
        "chart": "bar",
        "x": "column_name",
        "y": "column_name"
    }}
    """

    response = call_llm(prompt)

    try:
        return json.loads(response)
    except:
        return {"plot": "no"}


