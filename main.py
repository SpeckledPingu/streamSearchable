import streamlit as st
import pandas as pd
import json
import requests
from datetime import datetime
from pathlib import Path
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
index_folder = Path('data/indexes')
index_name = 'index.tar.gz'
available_indexes = list()
for _collection in index_folder.glob('*'):
    if _collection.is_dir():
        if _collection.joinpath(index_name).exists():
            available_indexes.append(_collection.name)

index_to_search = st.selectbox(label='Available Indexes', options=available_indexes)
# config_file = Path('data/config/indexes.yaml')
# with open(config_file, 'r') as f:
#     config = yaml.unsafe_load(f)
#
# available_fields = config[index_to_search]



query = st.text_input(label="What do you want to search?", value='')
result_cutoff = st.number_input(label='Result cutoff', value=50)
keyword_importance = st.slider(label='Importance of keyword matches',
                               min_value=0.0, max_value=1.0, step=0.05, value=0.5)
st.session_state['query'] = query

@st.cache_data
def remote_search(query, collection_name):
    results = requests.post('http://localhost:8000/query',
                           json={'query':query, 'collection_name':collection_name})
    scored_results = list()
    # print(results.json())
    available_fields = set()
    for row in results.json():
        _data = json.loads(row['data'])
        _data['score'] = row['score']
        scored_results.append(_data)
        available_fields.update(list(_data.keys()))
    return scored_results, sorted(list(available_fields))

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
    current_collections = [x for x in collections_folder.glob('*') if x.is_dir()]
    current_collections = [x for x in current_collections if x.name[0] != '.']
    selected_collections = st.multiselect('Collection Destination',
                                      options=[x.name for x in current_collections])
    st.write('Create new collection')
    new_bucket_name = st.text_input(label='New Collection Name', value='')
    if st.button('Create Collection'):
        collections_folder.joinpath(new_bucket_name).mkdir(parents=True, exist_ok=True)
    #     st.rerun()

    # st.write(st.session_state['results_to_save'])
    note_quick_view = [x['title'] for _hash, x in st.session_state['results_to_save'].items()]
    st.markdown("Selected Notes")
    st.json(note_quick_view, expanded=False)
    if st.button('Save selected results'):
        # st.write(st.session_state['results_to_save'])
        for _collection in selected_collections:
            for _hash, _result in st.session_state['results_to_save'].items():
                _path = collections_folder.joinpath(_collection)
                with open(_path.joinpath(f'{query}_{_result["title"]}.json'),'w') as f:
                    json.dump(_result, f)


if query:
    query_results, available_fields = remote_search(query, index_to_search)
    show_fields = st.multiselect("Show Fields", available_fields, default=available_fields)
    st.write(len(query_results))
    for index, result in enumerate(query_results):
        st.markdown(f"**:blue[{result['title']}]**")
        st.markdown(f"*:blue[Score: {round(result['score'], 3)}]*")
        with st.container():
            # st.write(f"{' '.join(result['text'].split(' ')[:50])}...")
            st.write(f"{' '.join(result['text'].split(' ')[:100])}.....")
            save_to_collection = st.toggle('Save to collection',key=f'toggle_{index}',
                                             on_change=add_result_to_save, args=(result, ))
            # if save_to_collection:
            #     st.write(st.session_state['results_to_save'])

            #     for _collection in selected_collections:
            #         _path = collections_folder.joinpath(_collection)
            #         with open(_path.joinpath(f'{query}_{result["title"]}.json'),'w') as f:
            #             json.dump(result, f)
            with st.expander('See Full Text and Details'):
                full_text, quick_annotate = st.columns([4,1])
                with full_text:
                    for _field in show_fields:
                        st.markdown(f"**{_field}:** {result[_field]}")
                    # st.write(result)
                    # st.divider()
                    # if isinstance(result['text'], list):
                    #     st.markdown('\n\n'.join(result['text']))
                    # st.markdown(result['text'])

                # with quick_annotate:
                #     quick_note = st.text_area('Quick Annotation', key=f'text_{index}')
                #     if st.button('Save', key=f'fast_annotate_{index}'):
                #         fast_note = result.copy()
                #         fast_note['quick_note'] = quick_note
                #         for _bucket in selected_collections:
                #             _path = collections_folder.joinpath(_bucket)
                #             with open(_path.joinpath(f'{query}_{result["title"]}.json'),'w') as f:
                #                 json.dump(fast_note, f)
                                
        st.divider()

