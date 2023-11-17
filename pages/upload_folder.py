import streamlit as st
import pandas as pd
import json
import requests
from pathlib import Path
from io import StringIO
from shutil import copy

st.set_page_config(layout='wide',
                  page_title='Upload')


data_folder = Path('data/collections')
# notes_folder = Path('data/notes')
config_file = Path('data/config/indexed.json')

current_collections = [x.name for x in data_folder.glob('*') if x.is_dir()]
current_collections = [x for x in current_collections if x[0] != '.']

current_notes = [x.name for x in notes_folder.glob('*') if x.is_dir()]
current_notes = [x for x in current_notes if x[0] != '.']

file_already_indexed = False


collection_name = st.selectbox('Which folder of files to load', options=current_collections)
file_text_field = st.text_input(label='Text field', value='text')

if st.button('Index Folder'):
    payload = {'collection_name':collection_name, 'text_field':file_text_field}
    st.write(payload)
    response = requests.post('http://localhost:8000/batch_index', json=payload)
    st.write(response.json())

st.write('Index notes')
note_index = st.selectbox('Which folder of notes to load', options=current_notes)
if st.button('Index Notes to Collection'):
    notes_index_folder = data_folder.joinpath(note_index)
    notes_index_folder.mkdir(parents=True, exist_ok=True)
    
    # notes_data = notes_folder.joinpath(note_index)
    # print(notes_data)
    # notes_files = [x for x in notes_data.glob('*') if x.is_file()]
    # print(notes_files)
    # print(notes_index_folder)
    # for file in notes_files:
    #     copy(file, notes_index_folder)
    
    payload = {'collection_name':note_index, 'text_field':file_text_field}
    response = requests.post('http://localhost:8000/batch_index', json=payload)
    st.write(response.json())

