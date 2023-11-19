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


data_folder = Path('data/collections')

config_file = Path('data/config/indexes.yaml')
with open(config_file, 'r') as f:
    config = yaml.unsafe_load(f)

current_collections = [x.name for x in data_folder.glob('*') if x.is_dir()]
current_collections = [x for x in current_collections if x[0] != '.']

type_select_col, preview_col = st.columns(2)
with type_select_col:
    type_of_index_op = st.radio("What type of indexing operation do you want to do?",
                                options=["Upload files", "Index existing data folder"])

upload_col, metadata_col = st.columns([0.5,0.5])

with upload_col:
    if type_of_index_op == "Upload files":
        with st.container():
            st.markdown('**Drag and drop collection of files:** \n\n *Use if you want to create a new folder of files and index*')
            collection_name = st.text_input("What is the collection's name?")
            uploaded_files = st.file_uploader('Drag and Drop Files Here', accept_multiple_files=True)

    else:
        with st.container():
            st.markdown("**Index and existing folder to a collection:** \n\n *Use if you have an existing folder of files*")
            collection_name = st.selectbox('Which folder of files to load?', options=current_collections, index=None)

with metadata_col:
    preview_file = {}
    if type_of_index_op == "Upload files":
        if uploaded_files:
            preview_file = uploaded_files[0]
            preview_file = json.loads(preview_file.getvalue() )
            if isinstance(preview_file, list):
                preview_file = preview_file[0]
    else:
        if collection_name:
            collection_path = data_folder.joinpath(collection_name)
            preview_file = [x for x in collection_path.glob('*.json')][0]
            with open(preview_file, 'r') as f:
                preview_file = json.load(f)
            if isinstance(preview_file, list):
                preview_file = preview_file[0]

    for key, text in preview_file.items():
        if isinstance(preview_file[key], str):
            if len(text) > 300:
                preview_file[key] = text[:300] + ' ......'
    st.json(preview_file, expanded=True)


st.divider()
st.markdown("**Schema map for the documents**")
st.caption("If you leave these fields blank, then all text fields will be searched on and there will be no categorization of field types.")
field_maps = {"Tags":list(), "Text":list() ,"Date":list(), "Entities":list()}
file_col, explanation_col = st.columns(2)
with file_col:
    for field_map, fields in field_maps.items():
        fields = st.multiselect(f"Relevant Fields for {field_map}", options=preview_file.keys(), key=f"file_field_{field_map}")

with explanation_col:
    st.markdown("**Explanations of the different field types and uses**")
    st.markdown("**Tags:** Fields that contain values that you would use to categorize the data into different bins.")
    st.markdown("**Text:** Fields that you want to be able to search on.")
    st.markdown("**Date:** Date fields that you want parsed.")
    st.markdown("**Entitites:** Fields that contain entities or concepts that you would like to be able to mine relationships between.")

st.divider()

if st.button("Load And Index Data"):
    if type_of_index_op == "Upload files":
        collection_folder = data_folder.joinpath(collection_name)
        collection_folder.mkdir(parents=True, exist_ok=True)

        for _file in uploaded_files:
            json_formatted = json.loads(_file.getvalue() )
            with open(collection_folder.joinpath(_file.name),'w') as f:
                json.dump(json_formatted, f)
        payload = {'collection_name':collection_name, 'text_field':'text', 'index_type':'REPLACE ME'}
        st.write(payload)
        response = requests.post('http://localhost:8000/batch_index', json=payload)
        st.write(response.json())
    else:
        payload = {'collection_name':collection_name, 'text_field':'text', 'index_type':'REPLACE ME'}
        st.write(payload)
        response = requests.post('http://localhost:8000/batch_index', json=payload)
        st.write(response.json())


