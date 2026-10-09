from langgraph.graph import StateGraph, START, END
from typing import TypedDict, Annotated

from langchain_core.messages import (
    BaseMessage,
    SystemMessage,
    HumanMessage,
)

from langchain_openai import ChatOpenAI
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.graph.message import add_messages

from psycopg_pool import ConnectionPool

import streamlit as st


# ============================================================
# API KEYS
# ============================================================

OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
db_API_KEY = st.secrets["DB_API_KEY"]


# ============================================================
# LLM
# ============================================================

llm = ChatOpenAI(
    model="gpt-4.1",
    temperature=0.6,
    openai_api_key=OPENAI_API_KEY
)


# ============================================================
# CHAT STATE
# ============================================================

class ChatState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    component: str

def systemPrompt(component):
    SYSTEM_PROMPT1 = f"""
     Context:
          You are a mental health support specialist helping students improve self-esteem and confidence related to academic challenges.
    
      Goal:
          Help students develop a healthier self-view by understanding their academic problems, negative thoughts, and behavioral patterns.
    
      Guidelines:
        1. Explore the student's current academic problems and relevant past experiences.
        2. Identify unhelpful behaviors, negative thoughts, and beliefs affecting self-esteem.
        3. Respond with empathy, warmth, and nonjudgment; validate feelings without reinforcing negative self-beliefs.
        4. Help students recognize their strengths, achievements, and positive qualities.
        5. Ask one open-ended question at a time and suggest small, achievable actions.
        6. Before ending the conversation, provide at least **three practical, personalized recommendations** to improve self-esteem and confidence.
    
      Keep your response within 50 to 60 words. 
    """
    return SYSTEM_PROMPT1


def systemPrompt_second(component):
    SYSTEM_PROMPT1 = f"""
    Context: You are a mental health support specialist helping students improve self-esteem and confidence related to academic challenges.

          Goal: Help students improve their self-view by reviewing progress, exploring underlying issues, identifying negative thoughts, and setting achievable goals.

          Guidelines:
            1. Follow up on the student's experiences and challenges since the first session.
            2. Explore family dynamics and relationship issues affecting academic confidence and self-esteem.
            3. Ask miracle questions to help the student identify desired changes in their life.
            4. Identify negative thoughts and beliefs that affect self-esteem and encourage balanced thinking.
            5. Collaboratively set realistic, achievable goals to improve self-esteem and academic confidence.
            6. Respond with empathy, warmth, and nonjudgment; validate feelings without reinforcing negative self-beliefs.
            7. Ask one open-ended question at a time and suggest small, achievable actions.
            8. Before ending the conversation, provide at least **three practical, personalized recommendations** based on the student's goals.

          Keep your response within 50 to 60 words. 
    """
    return SYSTEM_PROMPT1



# ============================================================
# CHAT NODE
# ============================================================

def chat_node(state: ChatState):

    messages = state["messages"]

    component_action = state.get(
        "component",
        ""
    )

    prompt = systemPrompt(component_action)

    print("System Prompt", prompt)

    messages_with_system_prompt = [
        SystemMessage(content=prompt),
        *messages
    ]

    response = llm.invoke(
        messages_with_system_prompt
    )

    return {
        "messages": [response]
    }

# ============================================================
# DATABASE CONNECTION POOL
# ============================================================
DB_URI = db_API_KEY
connection_kwargs = {
    "autocommit": True,
    "prepare_threshold": 0,
}

DB_URI = db_API_KEY

connection_kwargs = {
    "autocommit": True,
    "prepare_threshold": 0,
}

pool = ConnectionPool(
    conninfo=DB_URI,
    kwargs=connection_kwargs,
    min_size=1,
    max_size=10,
    max_lifetime=300,
    max_idle=60,
    timeout=30,
    open=True,
)

pool.wait()



# ============================================================
# APPLICATION-SPECIFIC THREAD TABLE
# ============================================================

def setup_conversation_table():
    """Create the table used to map PatientID to conversation threads."""

    create_table_sql = """
    CREATE TABLE IF NOT EXISTS conversation_threads (
        thread_id TEXT PRIMARY KEY,
        patient_id TEXT NOT NULL,
        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
    )
    """

    create_index_sql = """
    CREATE INDEX IF NOT EXISTS idx_conversation_threads_patient_id
    ON conversation_threads (patient_id)
    """

    create_created_index_sql = """
    CREATE INDEX IF NOT EXISTS idx_conversation_threads_patient_created
    ON conversation_threads (patient_id, created_at DESC)
    """

    with pool.connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(create_table_sql)
            cursor.execute(create_index_sql)
            cursor.execute(create_created_index_sql)
        conn.commit()

checkpointer = PostgresSaver(pool)

checkpointer.setup()

# Create PatientID <-> thread_id mapping table
setup_conversation_table()


# ============================================================
# REGISTER THREAD
# ============================================================

def register_thread(thread_id, patient_id):
    sql = """
    INSERT INTO conversation_threads (thread_id, patient_id)
    VALUES (%s, %s)
    ON CONFLICT (thread_id) DO UPDATE
    SET patient_id = EXCLUDED.patient_id
    """

    with pool.connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                sql,
                (
                    str(thread_id),
                    str(patient_id),
                ),
            )

# ============================================================
# GET THREADS FOR PATIENT
# ============================================================

def retrieve_threads_for_patient(patient_id):
    if not patient_id:
        return []

    sql = """
    SELECT thread_id
    FROM conversation_threads
    WHERE patient_id = %s
    ORDER BY created_at DESC
    """

    try:
        with pool.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, (str(patient_id),))
                rows = cursor.fetchall()

        return [row[0] for row in rows]

    except Exception as e:
        print("Error retrieving patient threads:")
        print(e)
        return []

# ============================================================
# CHECK THREAD OWNERSHIP
# ============================================================

def thread_belongs_to_patient(thread_id, patient_id):
    if not thread_id or not patient_id:
        return False

    sql = """
    SELECT 1
    FROM conversation_threads
    WHERE thread_id = %s
      AND patient_id = %s
    LIMIT 1
    """

    try:
        with pool.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    sql,
                    (
                        str(thread_id),
                        str(patient_id),
                    ),
                )
                return cursor.fetchone() is not None

    except Exception as e:
        print("Thread ownership check error:")
        print(e)
        return False


# ============================================================
# GRAPH
# ============================================================

graph = StateGraph(ChatState)

graph.add_node(
    "chat_node",
    chat_node
)

graph.add_edge(
    START,
    "chat_node"
)

graph.add_edge(
    "chat_node",
    END
)


# ============================================================
# COMPILE GRAPH
# ============================================================

if checkpointer is None:

    raise RuntimeError(
        "Checkpointer not initialized. "
        "Database connection failed."
    )

chatbot = graph.compile(
    checkpointer=checkpointer
)
