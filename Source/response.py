from langchain.llms import OpenAI
from langchain.chains import ConversationChain
from langchain.memory import ConversationBufferMemory
import anthropic
from langchain.memory import ConversationBufferMemory
from langchain.prompts.prompt import PromptTemplate
from langchain.schema import messages_to_dict
from langchain.schema import messages_from_dict
from langchain_community.chat_models import ChatOpenAI
import openai
from langchain_community.llms import OpenAI
from langchain.llms import OpenAI
from openai import OpenAI
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI
#from langchain.chat_models import ChatOpenAI
# pip install langchain openai --upgrade this is use for update
from langchain import OpenAI
from openai import OpenAI
import langchain
#from pydantic import BaseModel
from langchain.prompts import (
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
    ChatPromptTemplate,
    MessagesPlaceholder
)
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationChain
import streamlit as st
OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]

antropic_API_KEY = st.secrets["Antropic_API_KEY"]


# memory_final = ConversationBufferMemory(memory_key="history", return_messages=True)
# memory_final = ConversationBufferMemory(human_prefix="Patient", ai_prefix="Therapist", memory_key="history", return_messages=True)

def response_Genration_from_GPT4(tem, user_query,conversation_memory):
  system_msg_template = SystemMessagePromptTemplate.from_template(template=tem)

  human_msg_template = HumanMessagePromptTemplate.from_template(template="{input}")
  prompt_template = ChatPromptTemplate.from_messages(
                                                    [system_msg_template,
                                                     MessagesPlaceholder(variable_name="history"),
                                                     human_msg_template])

  conversation = ConversationChain(memory=conversation_memory, 
                                   prompt=prompt_template, 
                                   llm=ChatOpenAI(
                                       model= 'gpt-4.1',
                                       temperature=0.6, 
                                       openai_api_key=OPENAI_API_KEY), verbose=True)
  response = conversation.predict(input=user_query)
  return response

def response_Generation_from_GPT4_test(tem, user_query,memory_buffer):
  system_msg_template = SystemMessagePromptTemplate.from_template(template=tem)

  human_msg_template = HumanMessagePromptTemplate.from_template(template="{input}")
  prompt_template = ChatPromptTemplate.from_messages(
                                                    [system_msg_template,
                                                     MessagesPlaceholder(variable_name="history"),
                                                     human_msg_template])
  # Confirm expected inputs
  prompt_template = prompt_template.partial(user_message=user_query)
  print("Prompt expects:", prompt_template.input_variables)
  conversation = ConversationChain(memory=memory_buffer, 
                                   prompt=prompt_template, 
                                   llm=ChatOpenAI(
                                       model= 'gpt-4.1',
                                       temperature=0.6, 
                                       openai_api_key=OPENAI_API_KEY), 
                                       verbose=True)
  response = conversation.predict(input=user_query)
  return response


def dialogueStateDetection(prompt):
    client = OpenAI(
            # defaults to os.environ.get("OPENAI_API_KEY")
            api_key= OPENAI_API_KEY,
        )
    chat_completion = client.chat.completions.create(
            model="gpt-4o",
            temperature = 0.5,
            response_format={ "type": "json_object" },
            messages=[
                    {"role": "system", "content": "Follow user Prompt"},
                    {"role": "user", "content": prompt}
                ]
        )
    chat_completion = str(chat_completion.choices[0].message.content)
    return chat_completion



def SubsetSelection(prompt):
    client = OpenAI(
            # defaults to os.environ.get("OPENAI_API_KEY")
            api_key=OPENAI_API_KEY,
        )

    chat_completion = client.chat.completions.create(
            model="gpt-4o",
            temperature = 0,
            response_format={ "type": "json_object" },
            messages=[
                    {"role": "system", "content": "Follow user Prompt"},
                    {"role": "user", "content": prompt}
                ]
        )
    chat_completion = str(chat_completion.choices[0].message.content)
    return chat_completion

def response_generation_from_antropic(tem, user_query,conversation_memory):

    system_msg_template = SystemMessagePromptTemplate.from_template(template=tem)

    human_msg_template = HumanMessagePromptTemplate.from_template(template="{input}")
    prompt_template = ChatPromptTemplate.from_messages(
                                                        [system_msg_template,
                                                        MessagesPlaceholder(variable_name="history"),
                                                        human_msg_template])
    Anthropic_llm = ChatAnthropic(model="claude-3-7-sonnet-20250219",
                        temperature = 0.6,
                        anthropic_api_key= antropic_API_KEY)
    
    conversation = ConversationChain(memory = conversation_memory, 
                                   prompt = prompt_template, 
                                   llm = Anthropic_llm, 
                                   verbose=True)
    response = conversation.predict(input=user_query)
    res1 = response.strip()
    res2 = res1.lstrip()
    res3 = res2.rstrip()
    return str(res3)


