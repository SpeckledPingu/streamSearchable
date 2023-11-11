import streamlit as st
import pandas as pd
import json
import requests
from pathlib import Path
from datetime import datetime

st.set_page_config(layout='wide',
                  page_title='Notes')


@st.cache_data
def summarize_text(text):
    results = requests.post('http://localhost:8001/summarize',
                           json={'text':text})
    return results.json()['summary']

# @st.cache_data
def keyphrase_text(text):
    results = requests.post('http://localhost:8001/phrases',
                           json={'text':text})
    return results.json()['phrases']

@st.cache_data
def entities_extract(text):
    results = requests.post('http://localhost:8001/ner',
                           json={'text':text})
    print(results.content)
    return results.json()['entities']

@st.cache_data
def store_note(note):
    with open('tmp_json.json','w') as f:
        json.dump(note, f)
    return note


buckets_folder = Path('data/buckets')
notes_folder = Path('data/notes')

# if st.button('Reload'):
#     st.rerun()

current_buckets = [x.name for x in buckets_folder.glob('*') if x.is_dir()]
current_buckets = [x for x in current_buckets if x[0] != '.']

# current_notes = [x for x in notes_folder.glob('*.json')]

selected_buckets = list()

selected_buckets = st.multiselect('Which note buckets to load', options=current_buckets, default='to_process')
for bucket_index, bucket in enumerate(selected_buckets):
    _path = buckets_folder.joinpath(bucket)
    _current_notes = [x for x in _path.glob('*.json')]
    with st.expander(_path.name):
        st.markdown("""Batch processing is possible. Select what you want and whether you want to overwrite the files or save to a new collection.\n\n*If you want to overwrite, leave the collection name as is.*""")
        batch_phrase, batch_entity, batch_summary = st.columns([1,1,1])
        with batch_phrase:
            batch_phrase_extract = st.toggle('Batch Phrase Extract', key=f'batch_phrase_extract_{bucket_index}')
        with batch_entity:
            batch_entity_extract = st.toggle('Batch Entity Extract', key=f'batch_entity_extract_{bucket_index}')
        with batch_summary:
            batch_summary_extract = st.toggle('Batch Summary Extract', key=f'batch_summary_extract_{bucket_index}')

        batch_collection, batch_save = st.columns([4,1])
        with batch_collection:
            batch_collection_name = st.text_input('Collection Name', value=bucket, key=f'batch_collection_save_{bucket_index}')
        with batch_save:
            if st.button('Batch Process!', key=f'batch_process_{bucket_index}'):
                batch_bucket = buckets_folder.joinpath(batch_collection_name)
                batch_bucket.mkdir(parents=True, exist_ok=True)
                for file in _current_notes:
                    with open(file,'r') as f:
                        tmp_note = json.load(f)
                    if 'vector' in tmp_note:
                        del tmp_note['vector']

                    if batch_phrase_extract:
                        tmp_note['phrases'] = keyphrase_text(tmp_note['text'])

                    if batch_entity_extract:
                        entities = entities_extract(tmp_note['text'])
                        entities_formatted = ''
                        for type, ents in entities.items():
                            ents_text = ', '.join(ents)
                            entities_formatted += f'{type}: {ents_text}\n'
                        tmp_note['entities'] = entities_formatted

                    if batch_summary_extract:
                        tmp_note['summary'] = summarize_text(tmp_note['text']).strip()

                    save_path = batch_bucket.joinpath(f'{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.json')
                    with open(save_path, 'w') as f:
                        json.dump(tmp_note, f)
                
                st.write(bucket)
                save_path = batch_bucket.joinpath(f'{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.json')
                with open(save_path, 'w') as f:
                    json.dump(tmp_note, f)
        
        with st.container():
            for index, file in enumerate(_current_notes):
                with open(file,'r') as f:
                    tmp_note = json.load(f)
                _title = tmp_note['title']
                if 'vector' in tmp_note:
                    del tmp_note['vector']
                st.markdown(f"**:blue[{_title}]**")
                if st.toggle('Show Note', key=f'show_note_{bucket_index}_{index}'):
                    text_col, note_col = st.columns([2,1])
                    with text_col:
                        for key, value in tmp_note.items():
                            st.caption(key)
                            st.write(value)
                    with note_col:
                        ## Create session state for the text
                        ## add button to make rest api call to populate and then update text
                        ## Add button to save the note
                        save_note, local_bucket = st.columns([1,3])
                        with save_note:
                            _save_note = st.button('Save', key=f'save_note_{bucket_index}_{index}')
                        with local_bucket:
                            save_buckets = st.multiselect('Which buckets to save to', 
                                                          options=current_buckets, default='to_process', 
                                                          key=f'save_buckets_{bucket_index}_{index}')

                        if st.toggle('\nPhrase Extract', key=f'phrase_extract_{bucket_index}_{index}'):
                                tmp_note['phrases'] = ''
                                phrases = keyphrase_text(tmp_note['text'])
                                phrases = [x[0] for x in phrases]
                                phrases = ','.join(phrases)
                                tmp_note['phrases'] = phrases
                        if 'phrases' in tmp_note:
                            phrase_input = st.text_area('Keyphrases', value=tmp_note['phrases'], 
                                                        key=f'phrase_input_{bucket_index}_{index}')
                        else:
                            phrase_input = st.text_area('Keyphrases', value='', 
                                                        key=f'phrase_input_{bucket_index}_{index}')

                        if st.toggle('Entity Extract', 
                                     key=f'entity_extract_{bucket_index}_{index}'):
                                tmp_note['entities'] = ''
                                entities = entities_extract(tmp_note['text'])
                                entities_formatted = ''
                                for type, ents in entities.items():
                                    ents_text = ', '.join(ents)
                                    entities_formatted += f'{type}: {ents_text}\n'
                                tmp_note['entities'] = entities_formatted
                        if 'entities' in tmp_note:
                            entities_input = st.text_area('Entities', value=tmp_note['entities'], 
                                                          key=f'entity_input_{bucket_index}_{index}')
                        else:
                            entities_input = st.text_area('Entities', value='', 
                                                          key=f'entity_input_{bucket_index}_{index}')

                        if st.toggle('Summarize', 
                                     key=f'summary_extract_{bucket_index}_{index}'):
                                tmp_note['summary'] = ''
                                summary = summarize_text(tmp_note['text']).strip()
                                tmp_note['summary'] = summary
                        if 'summary' in tmp_note:
                            summary_input = st.text_area('Summary', value=tmp_note['summary'], height=500, 
                                                         key=f'summary_input_{bucket_index}_{index}')
                        else:
                            summary_input = st.text_area('Summary', value='', height=500, 
                                                         key=f'summary_input_{bucket_index}_{index}')
                        
                        
                        if _save_note:
                            for bucket in save_buckets:
                                st.write(bucket)
                                save_path = buckets_folder.joinpath(bucket)
                                save_path = save_path.joinpath(f'{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.json')
                                with open(save_path, 'w') as f:
                                    json.dump(tmp_note, f)
    # selected_buckets = st.multiselect('Which note buckets to load', options=current_buckets)

# with create:
#     st.write('Create new bucket')
#     new_bucket_name = st.text_input(label='New Bucket Name', value='')
#     if st.button('Create Bucket'):
#         buckets_folder.joinpath(new_bucket_name).mkdir(parents=True, exist_ok=True)

with st.sidebar:
    new_bucket_name = st.text_input(label='New Bucket Name', value='')
    if st.button('Create Bucket'):
        buckets_folder.joinpath(new_bucket_name).mkdir(parents=True, exist_ok=True)
        st.rerun()