import streamlit as st
from streamlit_chat import message
import openai
import os
import Source.response as Response
import Source.DialogPrompt as Prompt
# import Source.mcts as MCTS
import json
# import Source.treegraph as treeBuild
# import Source.treegraphCriteria as treeBuildCriteria
from langchain.memory import ConversationBufferMemory
from streamlit_cookies_controller import CookieController
from streamlit_autorefresh import st_autorefresh
cookie_controller = CookieController()
from time import sleep
from datetime import datetime, UTC, timedelta
# from transformers import AutoTokenizer, AutoModelForCausalLM
# import torch

memory = ConversationBufferMemory(human_prefix="human", ai_prefix="AI",memory_key="history", return_messages=True)
st.title("Patient Problem Understanding")

USER_NAME = "user"
ASSISTANT_NAME = "assistant"
State_component = "State"
end_greeting = ['Thanks','thanks','Thank You','thank you','Thanks for your information','thanks for your instruction', 'thanks for your suggestions']

message_history = []

patient_messages = []
therapist_messages = []
therapist_messages_last_utterace = ""
patient_messages_last_utterace = ""
subset_list =[]
formatted_data = []
llm_call_trigured = 0
#############

import json
import statistics
import time
from typing import List, Tuple, Dict, Any, Union

from openai import OpenAI

# ---------------------------
# --- User-provided LLM call
# ---------------------------

def LLM_call_function(prompt: str) -> str:
    client = OpenAI(
        api_key="A",  # Replace with env var if needed
    )
    chat_completion = client.chat.completions.create(
        model="gpt-4o",
        temperature=0.7,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": "You are a safe, empathetic, and helpful assistant. Always output JSON."},
            {"role": "user", "content": prompt}
        ]
    )
    return str(chat_completion.choices[0].message.content)

# ---------------------------
# --- Prompts with context
# ---------------------------

ASPECTS = [
    "Emotional", "Empathic", "Naturalness","Caring", "Engagement"
]

EVAL_AND_FEEDBACK_PROMPT = """
You are an impartial evaluator for a mental health chatbot. You task is make respone more empathic, emotional, and real therapist natural response.
You can't give solution, coping stratigies because, It is problem understanding phase. You can't change the question sentence of current chatbot response.

Inputs:
- conversation history: {context}
- latest user query: {query}
- current chatbot response: {response}
- aspects: {aspects}

Task: For each aspect, provide:
  - You task is make respone more empathic, emotional, and real therapist natural response.
  - rationale (short, constructive text)
  - score (1–5 integer, higher is better)
  - You have to keep same question sentence of current chatbot response in your optimized response.
  - If user ask question, then you need to reminder that "this is problem understanding phase, I need to understand you more for better ssuggestion".
  - Keep your optimized responnse within 70 words.

Also provide one overall improvement suggestion (string).

Return a JSON object:
{{
  "EVAL_DICT": {{
      "Empathic": {{"rationale": "...", "score": 4}},
      "Naturalness":     {{"rationale": "...", "score": 3}},
      ...
  }},
  "SUGGESTION": "Be more specific about self-care strategies."
}}
"""

OPTIMIZER_PROMPT = """
You are an optimizer improving chatbot responses as like make respone more empathic, emotional, and real therapist natural response.
You can't give solution, coping stratigies because, It is problem understanding phase. You can't change the question sentence of current chatbot response.

Inputs:
- conversation history: {context}
- latest user query: {query}
- current chatbot response: "{current_response}"
- feedback: "{feedback}"

Task: 
 - Rewrite the response to more empathic, emotional, and real therapist like natural response.
 - You have to keep same question sentence of current chatbot response in your optimized response.
 - If user ask question, then you need to reminder that "this is problem understanding phase, I need to understand you more for better ssuggestion".
 - Keep your optimized response within 70 words.

Return a JSON object:
{{"response": "new improved response here"}}
"""

BASELINE_ANSWER_PROMPT = """
You are a  assistant for make respone more empathic, emotional, and real therapist natural response.
You can't give solution, coping stratigies because, It is problem understanding phase.
If user ask question, then you need to reminder that "this is problem understanding phase, I need to understand you more for better ssuggestion".

Conversation so far:
{context}

The user just asked: "{query}"

Provide a clear, supportive, safe, and empathetic answer.

Return a JSON object:
{{"answer": "your answer here"}}
"""

# ---------------------------
# --- Helpers
# ---------------------------

def safe_json_loads(text: str) -> Any:
    try:
        return json.loads(text)
    except Exception as e:
        raise ValueError(f"Could not parse JSON. Raw output:\n{text}") from e

