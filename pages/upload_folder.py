import streamlit as st
import pandas as pd
import json
import requests
from pathlib import Path
from io import StringIO
from shutil import copy
import yaml

st.set_page_config(layout='wide',
                  page_title='Upload')


data_folder = Path('data/collections')
# Future versions will use a yaml configuration to differentiate between data sources and notes
# notes_folder = Path('data/collections')

# notes_folder = Path('data/notes')
config_file = Path('data/config/indexes.yaml')
with open(config_file, 'r') as f:
    config = yaml.unsafe_load(f)

current_collections = [x.name for x in data_folder.glob('*') if x.is_dir()]
current_collections = [x for x in current_collections if x[0] != '.']

# current_notes = [x.name for x in notes_folder.glob('*') if x.is_dir()]
# current_notes = [x for x in current_notes if x[0] != '.']

file_already_indexed = False

st.markdown("**Index and existing folder to a collection:** use if you have an existing folder of files")
collection_name = st.selectbox('Which folder of files to load?', options=current_collections)
file_text_field = st.text_input(label='Text field', value='text')
index_type = st.selectbox('What type of index is this: ', options=['raw','notes'])

if st.button('Index Collection Folder'):
    payload = {'collection_name':collection_name, 'text_field':file_text_field, 'index_type':index_type}
    st.write(payload)
    response = requests.post('http://localhost:8000/batch_index', json=payload)
    st.write(response.json())

st.divider()
st.markdown('**Drag and drop collection of files:** use if you want to create a new folder of files and index')
upload_collection_name = st.text_input("What is the collection's name?")
uploaded_files = st.file_uploader('Drag and Drop Files Here', accept_multiple_files=True)
if st.button('Upload and Index New Collection'):
    collection_folder = data_folder.joinpath(upload_collection_name)
    collection_folder.mkdir(parents=True, exist_ok=True)

    for _file in uploaded_files:
        json_formatted = json.loads(_file.getvalue() )
        with open(collection_folder.joinpath(_file.name),'w') as f:
            json.dump(json_formatted, f)

    payload = {'collection_name':upload_collection_name, 'text_field':file_text_field, 'index_type':index_type}
    st.write(payload)
    response = requests.post('http://localhost:8000/batch_index', json=payload)
    st.write(response.json())