def SubsetSelection_Anthropic(prompt):
    client = anthropic.Anthropic(
            # defaults to os.environ.get("OPENAI_API_KEY")
            api_key= antropic_API_KEY
        )
    message = client.messages.create(
        model="claude-3-7-sonnet-20250219",
        max_tokens=2000,
        temperature=0.1,
        system="You need to follow user role Prompt instruction, you need to give just json response without any other text",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": """You need to follow  Prompt instruction: {prompt} for response generation.
                        You have to follow specific json response format which I set below:
                            {
                            "input": {
                                "user_previous_utterance": "string",
                                "user_last_utterance": "string",
                                "emotional_state": {
                                "emotions": [
                                    {
                                    "type": "string",
                                    "intensity": "string"
                                    }
                                ]
                                },
                                "context": "First session. No specific incidents mentioned"
                            },
                            "predictions": {
                                "Mindfulness": {
                                "possible_states": [
                                    {
                                    "mental_state_description": "Emotion: 'string' Symptoms: 'string'",
                                    "probability": "number",
                                    "reward": "number"
                                    }
                                ]
                                },
                                "Distress_Tolerance": {
                                "possible_states": [
                                    {
                                    "mental_state_description": "Emotion: 'string' Symptoms: 'string'",
                                    "probability": "number",
                                    "reward": "number"
                                    }
                                ]
                                },
                                "Interpersonal_Effectiveness": {
                                "possible_states": [
                                    {
                                    "mental_state_description": "Emotion: 'string' Symptoms: 'string'",
                                    "probability": "number",
                                    "reward": "number"
                                    },
                                ]
                                },
                                "Emotion_Regulation": {
                                "possible_states": [
                                    {
                                    "mental_state_description": "Emotion: 'string' Symptoms: 'string'",
                                    "probability": "number",
                                    "reward": "number"
                                    }
                                ]
                                },
                                "IsUserAskQuestion": "number"
                            }
                            }
                        """
                    }
                ]
            }
        ]
    )
    return message.content[0].text



def SubsetSelection_Anthropic_test(prompt):
    client = anthropic.Anthropic(
            # defaults to os.environ.get("OPENAI_API_KEY")
            api_key= antropic_API_KEY
        )
    message = client.messages.create(
        model="claude-3-7-sonnet-20250219",
        max_tokens=2000,
        temperature=0.1,
        system="You need to follow user role Prompt instruction, you need to give just json response without any other text",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": """You need to follow  Prompt instruction: {prompt} for response generation.
                        You have to follow specific json response format which I set below:
                         "input": {
                            "user_previous_utterance": "string",
                            "user_last_utterance": "string",
                            "emotional_state": {
                            "emotions": [
                                {
                                "type": "string",
                                "intensity": "string"
                                }
                            ]
                            },
                            "context": "First session. No specific incidents mentioned"
                        },
                        "predictions": {
                            "Mindfulness": {
                            "possible_states": [
                                {
                                "mental_state_description": "Emotion: 'string' Symptoms: 'string'",
                                "probability": "number",
                                "rewards":[
                                    {
                                    "Impact_on_well_being_reward": "number",
                                    "Impact_on_well_being_weight": "number"
                                    },
                                    {
                                    "Patient_goal_achievement_reward": "number",
                                    "Patient_goal_achievement_weight": "number"
                                    },
                                    {
                                    "Patient_satisfaction_reward": "number",
                                    "Patient_satisfaction_weight": "number",
                                    },
                                    {
                                    "Feedback_Quality_reward": "number",
                                    "Feedback_Quality_weight": "number"
                                    }
                                ]
                                }
                            ]
                            },
                            "Distress_Tolerance": {
                            "possible_states": [
                                {
                                "mental_state_description": "Emotion: 'string' Symptoms: 'string'",
                                "probability": "number",
                                "rewards":[
                                    {
                                    "Impact_on_well_being_reward": "number",
                                    "Impact_on_well_being_weight": "number"
                                    },
                                    {
                                    "Patient_goal_achievement_reward": "number",
                                    "Patient_goal_achievement_weight": "number"
                                    },
                                    {
                                    "Patient_satisfaction_reward": "number",
                                    "Patient_satisfaction_weight": "number",
                                    },
                                    {
                                    "Feedback_Quality_reward": "number",
                                    "Feedback_Quality_weight": "number"
                                    }
                                ]
                                }
                            ]
                            },
                            "Interpersonal_Effectiveness": {
                            "possible_states": [
                                {
                                "mental_state_description": "Emotion: 'string' Symptoms: 'string'",
                                "probability": "number",
                                "rewards":[
                                    {
                                    "Impact_on_well_being_reward": "number",
                                    "Impact_on_well_being_weight": "number"
                                    },
                                    {
                                    "Patient_goal_achievement_reward": "number",
                                    "Patient_goal_achievement_weight": "number"
                                    },
                                    {
                                    "Patient_satisfaction_reward": "number",
                                    "Patient_satisfaction_weight": "number",
                                    },
                                    {
                                    "Feedback_Quality_reward": "number",
                                    "Feedback_Quality_weight": "number"
                                    }
                                ]
                                },
                            ]
                            },
                            "Emotion_Regulation": {
                            "possible_states": [
                                {
                                "mental_state_description": "Emotion: 'string' Symptoms: 'string'",
                                "probability": "number",
                                "rewards":[
                                    {
                                    "Impact_on_well_being_reward": "number",
                                    "Impact_on_well_being_weight": "number"
                                    },
                                    {
                                    "Patient_goal_achievement_reward": "number",
                                    "Patient_goal_achievement_weight": "number"
                                    },
                                    {
                                    "Patient_satisfaction_reward": "number",
                                    "Patient_satisfaction_weight": "number",
                                    },
                                    {
                                    "Feedback_Quality_reward": "number",
                                    "Feedback_Quality_weight": "number"
                                    }
                                ]
                                }
                            ]
                            },
                        "IsUserAskQuestion": "number" 
                        }
                        }
                        """
                    }
                ]
            }
        ]
    )
    return message.content[0].text
