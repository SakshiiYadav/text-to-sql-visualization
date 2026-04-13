import json
from typing import TypedDict
import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st
from langgraph.graph import END, StateGraph

from utils.llm import call_llm
from utils.schema import schema
from utils.sql_generator import run_sql


class AgentState(TypedDict):
    query: str
    response: str
    sql: str
    error: str
    df: object
    retried: bool


def clean_text(text: str) -> str:
    return text.strip().replace("```sql", "").replace("```", "").strip()


def clean_sql(text: str) -> str:
    text = clean_text(text)
    lower = text.lower()

    if "select" in lower:
        start = lower.find("select")
        text = text[start:]

    if ";" in text:
        text = text.split(";")[0] + ";"

    return text.strip()

def force_graph_friendly_sql(sql: str, query: str) -> str:
    q = query.lower()
    s = sql.lower()

    if "by country" in q and "group by" not in s:
        return """
SELECT c.Country, SUM(i.Total) AS total_sales
FROM invoices i
JOIN customers c ON i.CustomerId = c.CustomerId
GROUP BY c.Country
ORDER BY total_sales DESC;
""".strip()

    if "each genre" in q or "by genre" in q:
        return """
SELECT g.Name AS genre, COUNT(t.TrackId) AS track_count
FROM tracks t
JOIN genres g ON t.GenreId = g.GenreId
GROUP BY g.Name
ORDER BY track_count DESC;
""".strip()

    if "top 5 customers" in q and "spending" in q:
        return """
SELECT c.FirstName || ' ' || c.LastName AS customer_name, SUM(i.Total) AS total_spent
FROM customers c
JOIN invoices i ON c.CustomerId = i.CustomerId
GROUP BY c.CustomerId
ORDER BY total_spent DESC
LIMIT 5;
""".strip()

    if "monthly sales trend" in q or "sales trend" in q:
        return """
SELECT strftime('%Y-%m', InvoiceDate) AS month, SUM(Total) AS monthly_sales
FROM invoices
GROUP BY month
ORDER BY month;
""".strip()

    return sql
def generate_sql_or_reply_node(state: AgentState):
    prompt = f"""
You are an expert SQLite assistant.

DATABASE SCHEMA:
{schema}

IMPORTANT RELATIONSHIPS:
- customers.CustomerId = invoices.CustomerId
- invoices.InvoiceId = invoice_items.InvoiceId
- invoice_items.TrackId = tracks.TrackId
- tracks.AlbumId = albums.AlbumId
- albums.ArtistId = artists.ArtistId
- tracks.GenreId = genres.GenreId
- tracks.MediaTypeId = media_types.MediaTypeId
- playlist_track.TrackId = tracks.TrackId
- playlist_track.PlaylistId = playlists.PlaylistId

TASK:
- If the user query is related to the database, return ONLY a valid SQLite SELECT query.
- If the user query is not related to the database, return ONLY this format:

Apologies! your query is not related to the available database.

Suggested Questions:
- <natural language question 1>
- <natural language question 2>
- <natural language question 3>
- <natural language question 4>

STRICT SQL RULES:
- Return only SQL if relevant
- SQL must start with SELECT
- Do not use markdown
- Do not add explanations
- Do not mix SQL and text
- For queries like "by country", "by genre", "by artist", "by customer":
  1. SELECT the grouping column
  2. use aggregate function like SUM/COUNT/AVG
  3. include GROUP BY on that grouping column
- For trend queries:
  1. SELECT the time column
  2. aggregate numeric values
  3. GROUP BY the time column
- Always use readable aliases like:
  - total_sales
  - total_spent
  - track_count
  - monthly_sales
- Make the output graph-friendly whenever possible

EXAMPLES:

User Query: What is the total sales by country?
SQL:
SELECT c.Country AS country, SUM(i.Total) AS total_sales
FROM invoices i
JOIN customers c ON i.CustomerId = c.CustomerId
GROUP BY c.Country
ORDER BY total_sales DESC;

User Query: How many tracks are there in each genre?
SQL:
SELECT g.Name AS genre, COUNT(t.TrackId) AS track_count
FROM tracks t
JOIN genres g ON t.GenreId = g.GenreId
GROUP BY g.Name
ORDER BY track_count DESC;

User Query: Show the monthly sales trend.
SQL:
SELECT strftime('%Y-%m', InvoiceDate) AS month, SUM(Total) AS monthly_sales
FROM invoices
GROUP BY month
ORDER BY month;

User Query:
{state["query"]}

Response:
"""
    raw_response = call_llm(prompt)
    cleaned = clean_text(raw_response)

    if cleaned.lower().startswith("select"):
        state["sql"] = force_graph_friendly_sql(clean_sql(cleaned), state["query"])
        state["response"] = ""
    else:
        state["sql"] = ""
        state["response"] = cleaned

    return state


def execute_sql_node(state: AgentState):
    if not state["sql"]:
        return state

    try:
        state["df"] = run_sql(state["sql"])
        state["error"] = ""
    except Exception as e:
        state["error"] = str(e)

    return state

