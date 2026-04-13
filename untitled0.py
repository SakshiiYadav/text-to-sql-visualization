import streamlit as st
import matplotlib.pyplot as plt
from utils.sql_executor import run_sql
from utils.llm import call_llm

# -------------------------------
# 🔹 SCHEMA (keep your updated one)
# -------------------------------
from utils.schema import schema


# -------------------------------
# 🔹 CLEAN SQL
# -------------------------------
def clean_sql(response):
    response = response.strip()
    response = response.replace("```sql", "").replace("```", "")

    if ";" in response:
        response = response.split(";")[0] + ";"

    if "select" in response.lower():
        idx = response.lower().find("select")
        response = response[idx:]

    return response.strip()


# -------------------------------
# 🔹 LLM CLASSIFIER
# -------------------------------
def classify_query(query, schema):
    prompt = f"""
You are a classifier.

DATABASE SCHEMA:
{schema}

Return ONLY one word:
YES → if query is related to database
NO → if not related

Query:
{query}

Answer:
"""
    res = call_llm(prompt).strip().lower()
    return "yes" in res


# -------------------------------
# 🔹 SQL GENERATION
# -------------------------------
def generate_sql(query, schema):
    prompt = f"""
You are an expert SQLite SQL generator.

DATABASE SCHEMA:
{schema}

IMPORTANT RELATIONSHIPS:
- customers.CustomerId = invoices.CustomerId
- invoices.InvoiceId = invoice_items.InvoiceId
- invoice_items.TrackId = tracks.TrackId
- tracks.AlbumId = albums.AlbumId
- albums.ArtistId = artists.ArtistId
- tracks.GenreId = genres.GenreId

TASK:
Convert the user query into a valid SQLite SELECT query.

RULES:
- Only SELECT queries
- No explanation
- No markdown
- Use JOINs when needed
- Use aggregation if required
- Use ORDER BY + LIMIT for top queries
- Output MUST start with SELECT

User Query:
{query}

SQL:
"""
    response = call_llm(prompt)
    return clean_sql(response)


# -------------------------------
# 🔹 SQL FIX (Retry)
# -------------------------------
def fix_sql(query, schema, bad_sql, error):
    prompt = f"""
You are an SQL expert.

Fix the SQL query.

Schema:
{schema}

Query:
{query}

Bad SQL:
{bad_sql}

Error:
{error}

Return ONLY corrected SQL.
"""
    return clean_sql(call_llm(prompt))


def execute_with_retry(query, schema):
    sql = generate_sql(query, schema)

    for _ in range(2):
        try:
            df = run_sql(sql)
            return df, sql
        except Exception as e:
            sql = fix_sql(query, schema, sql, str(e))

    raise Exception("SQL failed after retries")


# -------------------------------
# 🔹 GRAPH DECISION
# -------------------------------
def decide_graph(df, query):
    if len(df.columns) < 2:
        return {"plot": "no"}

    prompt = f"""
Decide if graph is needed.

Query: {query}
Columns: {list(df.columns)}

Return JSON:
{{
 "plot": "yes/no",
 "chart": "bar/line/pie",
 "x": "column",
 "y": "column"
}}
"""
    try:
        return eval(call_llm(prompt))
    except:
        return {"plot": "no"}


# -------------------------------
# 🔹 STREAMLIT UI
# -------------------------------
st.title("📊 Text-to-SQL with Visualization")

query = st.text_input("Enter your query:")

if st.button("Run Query"):

    if not query:
        st.warning("Please enter a query")
        st.stop()

    # -------------------------------
    # 🔹 CLASSIFY QUERY
    # -------------------------------
    if not classify_query(query, schema):
        st.subheader("💬 Response")
        st.markdown("""
Apologies! your query is not related to the available database.

Try asking:
- What is the total sales by country?
- Who are the top customers by spending?
- How many tracks are there in each genre?
- Which artists have the most albums?
""")
        st.stop()

    # -------------------------------
    # 🔹 EXECUTE SQL WITH RETRY
    # -------------------------------
    try:
        df, sql = execute_with_retry(query, schema)
    except Exception as e:
        st.error(f"SQL Error: {e}")
        st.stop()

    # -------------------------------
    # 🔹 DISPLAY
    # -------------------------------
    st.subheader("Generated SQL")
    st.code(sql, language="sql")

    col1, col2 = st.columns([2, 1])

    # TABLE
    with col1:
        st.subheader("Result Table")
        st.dataframe(df)

    # GRAPH
    with col2:
        graph = decide_graph(df, query)

        if graph.get("plot") == "yes":
            x = graph.get("x")
            y = graph.get("y")

            if x in df.columns and y in df.columns:
                st.subheader(f"{graph['chart'].capitalize()} Chart")

                fig, ax = plt.subplots()

                if graph["chart"] == "bar":
                    ax.bar(df[x], df[y])

                elif graph["chart"] == "line":
                    ax.plot(df[x], df[y])

                elif graph["chart"] == "pie":
                    ax.pie(df[y], labels=df[x], autopct="%1.1f%%")

                plt.xticks(rotation=45)
                st.pyplot(fig)
                
import requests

api_key = "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"

response = requests.post(
    "https://api.groq.com/openai/v1/chat/completions",
    headers={
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    },
    json={
        "model": "llama-3.1-8b-instant",
        "messages": [
            {"role": "user", "content": "Say hello"}
        ]
    }
)

print(response.json())