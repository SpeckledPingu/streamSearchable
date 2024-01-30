## Load a file into memory
## Load the vectors into a vector index
## Load the text data into a bm25 index

import json
import gzip
from fastapi import FastAPI
from pydantic import BaseModel
from keyphrase_vectorizers import KeyphraseCountVectorizer
from keybert import KeyBERT
import spacy
from collections import defaultdict
from llama_cpp import Llama, LlamaGrammar
from datetime import datetime
from unidecode import unidecode
from tqdm.auto import tqdm
import re
from newspaper import Article
import time
import requests
import os

from dotenv import load_dotenv
load_dotenv('../.env')

app = FastAPI()

system_prompt = "You are an existentialist philosopher who has been drinking. Be verbose and poetic in your answer."
user_prompt = "What is the meaning of life?"
response = requests.post(
    url=os.getenv('OPENROUTER_URL'),
    headers={
        "Authorization": os.getenv('OPENROUTER_API_KEY'),
        "HTTP-Referer": f"",
        "X-Title": f"",
    },
    data=json.dumps({
        "model": os.getenv('OPENROUTER_MODEL'),
        "temperature":0.2,
        "seed":15,
        "max_tokens":600,
        "messages": [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": user_prompt
            }
        ]
    })
)
print(response.json())
print(response.json()['choices'][0]['message']['content'].strip())

kw_model = KeyBERT()
vectorizer = KeyphraseCountVectorizer()

nlp = spacy.load(os.getenv('SPACY_MODEL'))

class Text(BaseModel):
    text: str

class Prompt(BaseModel):
    system_prompt: str
    content_prompt: str

@app.post("/summarize")
def summarize_text(prompts: Prompt):
    t0 = time.time()
    response = requests.post(
        url=os.getenv('OPENROUTER_URL'),
        headers={
            "Authorization": os.getenv('OPENROUTER_API_KEY'),
            "HTTP-Referer": f"",
            "X-Title": f"",
        },
        data=json.dumps({
            "model": os.getenv('OPENROUTER_MODEL'),
            "temperature":0.2,
            "seed":15,
            "max_tokens":600,
            "messages": [
                {"role": "system", "content": prompts.system_prompt},
                {
                    "role": "user",
                    "content": prompts.content_prompt
                }
            ]
        })
    )
    print(f'time to summarize: {time.time() - t0}')
    summary = response.json()['choices'][0]['message']['content'].strip()
    return {'summary':summary}

@app.post("/phrases")
def summarize_text(text: Text):
    phrases = kw_model.extract_keywords(docs=text.text, vectorizer=vectorizer)
    return {'phrases':[x[0] for x in phrases], 'strengths':[x[1] for x in phrases]}

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
