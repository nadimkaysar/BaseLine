import streamlit as st
from streamlit_chat import message
import openai
import os
import Source.response as Response
import Source.SystemPrompt as PromptInisilization
# import Source.mcts as MCTS
# import Source.mctsv2 as MCTSv2
import json
import Source.treegraph as treeBuild
# import Source.treegraphCriteria as treeBuildCriteria
from langchain.memory import ConversationBufferMemory
from streamlit_cookies_controller import CookieController
from streamlit_autorefresh import st_autorefresh
cookie_controller = CookieController()
from time import sleep
from datetime import datetime, UTC, timedelta

memory = ConversationBufferMemory(human_prefix="human", ai_prefix="AI",memory_key="history", return_messages=True)

# Create a folder for all chat logs
# LOG_DIR = "/Volumes/Research/Code/MentalHealthSystem/Log/P3"
# os.makedirs(LOG_DIR, exist_ok=True)

# Create unique session log file
# if "log_file" not in st.session_state:
#     timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
#     st.session_state.log_file = os.path.join(LOG_DIR, f"chat_{timestamp}.txt")

# # Function to log messages to the session-specific file
# def log_message(role, action, message):
#     timestamp_time = datetime.now().strftime("%H:%M:%S")
#     log_entry = f"[{timestamp_time}] {action} {role}: {message}\n"
#     with open(st.session_state.log_file, "a", encoding="utf-8") as f:
#         f.write(log_entry)


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

if "depression_level" not in st.session_state:
    st.session_state.depression_level = None

if "anxiety_level" not in st.session_state:
    st.session_state.anxiety_level = None

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
    
    return message_history

st.title("Well-Being Support For Student")
if "chat_log" not in st.session_state:
    st.session_state.chat_log = []
    st.session_state.state_log = []

utterance_list = []
user_msg = st.chat_input("Enter Your Thought")

if 'count' not in st.session_state: 
    st.session_state.count = 0

if st.chat_input:
    st.session_state.count += 1

if 'FlagState' not  in st.session_state:
    st.session_state.FlagState = None

if 'chat_history' not in st.session_state:
    st.session_state.chat_history = None

if "action" not in st.session_state:
    st.session_state.action = None

if "state_value" not in st.session_state:
    st.session_state.state_value = None

if "selfdis_value" not in st.session_state:
    st.session_state.selfdis_value = 1

if "risk_value" not in st.session_state:
   st.session_state.risk_value = 0

print('Count = ' + str(st.session_state.count))