# format conversation context

def format_context(history: List[Tuple[str, str]]) -> str:
    return "\n".join([f"{role}: {text}" for role, text in history])

# evaluation

def evaluate_response(response: str, query: str, context: str, aspects: List[str]) -> Tuple[float, Dict[str, Any], str]:
    aspects_str = ", ".join(aspects)
    prompt = EVAL_AND_FEEDBACK_PROMPT.format(context=context, query=query, response=response, aspects=aspects_str)
    raw = LLM_call_function(prompt)
    parsed = safe_json_loads(raw)
    eval_dict = parsed.get("EVAL_DICT", {})
    suggestion = parsed.get("SUGGESTION", "")
    scores = []
    for a in aspects:
        try:
            s = eval_dict[a]["score"]
            scores.append(float(s))
        except Exception:
            pass
    avg = statistics.mean(scores) if scores else 0.0
    return avg, eval_dict, suggestion

def optimizer_transition(current_response: str, feedback: str, query: str, context: str) -> str:
    prompt = OPTIMIZER_PROMPT.format(context=context, query=query, current_response=current_response, feedback=feedback)
    raw = LLM_call_function(prompt)
    parsed = safe_json_loads(raw)
    return parsed.get("response", raw).strip()

def generate_baseline_answer(query: str, context: str) -> str:
    prompt = BASELINE_ANSWER_PROMPT.format(context=context, query=query)
    raw = LLM_call_function(prompt)
    parsed = safe_json_loads(raw)
    return parsed.get("answer", raw).strip()

# ---------------------------
# --- Optimization pipeline
# ---------------------------

def optimize_query(query: str, baseline_response: str, context: str,
                   D: int = 2, W: int = 1, M: int = 1,
                   verbose: bool = True, sleep_between_calls: float = 0.0) -> Tuple[str, Dict[str, Any]]:
    aspects = ASPECTS
    if verbose:
        print("  Using aspects:", aspects)

    base_avg, base_eval, _ = evaluate_response(baseline_response, query, context, aspects)
    beam = [(baseline_response, base_avg, base_eval)]
    if verbose:
        print(f"  t=0 base score = {base_avg:.3f}")

    for t in range(1, D+1):
        if verbose:
            print(f"  depth t={t}/{D}")
        next_beam = []
        for (st_prev, _, eval_prev) in beam[:W]:
            _, _, suggestion = evaluate_response(st_prev, query, context, aspects)
            if verbose:
                print(f"    Suggestion: {suggestion[:80]}...")
            for m in range(M):
                st_candidate = optimizer_transition(st_prev, suggestion, query, context)
                cand_avg, cand_eval, _ = evaluate_response(st_candidate, query, context, aspects)
                next_beam.append((st_candidate, cand_avg, cand_eval))
                if verbose:
                    print(f"      Candidate m={m}, score={cand_avg:.3f}")
                if sleep_between_calls:
                    time.sleep(sleep_between_calls)
        if not next_beam:
            break
        beam = sorted(next_beam, key=lambda x: x[1], reverse=True)[:W]
        if verbose:
            print(f"    Top beam score now = {beam[0][1]:.3f}")

    final_response, final_score, final_eval = beam[0]
    return final_response, final_eval

# ---------------------------
# --- Entry points
# ---------------------------

def qa_optimize(history: List[Tuple[str, str]], user_query, baseResponse, **kwargs) -> Tuple[str, Dict[str, Any]]:
    """
    history: list of (role, text) tuples. Last entry must be ("user", query).
    """
    query = user_query
    context = history
    if kwargs.get("verbose", True):
        print(f"\nOptimizing user question: {query[:60]}...")
    baseline = baseResponse
    print("Baselinne", baseline)
    return optimize_query(query, baseline, context, **kwargs)

# ---------------------------
# --- Example usage
# ---------------------------

# if __name__ == "__main__":
#     history = [
#         ("user", "I’ve been stressed lately."),
#         ("assistant", "I hear you. Stress can feel overwhelming sometimes. Do you want to share what’s on your mind?"),
#         ("user", "I often feel anxious before exams. What can I do to calm down?")
#     ]

#     optimized_answer, evaluation = qa_optimize(history, D=2, W=1, M=1, verbose=True)
#     print("\nOptimized Answer:", optimized_answer)
#     # print("Evaluation Report:", json.dumps(evaluation, indent=2, ensure_ascii=False))


