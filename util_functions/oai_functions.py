import logging
from flask import jsonify
from openai.types.beta.threads.text_content_block import TextContentBlock
from config import OPENAI_CLIENT as client, chat_session_serializer, agent_session_serializer
import re

from services.sql_service import get_agent_data
from util_functions.functions import get_agent_session

class Text:
    def __init__(self, value, annotations=[]):
        self.value = value
        self.annotations = annotations

class TextContentBlock:
    def __init__(self, text, type='text'):
        self.text = text
        self.type = type

class MessageContent:
    def __init__(self, type, text):
        self.type = type
        self.text = text

def convert_content(content_list):
    converted_content = []
    for content in content_list:
        converted_content.append({
            'Type': content.type,
            'Text': {
                'Text': {
                    'value': content.text.value,
                    'annotations': content.text.annotations
                }
            }
        })
    return converted_content

def convert_attachments(attachments):
    return [{'file_id': attachment.file_name, 'tools': [{'type': tool.type} for tool in attachment.tools]} for attachment in attachments]

def check_switch_agent(response: str, switch_flag: str):
    """
    Validates if the response string contains the `switch_flag` and removes the flag from the response.
    
    Parameters:
        response (str): The response from an agent to be validated.
        switch_flag (str): The flag to be searched for in the response.
    
    Returns:
        Bool, str: A bool indicating whether the flag was found and the mutated response if the flag was found. If the flag isn't found returns False along with the
        original response.
    """
    if re.search(switch_flag, response, flags=re.IGNORECASE):
        result = re.sub(switch_flag, '', response, flags=re.IGNORECASE)
        return True, result
    return False, response

def get_switch_agent(agent_session):
    """
    Retrieves current agent_session data and uses the 'agent_id' to locate its agent pointer, which is returned.
    """
    if 'agent_id' in agent_session:
        agent_id = agent_session['agent_id']
        get_agent = get_agent_data(agent_id)
        print(agent_session, get_agent)
        if 'AgentPointer' in get_agent:
            get_agent_pointer = get_agent_data(get_agent['AgentPointer'])
            return get_agent_pointer
        logging.error(f'Could not find `AgentPointer` field in {get_agent}')
        return None
    logging.error(f'Could not find `agent_id` field in {agent_session}')
    return None

 # TODO: Add config option to webapp so admin can change it.
def wrap_message(message: str, agent_id: str, config: str='start'):
    """
    Wraps the user message with the agent's set wrapper prompt.
    Expects a `message` from the user, `agent_id` the user is currently conversing with and `config`, which can either be 'end' or 'start'.
    The config parameter determines whether the user message will be appended at the beginning or end of the wrapper prompt.
    """
    if config != 'start' and config != 'end':
        logging.error(f'`config` parameter must be either "start" or "end"')
        return message
    agent_data = get_agent_data(agentId=agent_id)
    if 'WrapperPrompt' not in agent_data:
        logging.error(f'Could not find `WrapperPrompt` field in {agent_data}')
        return message
    wrapper = agent_data['WrapperPrompt']
    if wrapper is None or wrapper == '' or not wrapper:
        logging.info(f'`WrapperPrompt` field is empty in {agent_data}')
        return message
    if config == 'start':
        return f"""
    user_message: 
    {message}
    -----
    instructions:
    {wrapper}
    """
    if config == 'end':
        return f"""
    instructions:
    {wrapper}
    -----
    user_message:
    {message}
    """