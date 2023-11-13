import streamlit as st
import pandas as pd
import json
import requests
from datetime import datetime
from pathlib import Path

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
data_folder = Path('data/source')
buckets_folder = Path('data/buckets')
tmp_folder = Path('data/tmp')


with open('all_biden_press_statements_sec_of_state_v2.json','r') as f:
    data = json.load(f)

df = pd.read_json('all_biden_press_statements_sec_of_state_v2.json')
df = df.drop('tags', axis=1)
df = df.explode('text')
# df = df.dropna(subset=['text'])
df['text'] = df['text'].fillna('')
df = df.reset_index(drop=True)
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

query = st.text_input(label="What do you want to search?", value='')

st.session_state['query'] = query

if 'note' not in st.session_state:
    st.session_state['note'] = dict()
if 'current_note' not in st.session_state:
    st.session_state['current_note'] = dict()

if 'summary' not in st.session_state:
    st.session_state['summary'] = ''
if 'phrases' not in st.session_state:
    st.session_state['phrases'] = ''
if 'entities' not in st.session_state:
    st.session_state['entities'] = ''
if 'entities_formatted' not in st.session_state:
    st.session_state['entities_formatted'] = ''

@st.cache_data
def search_df(query):
    query_results = df[df['text'].str.contains(query, case=False)]
    return query_results

@st.cache_data
def remote_search(query, collection_name):
    results = requests.post('http://localhost:8000/query',
                           json={'query':query, 'collection_name':collection_name})
    cleaned_results = list()
    for row in results.json():
        org_data = json.loads(row['data'])
        org_data['score'] = row['score']
        cleaned_results.append(org_data)
    return cleaned_results

with st.sidebar:
    current_buckets = [x for x in buckets_folder.glob('*') if x.is_dir()]
    current_buckets = [x for x in current_buckets if x.name[0] != '.']
    selected_buckets = st.multiselect('Bucket Destination', 
                                      options=[x.name for x in current_buckets], default='to_process')
    st.write('Create new bucket')
    new_bucket_name = st.text_input(label='New Bucket Name', value='')
    if st.button('Create Bucket'):
        buckets_folder.joinpath(new_bucket_name).mkdir(parents=True, exist_ok=True)
        st.rerun()
        
# st.dataframe(df.sample(20))
# tab1, tab2 = st.tabs(["Search Results","Notes"])

if query:
    # query_results = search_df(query)
    query_results = remote_search(query, index_to_search)
    # for index, result in query_results.head().iterrows():
    for index, result in enumerate(query_results):
        # st.write(result)
        st.markdown(f"**:blue[{result['title']}]**")
        st.markdown(f"*:blue[Score: {round(result['score'], 3)}]*")
        with st.container():
            st.write(f"{' '.join(result['text'].split(' ')[:50])}...")
            save_to_bucket = st.toggle('Save to bucket',key=f'toggle_{index}')
            if save_to_bucket:
                for _bucket in selected_buckets:
                    _path = buckets_folder.joinpath(_bucket)
                    with open(_path.joinpath(f'{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.json'),'w') as f:
                        json.dump(result, f)
            with st.expander('See Full Text and Details'):
                full_text, quick_annotate = st.columns([4,1])
                with full_text:
                    st.markdown(f"**Type:** {result['document_type']}")
                    st.markdown(f"**Author:** {result['document_author']}")
                    st.markdown(f"**Date:** {result['publish_date']}")
                    st.markdown(f"**Tags:** {result['tags']}")
                    st.divider()
                    st.markdown('\n\n'.join(result['text'].split('\n')))
                with quick_annotate:
                    quick_note = st.text_area('Quick Annotation', key=f'text_{index}')
                    if st.button('Save', key=f'fast_annotate_{index}'):
                        fast_note = result.copy()
                        fast_note['quick_note'] = quick_note
                        for _bucket in selected_buckets:
                            _path = buckets_folder.joinpath(_bucket)
                            with open(_path.joinpath(f'{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.json'),'w') as f:
                                json.dump(fast_note, f)
                                
        st.divider()

## Write a basic in memory search of the documents
## Cache the query
## Cache the result set
def run_query():
    pass

## Paginate the results
def display_results():
    pass


### Add expander for the full text and the notes


### Add a page for more comprehensive note taking
### Save the document that was clicked to json to prevent rerunning



