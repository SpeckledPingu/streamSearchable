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
    # st.write(results.json()['entities'])
    return results.json()['entities']

@st.cache_data
def store_note(note):
    with open('tmp_json.json','w') as f:
        json.dump(note, f)
    return note


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
selected_collections = st.multiselect('Which note collections to load', options=available_indexes)

index_to_search = st.selectbox(label='Available Indexes', options=available_indexes)
prompt_option_choices = [x['Name'] for x in prompt_options]


for collection_idx, collection_name in enumerate(selected_collections):
    sqlite_conn = sqlite3.connect(sqlite_location)
    notes = sqlite_conn.execute(f"""SELECT * from {collection_name}""").fetchall()
    fields = sqlite_conn.execute(f"PRAGMA table_info({collection_name})").fetchall()
    fields = [x[1] for x in fields]
    notes = [dict(zip(fields, note)) for note in notes]
    for note in notes:
        note['metadata'] = json.loads(note['metadata'])

    with st.expander(collection_name):
        st.markdown("""Batch processing is possible. Select what you want and whether you want to overwrite the files or save to a new collection.\n\n*If you want to overwrite, leave the collection name as is.*""")
        batch_phrase, batch_entity, batch_summary = st.columns([1,1,1])
        with batch_phrase:
            batch_phrase_extract = st.toggle('Batch Phrase Extract', key=f'batch_phrase_extract_{collection_name}')
        with batch_entity:
            batch_entity_extract = st.toggle('Batch Entity Extract', key=f'batch_entity_extract_{collection_name}')
        with batch_summary:
            batch_summary_extract = st.toggle('Batch Summary Extract', key=f'batch_summary_extract_{collection_name}')

        selected_prompt_name = st.selectbox("Which prompt template?", prompt_option_choices, index=0)
        selected_prompt = prompt_options[prompt_option_choices.index(selected_prompt_name)]
        print(selected_prompt)
        save_collection_name = st.text_input('Saved Notes Collection Name', value=collection_name, key=f'batch_collection_save_{collection_name}')

        if st.button('Batch Process!', key=f'batch_process_{collection_name}'):
            progress_text = "Processing Progress (May take some time if summarizing)"
            batch_progress_bar = st.progress(0, text=progress_text)
            for i, note in enumerate(notes, start=1):
                if batch_entity_extract:
                    entities = entities_extract(note['text'])
                    note['entities'] = entities

                if batch_summary_extract:
                    note['summary'] = summarize_text(note['text'], selected_prompt).strip()

                batch_progress_bar.progress(i/len(notes), text=progress_text)
            st.write("Collection Processed!")

        with st.container():
            for index, note in enumerate(notes):
                st.markdown(f"**:blue[{note['title']}]**")
                if st.toggle('Show Note', key=f'show_note_{collection_name}_{index}'):
                    text_col, note_col = st.columns([0.6,0.4])
                    with text_col:
                        st.markdown(f"**Date:** {note['date']}")
                        st.markdown(f"**Title:** {note['title']}")
                        if 'tags' in note and len(note['tags']) > 0:
                            st.markdown(f"**Tags:** {note['tags']}")
                        if 'phrases' in note['metadata']:
                            st.markdown(f"**Keyphrases:** {note['metadata']['phrases']}")
                        if 'entities' in note['metadata']:
                            st.markdown(f"Entities:** {note['metadata']['entities']}")

                        st.markdown("**Text**")
                        st.markdown(note['text'].replace('\n','\n\n'))
                        st.json(note['metadata'], expanded=False)

                    with note_col:
                        ## Create session state for the text
                        ## add button to make rest api call to populate and then update text
                        ## Add button to save the note
                        save_note, local_collection = st.columns([1,3])

                        with save_note:
                            _save_note = st.button('Save', key=f'save_note_{collection_name}_{index}')

                        ### Keyphrase extraction using Keybert/Keyphrase Vectorizers/Spacy NLP
                        if st.toggle('\nPhrase Extract', key=f'phrase_extract_{collection_name}_{index}'):
                            phrases = keyphrase_text(note['text'])
                            if 'phrases' not in note['metadata']:
                                note['metadata']['phrases'] = ','.join(phrases)
                            else:
                                note['metadata']['phrases'] = note['metadata']['phrases'] +'\n' + ','.join(phrases)

                        if 'phrases' in note['metadata']:
                            note['metadata']['phrases']  = st.text_area('Keyphrases', value=note['metadata']['phrases'],
                                                                height=100, key=f'phrase_input_{collection_name}_{index}')
                        else:
                            note['metadata']['phrases']  = st.text_area('Keyphrases', value='',
                                                                height=100, key=f'phrase_input_{collection_name}_{index}')

                        ### Entity extraction using Spacy NLP backend
                        if st.toggle('Entity Extract', key=f'entity_extract_{collection_name}_{index}'):
                            if 'entities' not in note['metadata']:
                                note['metadata']['entities'] = dict()
                            entities = entities_extract(note['text'])
                            note['metadata']['entities'].update(entities)
                        # st.write(note['metadata']['entities'])
                        entities_formatted = ''
                        if 'entities' in note['metadata']:
                            entities_formatted = ''
                            for ent_type, ents in note['metadata']['entities'].items():
                                ents_text = ', '.join(ents)
                                entities_formatted += f'{ent_type}: {ents_text};\n\n'
                            entities_formatted = entities_formatted.strip()
                            entities_formatted = st.text_area('Entities', value=entities_formatted,
                                                                height=200, key=f'entity_input_{collection_name}_{index}')
                        else:
                            entities = st.text_area('Entities', value='',
                                                                height=200, key=f'entity_input_{collection_name}_{index}')
                        note_json = dict()
                        for entity in entities_formatted.split(';'):
                            if len(entity) == 0:
                                continue
                            entity_type, entity_values = entity.split(':')
                            entity_values = [x.strip() for x in entity_values.split(',')]
                            note_json[entity_type.strip()] = entity_values
                        note['metadata']['entities'] = note_json

                        #### Summarization using Llama CPP backend
                        selected_prompt_name = st.selectbox("Which prompt template?", prompt_option_choices, index=0,
                                                            key=f'doc_prompt_template_{collection_name}_{index}')
                        selected_prompt = prompt_options[prompt_option_choices.index(selected_prompt_name)]
                        if st.toggle('Summarize', key=f'summary_extract_{collection_name}_{index}'):
                            if 'summary' not in note['metadata']:
                                note['metadata']['summary'] = ''
                            summary = summarize_text(note['text'], selected_prompt).strip()
                            note['metadata']['summary'] = summary
                        if 'summary' in note['metadata']:
                            note['metadata']['summary'] = st.text_area('Summary', value=note['metadata']['summary'], height=500,
                                                               key=f'summary_input_{collection_name}_{index}')
                        else:
                            note['metadata']['summary'] = st.text_area('Summary', value='', height=500,
                                                               key=f'summary_input_{collection_name}_{index}')

                        if _save_note:
                            note['metadata'] = json.dumps(note['metadata'])
                            lance_table = lance_index.open_table(collection_name)
                            st.write(note['uuid'])
                            # LanceDB current can't (or more likely I don't know) how to update its metadata fields
                            # Sqlite will be used instead as it's the document repository anyways
                            # To create searchable notes, I'll have to think up something with lancedb_notes
                            # lance_table.update(where=f"uuid =' {note['uuid']}'", values={'metadata':note['metadata']})
                            sqlite_conn.execute(f"""UPDATE {collection_name} SET metadata='{note['metadata'].replace("'","''")}' WHERE uuid='{note['uuid']}'""")
                            sqlite_conn.commit()

with st.sidebar:
    new_collection_name = st.text_input(label='New Collection Name', value='')
    if st.button('Create Collection'):
        collections_folder.joinpath(new_collection_name).mkdir(parents=True, exist_ok=True)
        st.rerun()