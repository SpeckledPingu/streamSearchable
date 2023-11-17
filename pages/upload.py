import streamlit as st
import pandas as pd
import json
import requests
from pathlib import Path
from io import StringIO

st.set_page_config(layout='wide',
                  page_title='Upload')


data_folder = Path('data/collections')
config_file = Path('data/config/indexed.json')
current_buckets = [x.name for x in data_folder.glob('*') if x.is_dir()]
current_buckets = [x for x in current_buckets if x[0] != '.']
file_already_indexed = False

new_bucket_name = st.text_input(label='New Collection Name', value='')
if st.button('Create Collection'):
    data_folder.joinpath(new_bucket_name).mkdir(parents=True, exist_ok=True)
    st.rerun()

collection_name = st.selectbox('Which note buckets to load', options=current_buckets)
file_name = st.text_input(label='File Name', value='')


uploaded_file = st.file_uploader('Drag and Drop Files Here')

if uploaded_file:
    bytes_data = uploaded_file.read()
    if file_name == '':
        file_name = uploaded_file.name
    st.write(file_name)

if st.button('Save File'):
    collection_folder = data_folder.joinpath(collection_name)
    collection_folder.mkdir(parents=True, exist_ok=True)
    json_formatted = json.loads(uploaded_file.getvalue() )
    with open(collection_folder.joinpath(file_name),'w') as f:
        json.dump(json_formatted, f)

file_to_index = st.text_input(label='File Name', value=file_name, key='file_to_index')
file_text_field = st.text_input(label='Text field', value='text')
if st.button('Index File'):
    payload = {'file_name':file_to_index, 'collection_name':collection_name, 'text_field':file_text_field}
    st.write(payload)
    response = requests.post('http://localhost:8000/index', json=payload)
    st.write(response.content)