def fix_sql_node(state: AgentState):
    prompt = f"""
You are an expert SQLite SQL fixer.

DATABASE SCHEMA:
{schema}

IMPORTANT RELATIONSHIPS:
- customers.CustomerId = invoices.CustomerId
- invoices.InvoiceId = invoice_items.InvoiceId
- invoice_items.TrackId = tracks.TrackId
- tracks.AlbumId = albums.AlbumId
- albums.ArtistId = artists.ArtistId
- tracks.GenreId = genres.GenreId
- tracks.MediaTypeId = media_types.MediaTypeId
- playlist_track.TrackId = tracks.TrackId
- playlist_track.PlaylistId = playlists.PlaylistId

Fix the SQL query.

User Query:
{state["query"]}

Previous SQL:
{state["sql"]}

Execution Error:
{state["error"]}

RULES:
- Return ONLY corrected SQLite SELECT query
- Do not explain anything
- For queries like "by country", "by genre", "by customer", "by artist":
  1. include the grouping column in SELECT
  2. use aggregate function
  3. include GROUP BY
- Use aliases like total_sales, total_spent, track_count, monthly_sales
- Make result suitable for table + graph output
"""
    fixed = call_llm(prompt)
    state["sql"] = force_graph_friendly_sql(clean_sql(fixed), state["query"])
    state["retried"] = True
    return state

def route_after_execution(state: AgentState):
    if state["error"] and not state["retried"]:
        return "fix_sql"
    return END

import pandas as pd


def decide_graph(df, query: str):
    if df is None or df.empty or len(df.columns) < 2:
        return None

    q = query.lower().strip()
    cols = list(df.columns)

    numeric_cols = [c for c in cols if pd.api.types.is_numeric_dtype(df[c])]
    categorical_cols = [c for c in cols if not pd.api.types.is_numeric_dtype(df[c])]

    if not numeric_cols:
        return None

    x = categorical_cols[0] if categorical_cols else cols[0]
    y = numeric_cols[0]

    time_keywords = ["trend", "over time", "monthly", "yearly", "daily", "date", "month", "year"]
    pie_keywords = ["distribution", "share", "percentage", "proportion", "contribution"]
    bar_keywords = ["top", "country", "genre", "artist", "customer", "album", "city", "count", "number"]

    datetime_cols = []
    for c in cols:
        try:
            converted = pd.to_datetime(df[c], errors="coerce")
            if converted.notna().sum() >= max(2, len(df) // 2):
                datetime_cols.append(c)
        except Exception:
            pass

    if any(k in q for k in time_keywords) and datetime_cols:
        return {
            "chart": "line",
            "x": datetime_cols[0],
            "y": y
        }

    if any(k in q for k in pie_keywords) and len(df) <= 8 and categorical_cols:
        return {
            "chart": "pie",
            "x": x,
            "y": y
        }

    if any(k in q for k in bar_keywords) and categorical_cols:
        return {
            "chart": "bar",
            "x": x,
            "y": y
        }

    if datetime_cols:
        return {
            "chart": "line",
            "x": datetime_cols[0],
            "y": y
        }

    if categorical_cols and len(df) <= 8:
        return {
            "chart": "bar",
            "x": x,
            "y": y
        }

    if categorical_cols:
        return {
            "chart": "bar",
            "x": x,
            "y": y
        }

    return None

builder = StateGraph(AgentState)
builder.add_node("generate_sql_or_reply", generate_sql_or_reply_node)
builder.add_node("execute_sql", execute_sql_node)
builder.add_node("fix_sql", fix_sql_node)

builder.set_entry_point("generate_sql_or_reply")
builder.add_edge("generate_sql_or_reply", "execute_sql")
builder.add_conditional_edges(
    "execute_sql",
    route_after_execution,
    {
        "fix_sql": "fix_sql",
        END: END,
    },
)
builder.add_edge("fix_sql", "execute_sql")

graph = builder.compile()


def run_agent(query: str):
    initial_state: AgentState = {
        "query": query,
        "response": "",
        "sql": "",
        "error": "",
        "df": None,
        "retried": False,
    }
    return graph.invoke(initial_state)


st.set_page_config(page_title="Text-to-SQL with Visualization", layout="wide")
st.title("Text-to-SQL with Visualization")

query = st.text_input("Enter your query:")

if st.button("Run Query"):
    if not query.strip():
        st.warning("Please enter a query.")
        st.stop()

    result = run_agent(query.strip())

    if result["response"]:
        st.subheader("Response")
        st.markdown(result["response"])
        st.stop()

    if result["error"]:
        st.error(f"SQL Error: {result['error']}")
        st.stop()

    df = result["df"]
    sql = result["sql"]

    st.subheader("Generated SQL")
    st.code(sql, language="sql")

    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("Result Table")
        st.dataframe(df, width="stretch")
    with col2:
        graph_plan = decide_graph(df, query)
    
        if graph_plan:
            chart = graph_plan["chart"]
            x = graph_plan["x"]
            y = graph_plan["y"]
    
            plot_df = df.copy()
            fig, ax = plt.subplots(figsize=(6, 4))
    
            if chart == "line":
                plot_df[x] = pd.to_datetime(plot_df[x], errors="coerce")
                plot_df = plot_df.dropna(subset=[x, y]).sort_values(by=x)
                ax.plot(plot_df[x], plot_df[y], marker="o")
                ax.set_xlabel(x)
                ax.set_ylabel(y)
                plt.xticks(rotation=45)
    
            elif chart == "bar":
                plot_df = plot_df.dropna(subset=[x, y]).head(15)
                ax.bar(plot_df[x].astype(str), plot_df[y])
                ax.set_xlabel(x)
                ax.set_ylabel(y)
                plt.xticks(rotation=45)
    
            elif chart == "pie":
                plot_df = plot_df.dropna(subset=[x, y]).head(8)
                ax.pie(plot_df[y], labels=plot_df[x].astype(str), autopct="%1.1f%%")
    
            st.subheader(f"{chart.capitalize()} Chart")
            st.pyplot(fig)
        else:
            st.info("No suitable graph for this result.")