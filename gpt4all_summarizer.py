## Load a file into memory
## Load the vectors into a vector index
## Load the text data into a bm25 index

import json
import gzip
from gpt4all import GPT4All
from fastapi import FastAPI
from pydantic import BaseModel
from keyphrase_vectorizers import KeyphraseCountVectorizer
from keybert import KeyBERT
import spacy
from collections import defaultdict

app = FastAPI()
model = GPT4All("orca-mini-3b-gguf2-q4_0.gguf", device='gpu')


kw_model = KeyBERT()
vectorizer = KeyphraseCountVectorizer()

nlp = spacy.load("en_core_web_sm")

class Text(BaseModel):
    text: str

# @app.get("/vec_query")
# def vec_query(query, limit=20):
#     results = embedding_index.search(query, limit=limit)
#     result_data = [data[index[0]] for index in results]
#     return result_data


@app.post("/summarize")
def summarize_text(text: Text):
    query_template = f"""### System: You are a very helpful policy analyst and AI assistant.
    ### Human: Summarize this text: {text}
    ### Response: """
    _query = ' '.join(query_template.split(' ')[:1300])
    summary = model.generate(_query, max_tokens=500)
    return {'summary':summary}

@app.post("/phrases")
def summarize_text(text: Text):
    phrases = kw_model.extract_keywords(docs=text.text, vectorizer=vectorizer)
    return {'phrases':','.join([x[0] for x in phrases])}

@app.post("/ner")
def ner_extract(text: Text):
    doc = nlp(text.text)
    # nlp.add_pipe("merge_entities")
    # nlp.add_pipe("merge_noun_chunks")
    entities = defaultdict(list)
    for token in doc.ents:
        _token_tag = token.label_
        entities[_token_tag].append(token.text)
    for _label, _ent in entities.items():
        entities[_label] = list(set(entities[_label]))
    return {'entities':entities}
