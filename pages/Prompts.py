import streamlit as st
import pandas as pd
import json
import requests
from pathlib import Path
from io import StringIO
from shutil import copy
import yaml
import streamlit_scrollable_textbox as stx

st.set_page_config(layout='wide',
                   page_title='Upload')

config_folder = Path('data/config')
prompt_file = config_folder.joinpath('prompt_templates.json')
prompt_demo_file = config_folder.joinpath('prompt_templates_demo.json')

with open(prompt_file, 'r') as f:
    prompts = json.load(f)

with open(prompt_demo_file, 'r') as f:
    prompt_demo = json.load(f)


walkthrough, example = st.columns(2)
with walkthrough:
    st.markdown('**Use the template to the right to see how a template is formed with this page:** \n\n *These are stored as json, so you can modify them directly if you want in the config/prompt_templates.json file*')
    st.markdown("Some LLMs (like Mistral) work well when there is new line spacing between important parts. To add a newline, as you would when formatting for a person, just add a blank entry.")

    st.markdown("""Required fields are:
    
**- Name** (What is the name so that you can specify which prompt to use when summarizing)
    
**- Goal** (Quick summary of what this prompt does)
    
**- Intended Use** (When to use this)
    
**- Models** are a list of any class of models or specific model name to be used for the prompt. mistral-7b will match any of the models from TheBloke that have that substring. 
Prompts to not work the same across different kinds of models, so if you specify which LLM to use, you can check to see if the prompt has been tested with it.

**- system_prompt** (This is the message that is always sent to the llm to ground it in a specific way, basically how to think about things)
    
**- context_prompt** (This is where you add any special formatting and the actual text in **{{text}}** tags to be replaced.""")
with example:
    st.json(prompt_demo)