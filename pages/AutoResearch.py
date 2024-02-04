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
from services.auto_research import AutoResearch

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
                                  'top_k':50, 'fts_weight':0.5, 'vec_weight':1-0.5})

    result_data, available_fields = results.json()
    available_fields = set(available_fields)
    new_fields = set()
    for result in result_data:
        if 'metadata' in result and len(result['metadata']) > 0:
            metadata = json.loads(result['metadata'])
            result.update(metadata)
            new_fields.update(metadata.keys())
            del result['metadata']

    return result_data

if 'results_to_save' not in st.session_state:
    st.session_state['results_to_save'] = dict()
def add_result_to_save(result):
    note_hash = hash(str(result))
    st.write(st.session_state['results_to_save'].keys())
    if note_hash not in st.session_state['results_to_save']:
        st.session_state['results_to_save'][note_hash] = result
    else:
        del st.session_state['results_to_save'][note_hash]



if query:
    st.markdown(f"## {query}")

    auto_search = AutoResearch(objective=query, collection_name='trump')
    report_results = auto_search.research_question(query)
    # st.write(report_results)

    for task_idx in range(len(report_results)):
        task_description = report_results[str(task_idx + 1)]['task']
        task_result = report_results[str(task_idx + 1)]['results']
        # st.json(task_result)
        st.markdown(f"### Task {task_idx + 1}: {task_description['task']}")
        st.markdown(f"**Research Actions**: {task_description['actions']}")
        st.markdown(f"**Expected Outcomes**: {task_description['expected_outcomes']}")
        st.markdown(f"**Considerations**: {task_description['considerations']}")
        st.write()
        st.markdown(f"### Full Summary:\n{task_result['final_summary']}")
        st.markdown(f"### Summarized Summary:\n{task_result['summarized_summary']}")
        st.divider()
        for query_idx, sub_query in enumerate(task_result['internet_queries']):
            with st.expander(f"Expand for sub query: {sub_query}"):
                st.markdown(f"### Subquery: {sub_query}")
                # st.json(task_result['queries'])
                query_results = task_result['queries'][query_idx]
                st.markdown("#### Summary")
                st.markdown(query_results['sub_summary'])
                st.divider()
                for _article in query_results['article_objects']:
                    st.markdown(f"**Title: {_article['title']}** ---  **UUID: {_article['uuid']}**")
                    st.markdown("**Text**")
                    _text = _article['text'].replace('\n','\n\n')
                    st.markdown(f"{_text}")
                    st.divider()
    #
    # for index, result in enumerate(query_results):
    #     # st.write(result)
    #     st.markdown(f"**:blue[{result['title']}]**")
    #     st.markdown(f"*:blue[Score: {round(result['score'], 3)}]*")
    #     with st.container():
    #         st.write(f"{' '.join(result['text'].split(' ')[:100])}.....")
    #         with st.expander('See Full Text and Details'):
    #             full_text, quick_annotate = st.columns([4,1])
    #             with full_text:
    #                 st.markdown('**Text:**')
    #                 st.markdown(result['text'])
            # save_to_collection = st.toggle('Save to collection',key=f'toggle_{index}',
            #                                on_change=add_result_to_save, args=(result, ))
            st.divider()

