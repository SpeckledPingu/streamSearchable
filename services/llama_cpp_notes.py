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

from dotenv import load_dotenv


app = FastAPI()
model = Llama(model_path="../llama_cpp/mistral-7b-instruct-v0.2.Q3_K_M.gguf",
              n_threads=6, n_gpu_layers=33, n_ctx=32768, offload_kqv=False,
              chat_format="llama-2",
              use_mlock=True,
              use_mmap=True,
              n_batch=128,
              seed=1)


kw_model = KeyBERT()
vectorizer = KeyphraseCountVectorizer()

nlp = spacy.load("en_core_web_lg")

class Text(BaseModel):
    text: str

class Prompt(BaseModel):
    system_prompt: str
    content_prompt: str

@app.post("/summarize")
def summarize_text(prompts: Prompt):
    params = {
        "mirostat_mode":2,
        "mirostat_tau": 6,
        "mirostat_eta":0.1,
        "temperature":0.7,
        "seed":1,
        "max_tokens":1500
    }
    # system_prompt = [
    #     " You are a top-tier legal editor who is great at cutting to the point and providing insightful analysis.",
    #     "In order to write such great analyses, you identify all the important arguments with the supporting reasons and facts before you write the analysis for it.",
    #     "To identify good arguments, you ask yourself Who did What, When they did it, Why they did it, and How they did it, then provide the answer to those questions.",
    #     "List each argument with a number and title that uniquely identifies the argument.",
    #     "Beneath each argument, write each supporting reason and supporting fact.",
    #     "Once you have written all the arguments, reasons, and facts, use them to write an thorough analysis under a Final Analysis: tag.",
    #     "Be sure to add any citations to the final analysis where the user would want to research the deeper complexities on their own.",
    #     "Be thorough and write out all the arguments, reasons, and facts before you analyze a document.",
    #     "Make sure that you write about every argument, reason, and fact, when you write your analysis.",
    #     "Finally, at the end of your analysis, think of any follow up critical details that would benefit from additional research and write them as if you were doing a web search for the answer."
    # ]
    #
    # content_prompt = [" Provide the arguments, reasons, and facts in this format:",
    #                   """**Argument 1:  **
    #                    - Reason 1:
    #                       - Fact 1:
    #                       - Fact 2: \n
    #                    - Reason 2:
    #                       - Fact 1: \n
    #
    #                   **Final Analysis:**
    #
    #                   **Citations:**
    #                   - Citation 1
    #                   - Citation 2
    #
    #                   **Additional Research:**
    #                   -
    #                   -
    #                   """,
    #                   "Write a detailed and thorough analysis of this document:",
    #
    #                   f"{text}",
    #                   "Assistant: "]

    # system_prompt = '\n'.join(system_prompt)
    # content_prompt = '\n'.join(content_prompt)

    full_chat = model.create_chat_completion(
        messages = [
            {"role": "system", "content": prompts.system_prompt},
            {
                "role": "user",
                "content": prompts.content_prompt
            }
        ],
        **params
    )
    summary = full_chat['choices'][0]['message']['content'].strip()
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