if user_msg:
    for chat in st.session_state.chat_log:
        with st.chat_message(chat["name"]):
            st.write(chat["msg"])

    with st.chat_message(USER_NAME):
        st.write(user_msg)
    
    # if 'action' not in st.session_state:
    # st.session_state.action = None

    # promptInitilize and StateDefine
    # stateSelectionPrompt = PromptInisilization.stateDefine(history, user_msg)
   
    if st.session_state.count >= 1:       
        # Determine The Reward GPT
        Subset_prompt  = PromptInisilization.determine_reward_final(message_history,user_msg,st.session_state.action)
        actual_reward = Response.SubsetSelection(Subset_prompt)
        print("Before Extract Reawrd: ",actual_reward)
        reward_data = json.loads(actual_reward)
        print("Reward After Json Data", reward_data)

        # Determine The Reward Claude
        # Subset_prompt  = PromptInisilization.determine_reward_final(message_history,user_msg,st.session_state.action)
        # actual_reward = Response.SubsetSelection_Claude(Subset_prompt)
        # print("Before Extract Reawrd: ",actual_reward)
        # reward_data = json.loads(actual_reward)
        # print("Reward After Json Data", reward_data)
        
        # Determine The Reward with Criteria OpenAI
        # Subset_prompt  = PromptInisilization.subset_detection_with_weight(message_history,user_msg,st.session_state.action)
        # actual_reward = Response.SubsetSelection(Subset_prompt)
        # print("Before Extract Reawrd: ",actual_reward)
        # reward_data = json.loads(actual_reward)
        # print("Reward After Json Data", reward_data)

        # Determine The Reward with Criteria Antropic
        # Subset_prompt  = PromptInisilization.subset_detection_with_weight(message_history,user_msg,st.session_state.action)
        # actual_reward = Response.SubsetSelection_Anthropic_test(Subset_prompt)
        # print("Before Extract Reawrd: ",actual_reward)
        # reward_data = json.loads(actual_reward)
        # print("Reward After Json Data", reward_data)
    
    
        # Data Extraction
        best_action = treeBuild.dataImport(reward_data)

        # st.session_state.action = best_action
        history = archive_messages(st.session_state.chat_log)
        print(history)
        # MCTS Code Implimentation
        # mcts_prompt = MCTSv2.MCTS_prompt(history,user_msg)
        # best_action = MCTSv2.call_MCTS(mcts_prompt)
        # print("Test Subset from MCTS", best_action)
        # subset = "problem_understand"

        
        # promptType = PromptInisilization.EnglishConversationPromptForGPT4oV8_testing(message_history,best_action,user_msg)
        # promptType = PromptInisilization.EnglishConversationPromptFor_Student_V11(message_history,best_action,user_msg)
        if st.session_state.count >= 1 and st.session_state.count <= 8:
             promptType = PromptInisilization.self_explorerV2(message_history,user_msg,st.session_state.depression_level,st.session_state.anxiety_level,best_action)
        
        if st.session_state.count >= 9:
             promptType = PromptInisilization.dbt_counseling(message_history,best_action,user_msg,st.session_state.depression_level,st.session_state.anxiety_level)
        
        # promptType = PromptInisilization.dbt_support(message_history,best_action,user_msg,st.session_state.depression_level,st.session_state.anxiety_level)
        # promptType = PromptInisilization.JapaneseConversationPromptFor_Student_V12(message_history,best_action,user_msg)
        # promptType = PromptInisilization.EnglishConversationPromptForGPT4oV7_japansese(message_history,best_action,user_msg)
    
        # promptType = PromptInisilization.JapaneseConversationPromptForGPT4o(message_history,subset,patient_messages)
    
        # Save in Memory for Management
        if st.session_state.chat_history is None:
            st.session_state.chat_history = []
        else:
            for message in st.session_state.chat_history:
                memory.save_context({'input':message['human']},{'output':message['AI']})

        # Response Generation
        #response = Response.response_generation_from_antropic(promptType,user_msg,memory)
        response = Response.response_Generation_from_GPT4_test(promptType,user_msg,memory)
        
        if st.session_state.selfdis_value == 1:
            response =  response +'  '+ "Finally, please keep in mind that this is the problem-understanding phase. I will ask a few questions to better understand your situation so I can support you effectively."  
            # response =  response +'  '+ "最後に、これは問題を理解するための段階であることを忘れないでください。あなたをできるだけよく支えるために、私はあなたのことを理解したいと思っています。"
            st.session_state.selfdis_value += 2
        
        print("Final Response: ",response)
        
        # Save in Session
        message = {'human':user_msg,'AI':response}
        st.session_state.chat_history.append(message)

        # log_message("User", "          ", user_msg)
        # log_message("Assistant",best_action,response)

    with st.chat_message(ASSISTANT_NAME):
        assistant_msg = ""
        assistant_response_area = st.empty()
        
        # for chunk in response:
        tmp_assistant_msg = response
        assistant_msg += tmp_assistant_msg
        assistant_response_area.write(assistant_msg)

    # st.session_state.state_log.append({"name": State_component, "msg": best_action})
    # print("State Log Print for the system: ", st.session_state.state_log )
    st.session_state.chat_log.append({"name": USER_NAME, "msg": user_msg})
    st.session_state.chat_log.append({"name": ASSISTANT_NAME, "msg": assistant_msg})
