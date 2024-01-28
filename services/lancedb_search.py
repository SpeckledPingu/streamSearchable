import json
import gzip
from sentence_transformers import SentenceTransformer
from fastapi import FastAPI
from pydantic import BaseModel
from pathlib import Path
from tqdm.auto import tqdm
import yaml
import lancedb
import sqlite3

app = FastAPI()
encoder = SentenceTransformer('all-MiniLM-L6-v2')
lance_location = Path('../data/indexes/lance/')
sqlite_location = Path('../data/indexes/documents.sqlite')

lancedb_conn = lancedb.connect(lance_location)
sqlite_conn = sqlite3.connect(sqlite_location)
indexes = lancedb_conn.table_names()

class IndexFile(BaseModel):
    file_name: str
    collection_name: str
    text_field: str

class IndexCollection(BaseModel):
    collection_name: str
    field_map: dict

class Query(BaseModel):
    collection_name: str
    query: str

@app.post("/query")
def index_query(query: Query):
    print(query.collection_name)
    index = lancedb_conn.open_table(query.collection_name)

    query_vec = encoder.encode([query])[0]
    search_results = index.search(query_vec).limit(20).to_list()
    uuids = {doc['uuid']:position for position, doc in enumerate(search_results)}
    uuid_query = [f"'{uuid}'" for uuid in list(uuids.keys())]
    document_results = sqlite_conn.execute(f"""SELECT uuid, * from {query.collection_name}
    WHERE uuid in ({','.join(uuid_query)});""")

    results = sorted([(document[0], document) for document in document_results])

    return [result[1] for result in results]

