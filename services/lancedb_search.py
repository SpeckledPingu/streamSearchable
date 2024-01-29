import json
import gzip
from sentence_transformers import SentenceTransformer
from fastapi import FastAPI
from pydantic import BaseModel
from pathlib import Path
from tqdm.auto import tqdm
import pandas as pd
import lancedb
import sqlite3

app = FastAPI()
encoder = SentenceTransformer('all-MiniLM-L6-v2')
lance_location = Path('../indexes')
sqlite_location = Path('../data/indexes/documents.sqlite')

lancedb_conn = lancedb.connect(lance_location)
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
    top_k: int

class HybridQuery(BaseModel):
    collection_name: str
    query: str
    top_k: int
    fts_weight: float
    vec_weight: float

@app.post("/vec_query")
def index_query(query: Query):
    sqlite_conn = sqlite3.connect(sqlite_location)

    print(query.collection_name)
    index = lancedb_conn.open_table(query.collection_name)

    query = encoder.encode(query.query)
    search_results = index.search(query).limit(query.top_k).to_list()
    uuids = {doc['uuid']:position for position, doc in enumerate(search_results)}
    scores = {doc['uuid']:1-doc['_distance'] for doc in search_results}

    uuid_query = [f"'{uuid}'" for uuid in list(uuids.keys())]
    document_results = sqlite_conn.execute(f"""SELECT uuid, * from trump WHERE uuid in ({','.join(uuid_query)});""").fetchall()
    field_maps = ['uuid']
    field_maps.extend([x[1] for x in sqlite_conn.execute(f"PRAGMA table_info({query.collection_name})").fetchall()])

    def results_to_display(row, table_schema, scores):
        doc = {field:value for field,value in zip(table_schema,row)}
        doc['score'] = scores[doc['uuid']]
        return doc

    document_results = [results_to_display(row, field_maps, scores) for row in document_results]
    # provide the proper sorting because sqlite will not respect the original order in the where clause
    document_results = sorted([(uuids[doc['uuid']], doc) for doc in document_results])
    # undo the sorting key
    document_results = [x[1] for x in document_results]
    sqlite_conn.close()
    return document_results, list(document_results[0].keys())


@app.post("/fts_query")
def index_query(query: Query):
    sqlite_conn = sqlite3.connect(sqlite_location)

    print(query.collection_name)
    index = lancedb_conn.open_table(query.collection_name)

    search_results = index.search(query.query).limit(query.top_k).to_list()
    uuids = {doc['uuid']:position for position, doc in enumerate(search_results)}
    scores = {doc['uuid']:doc['score'] for doc in search_results}

    uuid_query = [f"'{uuid}'" for uuid in list(uuids.keys())]
    document_results = sqlite_conn.execute(f"""SELECT uuid, * from {query.collection_name} WHERE uuid in ({','.join(uuid_query)});""").fetchall()
    field_maps = ['uuid']
    field_maps.extend([x[1] for x in sqlite_conn.execute(f"PRAGMA table_info({query.collection_name})").fetchall()])

    def results_to_display(row, table_schema, scores):
        doc = {field:value for field,value in zip(table_schema,row)}
        doc['score'] = scores[doc['uuid']]
        return doc

    document_results = [results_to_display(row, field_maps, scores) for row in document_results]
    # provide the proper sorting because sqlite will not respect the original order in the where clause
    document_results = sorted([(uuids[doc['uuid']], doc) for doc in document_results])
    # undo the sorting key
    document_results = [x[1] for x in document_results]
    sqlite_conn.close()
    return document_results, list(document_results[0].keys())



@app.post("/hybrid")
def index_query(query: HybridQuery):
    sqlite_conn = sqlite3.connect(sqlite_location)

    print(query.collection_name)
    index = lancedb_conn.open_table(query.collection_name)

    fts_results = index.search(query.query).limit(query.top_k).to_list()
    fts_uuids = {doc['uuid']:position for position, doc in enumerate(fts_results)}
    fts_scores = {doc['uuid']:doc['score'] for doc in fts_results}
    fts_rrf = {uuid:1/(40+position) for uuid, position in fts_uuids.items()}

    vec_results = index.search(encoder.encode(query.query)).limit(query.top_k).to_list()
    vec_uuids = {doc['uuid']:position for position, doc in enumerate(vec_results)}
    vec_scores = {doc['uuid']:1-doc['_distance'] for doc in vec_results}
    vec_rrf = {uuid:1/(40+position) for uuid, position in vec_uuids.items()}

    rrf_df = pd.concat([pd.Series(vec_rrf, name='vec'), pd.Series(fts_rrf, name='fts')], axis=1).dropna()
    rrf_df['rrf'] = query.vec_weight * rrf_df['vec'] + query.fts_weight * rrf_df['fts']
    rrf_df['rrf_rank'] = rrf_df['rrf'].rank(ascending=False)

    rrf_rank = rrf_df['rrf_rank'].to_dict()
    rrf_score = rrf_df['rrf'].to_dict()

    # uuid_query = [f"'{uuid}'" for uuid in list(uuids.keys())]
    uuid_query = [f"'{uuid}'" for uuid in rrf_df.index.values]

    if len(uuid_query) > 0:
        uuid_query = ", ".join(uuid_query)
    sql_query = f"""SELECT uuid, * from {query.collection_name} WHERE uuid in ({uuid_query});"""
    document_results = sqlite_conn.execute(sql_query).fetchall()
    field_maps = ['uuid']
    field_maps.extend([x[1] for x in sqlite_conn.execute(f"PRAGMA table_info({query.collection_name})").fetchall()])

    print(field_maps)
    def results_to_display(row, table_schema, scores):
        print(row[:3])
        doc = {field:value for field,value in zip(table_schema,row)}
        doc['score'] = scores[doc['uuid']]
        return doc

    document_results = [results_to_display(row, field_maps, rrf_score) for row in document_results]
    # provide the proper sorting because sqlite will not respect the original order in the where clause
    document_results = sorted([(rrf_rank[doc['uuid']], doc) for doc in document_results])
    # undo the sorting key
    document_results = [x[1] for x in document_results]

    sqlite_conn.close()

    return document_results, list(document_results[0].keys())

    # if len(search_results) > 0:
    #     if 'score' in search_results[0]:
    #         scores = {doc['uuid']:doc['score'] for doc in search_results}
    #     elif '_distance' in search_results[0]:
    #         scores = {doc['uuid']:1-doc['_distance'] for doc in search_results}
    #     else:
    #         scores = {doc['uuid']:-999 for doc in search_results}