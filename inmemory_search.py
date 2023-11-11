## Load a file into memory
## Load the vectors into a vector index
## Load the text data into a bm25 index

import json
import gzip
from sentence_transformers import SentenceTransformer
from txtai.embeddings import Embeddings
from fastapi import FastAPI

app = FastAPI()

embedding_index = Embeddings()
embedding_index.load('txtai_embedding_text.tar.gz')

# with gzip.open('vectorized_combined_text_biden.json.gz','rt') as f:
#     data = json.load(f)


# @app.get("/vec_query")
# def vec_query(query, limit=20):
#     results = embedding_index.search(query, limit=limit)
#     result_data = [data[index[0]] for index in results]
#     return result_data

@app.get("/vec_query")
def vec_query(query, limit=20):
    results = embedding_index.search(query, limit=limit)
    result_data = [data[index[0]] for index in results]
    return result_data

@app.get('/fts_query')
def fts_query(query, limit=20):
    results = fts_index.search(query, limit=limit)
    result_data = {index[0]:data[index[0]] for index in results}
    return result_data

@app.get('/hybrid_query')
def hybrid_query(query):
    dense_results = vec_query(query, limit=200)
    fts_results = fts_query(query, limit=200)
    results = hybrid_rerank(dense_results, fts_results)
    result_data = {index[0]:data[index[0]] for index in results}


def hybrid_rerank(dense_results, fts_results):
    dense_index = [x[0] for x in dense_results]
    fts_index = [x[0] for x in fts_results]
    overlap = [x for x in dense_index if x in fts_index]
    #magic
    return overlap
