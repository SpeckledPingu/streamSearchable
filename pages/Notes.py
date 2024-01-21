import streamlit as st
import pandas as pd
import json
import requests
from pathlib import Path
from datetime import datetime
from jinja2 import Template

st.set_page_config(layout='wide',
                   page_title='Notes')

@st.cache_data
def summarize_text(text, prompt):
    system_prompt = '\n'.join(prompt['system_prompt'])
    content_prompt = Template('\n'.join(prompt['content_prompt']))
    content_prompt = content_prompt.render({'text':text})
    results = requests.post('http://localhost:8001/summarize',
                            json={'system_prompt':system_prompt, 'content_prompt':content_prompt})
    return results.json()['summary']

# @st.cache_data
def keyphrase_text(text, strength_cutoff=0.3):
    results = requests.post('http://localhost:8001/phrases',
                            json={'text':text})
    results = results.json()
    phrases = list()
    for phrase, strength in zip(results['phrases'], results['strengths']):
        if strength >= strength_cutoff:
            phrases.append(phrase)
    return phrases

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
config_folder = Path('data/config')
with open(config_folder.joinpath('prompt_templates.json'), 'r') as f:
    prompt_options = json.load(f)

prompt_option_choices = [x['Name'] for x in prompt_options]

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

        selected_prompt_name = st.selectbox("Which prompt template?", prompt_option_choices, index=0)
        selected_prompt = prompt_options[prompt_option_choices.index(selected_prompt_name)]
        print(selected_prompt)
        save_collection_name = st.text_input('Saved Notes Collection Name', value=collection, key=f'batch_collection_save_{collection_index}')

        if st.button('Batch Process!', key=f'batch_process_{collection_index}'):
            batch_collection = collections_folder.joinpath(save_collection_name)
            batch_collection.mkdir(parents=True, exist_ok=True)

            progress_text = "Processing Progress (May take some time if summarizing)"
            batch_progress_bar = st.progress(0, text=progress_text)
            for i, file in enumerate(_current_notes, start=1):
                with open(file,'r') as f:
                    tmp_note = json.load(f)
                if 'vector' in tmp_note:
                    del tmp_note['vector']

                if batch_phrase_extract:
                    tmp_note['phrases'] = keyphrase_text(tmp_note['text'])

                if batch_entity_extract:
                    entities = entities_extract(tmp_note['text'])
                    # entities_formatted = ''
                    # for type, ents in entities.items():
                    #     ents_text = ', '.join(ents)
                    #     entities_formatted += f'{type}: {ents_text}\n'
                    tmp_note['entities'] = entities

                if batch_summary_extract:
                    tmp_note['summary'] = summarize_text(tmp_note['text'], selected_prompt).strip()

                # save_path = batch_collection.joinpath(f'{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.json')
                with open(file, 'w') as f:
                    json.dump(tmp_note, f)
                batch_progress_bar.progress(i/len(_current_notes), text=progress_text)

            st.write("Collection Processed!")

            st.write(collection)

        with st.container():
            for index, file in enumerate(_current_notes):
                with open(file,'r') as f:
                    tmp_note = json.load(f)
                _title = tmp_note['title']

                st.markdown(f"**:blue[{_title}]**")
                if st.toggle('Show Note', key=f'show_note_{collection_index}_{index}'):
                    text_col, note_col = st.columns([0.6,0.4])
                    with text_col:
                        for key, value in tmp_note.items():
                            if key == 'vector':
                                continue
                            if key == 'text':
                                st.caption(key)
                                st.markdown('\n\n'.join(value.split('\n')))
                                continue
                            if key == 'phrases':
                                if isinstance(value, list):
                                    st.caption(key)
                                    st.markdown(', '.join(value))
                                    continue
                            if key == 'entities':
                                if isinstance(value, dict):
                                    st.caption(key)
                                    entities_formatted = ''
                                    for type, ents in value.items():
                                        ents_text = ', '.join(ents)
                                        entities_formatted += f'**{type}**: {ents_text};\n\n'
                                    st.write(entities_formatted)
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

                        ### Keyphrase extraction using Keybert/Keyphrase Vectorizers/Spacy NLP
                        if st.toggle('\nPhrase Extract', key=f'phrase_extract_{collection_index}_{index}'):
                            tmp_note['phrases'] = ''
                            phrases = keyphrase_text(tmp_note['text'])
                            tmp_note['phrases'] = phrases

                        if 'phrases' in tmp_note:
                            if isinstance(tmp_note['phrases'], list):
                                phrase_text_notes = ', '.join(tmp_note['phrases'])
                            tmp_note['phrases']  = st.text_area('Keyphrases', value=phrase_text_notes,
                                                                height=100, key=f'phrase_input_{collection_index}_{index}')
                        else:
                            tmp_note['phrases']  = st.text_area('Keyphrases', value='',
                                                                height=100, key=f'phrase_input_{collection_index}_{index}')

                        ### Entity extraction using Spacy NLP backend
                        if st.toggle('Entity Extract', key=f'entity_extract_{collection_index}_{index}'):
                            tmp_note['entities'] = ''
                            entities = entities_extract(tmp_note['text'])
                            entities_formatted = ''
                            for type, ents in entities.items():
                                ents_text = ', '.join(ents)
                                entities_formatted += f'{type}: {ents_text};\n\n'
                            tmp_note['entities'] = entities_formatted.strip()

                        if 'entities' in tmp_note:
                            if isinstance(tmp_note['entities'], dict):
                                entities_formatted = ''
                                for type, ents in tmp_note['entities'].items():
                                    ents_text = ', '.join(ents)
                                    entities_formatted += f'{type}: {ents_text};\n\n'
                            entities_formatted = entities_formatted.strip()
                            tmp_note['entities'] = st.text_area('Entities', value=entities_formatted,
                                                                height=200, key=f'entity_input_{collection_index}_{index}')
                        else:
                            tmp_note['entities'] = st.text_area('Entities', value='',
                                                                height=200, key=f'entity_input_{collection_index}_{index}')

                        #### Summarization using Llama CPP backend
                        selected_prompt_name = st.selectbox("Which prompt template?", prompt_option_choices, index=0,
                                                            key=f'doc_prompt_template_{collection_index}_{index}')
                        selected_prompt = prompt_options[prompt_option_choices.index(selected_prompt_name)]
                        if st.toggle('Summarize', key=f'summary_extract_{collection_index}_{index}'):

                            tmp_note['summary'] = ''
                            summary = summarize_text(tmp_note['text'], selected_prompt).strip()
                            tmp_note['summary'] = summary
                        if 'summary' in tmp_note:
                            tmp_note['summary'] = st.text_area('Summary', value=tmp_note['summary'], height=500,
                                                               key=f'summary_input_{collection_index}_{index}')
                        else:
                            tmp_note['summary'] = st.text_area('Summary', value='', height=500,
                                                               key=f'summary_input_{collection_index}_{index}')

                        if _save_note:
                            _entities = [x.strip().split(':') for x in tmp_note['entities'].split(';')]
                            _entities = {key.strip():[x.strip() for x in value.split(',')] for key, value in _entities}
                            tmp_note['entities'] = _entities

                            _keyphrases = [x.strip() for x in tmp_note['keyphrases'].split(',')]
                            tmp_note['keyphrases'] = _keyphrases
                            for collection in save_collections:
                                st.write(collection)
                                # save_path = notes_folder.joinpath(collection)
                                # save_path = save_path.joinpath(f'{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.json')
                                with open(file, 'w') as f:
                                    json.dump(tmp_note, f)

with st.sidebar:
    new_collection_name = st.text_input(label='New Collection Name', value='')
    if st.button('Create Collection'):
        collections_folder.joinpath(new_collection_name).mkdir(parents=True, exist_ok=True)
        st.rerun()