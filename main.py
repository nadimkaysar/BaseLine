import os
from langchain.llms import OpenAI
from langchain.chains import ConversationChain
from langchain.memory import ConversationBufferMemory
from langchain.prompts.prompt import PromptTemplate
from langchain_community.chat_models import ChatOpenAI
import streamlit as st
from streamlit_chat import message
import openai
import os
import json
import Source.response as Response
import Source.SystemPrompt as PromptInisilization
memory = ConversationBufferMemory(human_prefix="human", ai_prefix="AI",memory_key="history", return_messages=True)

st.title("Well-Being Chatbot System")
USER_NAME = "user"
ASSISTANT_NAME = "assistant"

if 'reframing_slot' not in st.session_state:
     st.session_state.reframing_slot = 1


utterance_list = []
user_msg = st.chat_input("Enter Your Thought")
if "chat_log" not in st.session_state:
    st.session_state.chat_log = []
    st.session_state.state_log = []

if user_msg:
    for chat in st.session_state.chat_log:
      with st.chat_message(chat["name"]):
        st.write(chat["msg"])

    with st.chat_message(USER_NAME):
        st.write(user_msg)
    test_key = 1
    
    # Save in Memory for Management
    
    if 'chat_history' not in st.session_state:
         st.session_state.chat_history = []
    else:
        for message in st.session_state.chat_history:
          memory.save_context({'input':message['human']},{'output':message['AI']})

    print("Chat history",st.session_state.chat_history)
    

    responePrompt = PromptInisilization.counseling_prompt()
    response = Response.response_generation_from_antropic(responePrompt,user_msg,memory)

    # Save in Session
    message = {'human':user_msg,'AI':response}
    st.session_state.chat_history.append(message)

    with st.chat_message(ASSISTANT_NAME):
        assistant_msg = ""
        assistant_response_area = st.empty()
        # for chunk in response:
        tmp_assistant_msg = response
        assistant_msg += tmp_assistant_msg
        assistant_response_area.write(assistant_msg)

    #st.session_state.state_log.append({"name": State_component, "msg": subset})
    # print("State Log Print for the system: ", st.session_state.state_log )
    st.session_state.chat_log.append({"name": USER_NAME, "msg": user_msg})
    st.session_state.chat_log.append({"name": ASSISTANT_NAME, "msg": assistant_msg})

        