#############
def archive_messages(log_conversation_from_session):
    # Iterate through messages and separate them based on the 'Name' key
    """
    for message in log_conversation_from_session:
        message_history.append((message['Name'],':', message['msg'],' \n'))

    print("The Message")
    print(message_history)"""
    
    for message in log_conversation_from_session:
        if message['name'] == 'user':
            patient_messages.append(message['msg'])
        elif message['name'] == 'assistant':
            therapist_messages.append(message['msg'])
    
    for i in range(len(patient_messages)):
        message_history.append("Patient :" + patient_messages[i] + '\n')
        message_history.append("Therapist :" + therapist_messages[i] + '\n')

def Conversation_flow_handeling(HandledTopic):
    # if HandledTopic =='Problem Understanding Topic':
    #     return "Hello, I’m truly sorry. It seems you may be going through a very difficult situation. But I’d like to first understand what has been happening and how these changes came about. As example, exam pressure, presentationn issue."
    
    # elif HandledTopic =='Thought-Pattern Understanding Topic':
    #     return "I understood your situation, and I am so sorry to hear that. But, I want  to understand your current thought or thinking for this situation. As like: I can't do that, Maybe I am not perfect for that or something else"

    # elif HandledTopic =='Feeling and Physical Symptoms Understanding Topic': 
    #     return "I understood your situation, and I am so sorry to hear that. But, I want  to understand your current feelings and any physical reaction as like: sad, depressed, anxious and heartbeat increasing or something else"    
    

    # elif HandledTopic =='Behavior Pattern Understanding Topic': 
    #      return "I understood your situation, and I am so sorry to hear that. But, I want  to understand your current change of habit, daily life activities"
    
    if HandledTopic == 'Problem Understanding Topic':
       return "こんにちは。本当に申し訳ありません。とても大変な状況にいらっしゃるのかもしれませんね。ですが、まずは何が起きていて、どのようにこの変化が生じたのかを理解したいと思っています。例えば、試験のプレッシャーや発表に関する悩みなどです。"

    elif HandledTopic == 'Thought-Pattern Understanding Topic':
        return "あなたの状況を理解しました。本当に大変だったと思います。ただ、この状況に対する現在の考え方や思考を理解したいです。例えば、「できない」「自分は完璧ではないかもしれない」などの考えです。"

    elif HandledTopic == 'Feeling and Physical Symptoms Understanding Topic': 
        return "あなたの状況を理解しました。本当に大変だったと思います。ただ、今の気持ちや体の反応を理解したいです。例えば、悲しい、憂うつ、不安、動悸がする、などです。"

    elif HandledTopic == 'Behavior Pattern Understanding Topic': 
        return "あなたの状況を理解しました。本当に大変だったと思います。ただ、最近の習慣や日常生活の変化について理解したいです。"

if "chat_log" not in st.session_state:
    st.session_state.chat_log = []
    st.session_state.state_log = []


if 'count' not in st.session_state: 
    st.session_state.count = 0

if st.chat_input:
    st.session_state.count += 1

if 'topic' not  in st.session_state:
    st.session_state.topic = None

if 'chat_history' not in st.session_state:
    st.session_state.chat_history = None

if "action" not in st.session_state:
    st.session_state.action = None

# if "state_value" not in st.session_state:
#     st.session_state.state_value = None

if "risk_value" not in st.session_state:
    st.session_state.risk_value = 0

if 'currentAct' not in st.session_state:
        st.session_state.currentAct = None

if 'ActTrack' not in st.session_state:
        st.session_state.ActTrack = []

if "selfdis_value" not in st.session_state:
    st.session_state.selfdis_value = 1

if "finish" not in st.session_state:
    st.session_state.finish = 1

print('Count = ' + str(st.session_state.count))

utterance_list = []
user_msg = st.chat_input("Enter Your Thought")

