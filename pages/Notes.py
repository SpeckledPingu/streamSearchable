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


collections_folder = Path('data/collections')
notes_folder = Path('data/notes')

# if st.button('Reload'):
#     st.rerun()

current_collections = [x.name for x in collections_folder.glob('*') if x.is_dir()]
current_collections = [x for x in current_collections if x[0] != '.']

current_notes = [x for x in notes_folder.glob('*.json')]

selected_collections = list()

selected_collections = st.multiselect('Which note collections to load', options=current_collections)
for collection_index, collection in enumerate(selected_collections):
    _path = collections_folder.joinpath(collection)
    _current_notes = [x for x in _path.glob('*.json')]
    with st.expander(_path.name):
        st.markdown("""Batch processing is possible. Select what you want and whether you want to overwrite the files or save to a new collection.\n\n*If you want to overwrite, leave the collection name as is.*""")
        batch_phrase, batch_entity, batch_summary = st.columns([1,1,1])
        with batch_phrase:
            batch_phrase_extract = st.toggle('Batch Phrase Extract', key=f'batch_phrase_extract_{collection_index}')
        with batch_entity:
            batch_entity_extract = st.toggle('Batch Entity Extract', key=f'batch_entity_extract_{collection_index}')
        with batch_summary:
            batch_summary_extract = st.toggle('Batch Summary Extract', key=f'batch_summary_extract_{collection_index}')

        batch_collection, batch_save = st.columns([0.7,0.3])
        with batch_collection:
            save_collection_name = st.text_input('Saved Notes Collection Name', value=collection, key=f'batch_collection_save_{collection_index}')

        with batch_save:
            if st.button('Batch Process!', key=f'batch_process_{collection_index}'):
                batch_collection = collections_folder.joinpath(save_collection_name)
                batch_collection.mkdir(parents=True, exist_ok=True)
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

                    save_path = batch_collection.joinpath(f'{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.json')
                    with open(save_path, 'w') as f:
                        json.dump(tmp_note, f)
                
                st.write(collection)
                save_path = batch_collection.joinpath(f'{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.json')
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
                if st.toggle('Show Note', key=f'show_note_{collection_index}_{index}'):
                    text_col, note_col = st.columns([0.7,0.3])
                    with text_col:
                        for key, value in tmp_note.items():
                            if key == 'text':
                                st.caption(key)
                                st.markdown('\n\n'.join(value.split('\n')))
                                continue
                            st.caption(key)
                            st.write(value)
                    with note_col:
                        ## Create session state for the text
                        ## add button to make rest api call to populate and then update text
                        ## Add button to save the note
                        save_note, local_collection = st.columns([1,3])
                        with save_note:
                            _save_note = st.button('Save', key=f'save_note_{collection_index}_{index}')
                        with local_collection:
                            save_collections = st.multiselect('Which collections to save to', 
                                                          options=current_collections,
                                                          key=f'save_collections_{collection_index}_{index}')

                        if st.toggle('\nPhrase Extract', key=f'phrase_extract_{collection_index}_{index}'):
                                tmp_note['phrases'] = ''
                                phrases = keyphrase_text(tmp_note['text'])
                                # phrases = [x[0] for x in phrases]
                                # phrases = ','.join(phrases)
                                tmp_note['phrases'] = phrases
                        if 'phrases' in tmp_note:
                            phrase_input = st.text_area('Keyphrases', value=tmp_note['phrases'],
                                                        height=300, key=f'phrase_input_{collection_index}_{index}')
                        else:
                            phrase_input = st.text_area('Keyphrases', value='',
                                                        height=300, key=f'phrase_input_{collection_index}_{index}')

                        if st.toggle('Entity Extract', 
                                     key=f'entity_extract_{collection_index}_{index}'):
                                tmp_note['entities'] = ''
                                entities = entities_extract(tmp_note['text'])
                                entities_formatted = ''
                                for type, ents in entities.items():
                                    ents_text = ', '.join(ents)
                                    entities_formatted += f'{type}: {ents_text}\n'
                                tmp_note['entities'] = entities_formatted
                        if 'entities' in tmp_note:
                            entities_input = st.text_area('Entities', value=tmp_note['entities'],
                                                          height=300, key=f'entity_input_{collection_index}_{index}')
                        else:
                            entities_input = st.text_area('Entities', value='',
                                                          height=300, key=f'entity_input_{collection_index}_{index}')

                        if st.toggle('Summarize', 
                                     key=f'summary_extract_{collection_index}_{index}'):
                                tmp_note['summary'] = ''
                                summary = summarize_text(tmp_note['text']).strip()
                                tmp_note['summary'] = summary
                        if 'summary' in tmp_note:
                            summary_input = st.text_area('Summary', value=tmp_note['summary'], height=500, 
                                                         key=f'summary_input_{collection_index}_{index}')
                        else:
                            summary_input = st.text_area('Summary', value='', height=500, 
                                                         key=f'summary_input_{collection_index}_{index}')
                        
                        
                        if _save_note:
                            for collection in save_collections:
                                st.write(collection)
                                # save_path = collections_folder.joinpath(collection)
                                save_path = notes_folder.joinpath(collection)
                                save_path = save_path.joinpath(f'{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.json')
                                with open(save_path, 'w') as f:
                                    json.dump(tmp_note, f)
    # selected_collections = st.multiselect('Which note collections to load', options=current_collections)

# with create:
#     st.write('Create new collection')
#     new_collection_name = st.text_input(label='New collection Name', value='')
#     if st.button('Create collection'):
#         collections_folder.joinpath(new_collection_name).mkdir(parents=True, exist_ok=True)

with st.sidebar:
    new_collection_name = st.text_input(label='New Collection Name', value='')
    if st.button('Create Collection'):
        collections_folder.joinpath(new_collection_name).mkdir(parents=True, exist_ok=True)
        st.rerun()