import streamlit as st
import pandas as pd
import json
import requests
from pathlib import Path
from datetime import datetime
from jinja2 import Template
import lancedb
import sqlite3
from services.lancedb_notes import IndexDocumentsNotes

st.set_page_config(layout='wide',
                   page_title='AutoResearch')

notes_folder = Path('data/notes')
collections_folder = Path('data/collections')
tmp_folder = Path('data/tmp')
config_folder = Path('data/config')
with open(config_folder.joinpath('prompt_templates.json'), 'r') as f:
    prompt_options = json.load(f)


index_folder = Path('indexes')
sqlite_location = Path('data/indexes/documents.sqlite')

lance_index = lancedb.connect(index_folder)
available_indexes = lance_index.table_names()
index_to_search = st.selectbox(label='Available Indexes', options=available_indexes)

query = st.text_input(label="What do you want to search?", value='')


@st.cache_data
def remote_search(query, collection_name):
    results = requests.post('http://localhost:8000/hybrid',
                            json={'query':query, 'collection_name':collection_name,
                                  'top_k':50, 'fts_weight':keyword_importance, 'vec_weight':1-keyword_importance})

    result_data, available_fields = results.json()
    available_fields = set(available_fields)
    new_fields = set()
    for result in result_data:
        if 'metadata' in result and len(result['metadata']) > 0:
            metadata = json.loads(result['metadata'])
            result.update(metadata)
            new_fields.update(metadata.keys())
            del result['metadata']

    return result_data, sorted(list(new_fields))

if 'results_to_save' not in st.session_state:
    st.session_state['results_to_save'] = dict()
def add_result_to_save(result):
    note_hash = hash(str(result))
    st.write(st.session_state['results_to_save'].keys())
    if note_hash not in st.session_state['results_to_save']:
        st.session_state['results_to_save'][note_hash] = result
    else:
        del st.session_state['results_to_save'][note_hash]