if user_msg:
    for chat in st.session_state.chat_log:
        with st.chat_message(chat["name"]):
            st.write(chat["msg"])

    with st.chat_message(USER_NAME):
        st.write(user_msg)
    
    if st.session_state.count >= 1:
        
        # Save in Memory for Management
        if st.session_state.chat_history is None:
            st.session_state.chat_history = []
        else:
            for message in st.session_state.chat_history:
                memory.save_context({'input':message['human']},{'output':message['AI']})
        
        archive_messages(st.session_state.chat_log)

        topicPrompt = Prompt.TopicManagerV2(st.session_state.chat_history,user_msg, st.session_state.topic, st.session_state.ActTrack)
        topic_data = Response.dialogueStateDetection(topicPrompt)
        topic_data_json = json.loads(topic_data)
        print(topic_data_json)

        topic = topic_data_json["predictions"]["TopicName"]
        topicStatus = topic_data_json["predictions"]["ActionState"]
        st.session_state.topic = topic
        print("Current: ", st.session_state.topic)
        
        topic_targetated_order = ['Problem Understanding Topic', 'Thought-Pattern Understanding Topic', 'Feeling and Physical symtomps Understanding Topic', 'Behavior Pattern Understanding Topic','Intervention Topic']
        
        # if topic not in st.session_state.ActTrack:
        #   st.session_state.ActTrack.append(topic)
        
        # if  st.session_state.ActTrack:  # check st.session_state.ActTrack not empty
        #     idx = len( st.session_state.ActTrack) - 1   # last index of st.session_state.ActTrack 
        #     if idx < len(topic_targetated_order):   # make sure topic_targetated_order  has that index
        #         if topic_targetated_order[idx] == st.session_state.ActTrack[idx]:
        #             print("Match:", topic_targetated_order[idx])
        #         else:
        #             print("Not match:", topic_targetated_order[idx], "!=", st.session_state.ActTrack[idx])
        #             corrected_topic = topic_targetated_order[idx]
                    
        #             # Remove last incorrect topic
        #             st.session_state.ActTrack.pop()
                    
        #             # Append corrected topic
        #             st.session_state.ActTrack.append(corrected_topic) 
                          
        #             base_response = Conversation_flow_handeling(corrected_topic)
        #             # Optionally update the current topic variable
        #             topic = corrected_topic
        #             llm_call_trigured = 1
        #             print("Corrected Topic: ", topic)
        #     else:
        #         print("Targated is shorter, no element to compare.")
        # else:
        #     print("Track List is Empty")
        # Next expected index
        
        idx = len(st.session_state.ActTrack)

        if idx < len(topic_targetated_order):
            expected_topic = topic_targetated_order[idx]

            if topic in st.session_state.ActTrack:
                #  Duplicate → do nothing
                print("Duplicate ignored:", topic)  

            else:
                #  Check skipped vs correct
                if topic != expected_topic:
                    print("Skipped detected. Expected:", expected_topic, "Got:", topic)
                    topic = expected_topic
                    
                    # Trigger response
                    base_response = Conversation_flow_handeling(topic)
                    llm_call_trigured = 1
                else:
                    print("Correct:", topic)

                #  Append only after duplicate check
                st.session_state.ActTrack.append(topic)
                print("Using Topic:", topic)
        else:
          print("All topics already completed.")

        print("Track: ", st.session_state.ActTrack)

        slot_prompt = Prompt.Act_generation_prompt(st.session_state.chat_history, user_msg, st.session_state.currentAct,topicStatus,topic)
        slot_data = Response.dialogueStateDetection(slot_prompt)
        data_slot = json.loads(slot_data)
        print(data_slot)

        # Calculate max utility slot name
        DialogueActs = data_slot["predictions"][0]["dialogueActs"]
        max_act = max(DialogueActs, key=lambda s: s["probability"] * s["reward"])
        final_act = max_act["name"]
        print("Act :", final_act)

        st.session_state.currentAct = final_act
                
        promptType = Prompt.problem_understanding_response(st.session_state.currentAct,message_history,user_msg)
        if llm_call_trigured != 1:
           base_response = Response.response_Generation_from_GPT4_test(promptType,user_msg,memory)
        # optimized_answer, evaluation = qa_optimize(st.session_state.chat_history,user_msg,base_response, D=2, W=1, M=1, verbose=True)
        print("\nOptimized Answer:", base_response)
        if final_act == "end_conversation_act":
            if  st.session_state.finish == 1:
                # base_response = base_response+'  '+ 'As well as, I want to finish this conversation.'
                base_response = base_response+'  '+ 'それから、この会話を終わりにしたいと思います。'
                st.session_state.finish +=3
        
        # Save in Session
        message = {'human':user_msg,'AI':base_response}
        st.session_state.chat_history.append(message)
        llm_call_trigured = 0
    
    with st.chat_message(ASSISTANT_NAME):
        assistant_msg = ""
        assistant_response_area = st.empty()
        
        # for chunk in response:
        tmp_assistant_msg = base_response
        assistant_msg += tmp_assistant_msg
        assistant_response_area.write(assistant_msg)

    st.session_state.chat_log.append({"name": USER_NAME, "msg": user_msg})
    st.session_state.chat_log.append({"name": ASSISTANT_NAME, "msg": assistant_msg})
