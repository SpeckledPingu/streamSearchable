import streamlit as st
import pandas as pd
import json
import requests
from datetime import datetime
from pathlib import Path
import lancedb
from services.lancedb_index import IndexDocuments
from services.lancedb_notes import IndexDocumentsNotes
import yaml

### For multipage note taking, save to a json and then load the json in a state
### Delete the file


### Create second page for using notes and searching those
### ### Sends it to a notes embedding api and index
### Create setup page to add templates, research buckets, etc
### ### Store initially as json, then as sqlite
### Create a drag and drop file upload with schema to add data
### ### Low priority
### Create a page where selected results are sent to a model for summaries for review/notes/etc
### ### Tag with the query, datetime, maybe a name from a modal pop out?
### Create a notes template

st.set_page_config(layout='wide',
                  page_title='Search')

notes_folder = Path('data/notes')
collections_folder = Path('data/collections')
tmp_folder = Path('data/tmp')

st.title("Welcome to streamSearchable\n**Your local reSearch engine**")


st.header("Query your data here:")
index_folder = Path('indexes')

index = lancedb.connect(index_folder)
available_indexes = index.table_names()
index_to_search = st.selectbox(label='Available Indexes', options=available_indexes)

query = st.text_input(label="What do you want to search?", value='')
result_cutoff = st.number_input(label='Result cutoff', value=50)
keyword_importance = st.slider(label='Importance of keyword matches',
                               min_value=0.0, max_value=1.0, step=0.05, value=0.5)
st.session_state['query'] = query

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

with st.sidebar:
    current_collections = index.table_names()
    selected_collections = st.selectbox('Existing Collection Destination',
                                      options=current_collections)

    new_index = st.text_input(label='Create new index', value='')

    note_quick_view = [x['title'] for _hash, x in st.session_state['results_to_save'].items()]
    st.markdown("Selected Notes")
    st.json(note_quick_view, expanded=False)
    if st.button('Save selected results'):
        if new_index != '':
            notes_save_name = new_index
        else:
            notes_save_name = selected_collections
        notes_save_name = notes_save_name + '_notes'
        notes_save_path = collections_folder.joinpath(notes_save_name)
        notes_save_path.mkdir(parents=True, exist_ok=True)
        notes_save_file = notes_save_path.joinpath('notes.json')
        save_data = list()
        for session_key, _note in st.session_state['results_to_save'].items():
            save_data.append(_note)
        with open(notes_save_file, 'w') as f:
            json.dump(save_data, f)

        indexer = IndexDocumentsNotes(field_mapping={'text':'text', 'tags':'tags','title':'title','date':'date'},
                                 source_file=notes_save_file,
                                 index_name=notes_save_name,
                                 overwrite=False)
        indexer.open_json()
        indexer.create_documents()
        indexer.ingest()
        st.write('done')

if query:
    query_results, available_fields = remote_search(query, index_to_search)
    show_fields = st.multiselect("Show Fields", available_fields, default=available_fields)
    st.write(len(query_results))
    for index, result in enumerate(query_results):
        st.markdown(f"**:blue[{result['title']}]**")
        st.markdown(f"*:blue[Score: {round(result['score'], 3)}]*")
        with st.container():
            st.write(f"{' '.join(result['text'].split(' ')[:100])}.....")
            with st.expander('See Full Text and Details'):
                full_text, quick_annotate = st.columns([4,1])
                with full_text:
                    if 'date' in result:
                        st.markdown(f"""**Date:** {result['date']}""")
                    if 'tags' in result:
                        st.markdown(f"""**Tags:** {', '.join(result['tags'])}""")
                    st.markdown('**Text:**')
                    st.markdown(result['text'])
                    for _field in show_fields:
                        st.markdown(f"**{_field}:** {result[_field]}")
            save_to_collection = st.toggle('Save to collection',key=f'toggle_{index}',
                                           on_change=add_result_to_save, args=(result, ))
        st.divider()

