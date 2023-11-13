## Load a file into memory
## Load the vectors into a vector index
## Load the text data into a bm25 index

import json
import gzip
from sentence_transformers import SentenceTransformer
from txtai.embeddings import Embeddings
from fastapi import FastAPI
from pydantic import BaseModel
from pathlib import Path

app = FastAPI()

embedding_index = Embeddings()
embedding_index.load('txtai_embedding_text.tar.gz')

class Index(BaseModel):
    file_name: str
    collection_name: str
    text_field: str

class Query(BaseModel):
    collection_name: str
    query: str

data_folder = Path('data/source')
config_file = Path('data/config/indexed.txt')
index_folder = Path('data/indexes')
index_name = 'index.tar.gz'
indexed_collections = list()
for _collection in index_folder.glob('*'):
    if _collection.is_dir():
        indexed_collections.append(_collection)
        
indexes = dict()
for _index in indexed_collections:
    index_path = _index.joinpath(index_name)
    print(index_path)
    print(index_path.exists())
    if index_path.exists():
        search_index = Embeddings()
        search_index.load(index_path.as_posix())
        indexes[_index.name] = search_index

print(indexes)

@app.post("/query")
def index_query(query: Query):
    print(query.collection_name)
    query_index = indexes[query.collection_name]
    print(query.query)
    print(type(query.query))
    # results = query_index.search(query.query)
    results = query_index.search(f"select * from txtai where similar('{query.query}')")
    return results

@app.post('/index')
def index_file(index: Index):
    file_name = index.file_name
    collection_name = index.collection_name
    text_field = index.text_field
    source_file = data_folder.joinpath(collection_name).joinpath(file_name)
    print(source_file)
    collection_folder = index_folder.joinpath(collection_name)
    index_file = collection_folder.joinpath('index.tar.gz')
    print(index_file)
    with open(config_file, 'r') as f:
        config_data = json.load(f)

    if collection_name in config_data:
        index_exists = True
    else:
        print('INDEX FILE LOCATION')
        print(index_file)
        collection_folder.mkdir(parents=True, exist_ok=True)
        config_data[collection_name] = list()
        
    collection_config = list(config_data.keys())
    if collection_name in collection_config:
        collection_index_path = collection_folder.joinpath('index.tar.gz')
        if collection_index_path.exists():
            print('INDEX EXISTS')
            index_exists = True
        else:
            index_exists = False
    else:
        print('INDEX FILE LOCATIN')
        print(index_file)
        index_file.mkdir(parents=True, exist_ok=True)
        config_data[collection_name] = list()
        index_exists = False

    if file_name in config_data[collection_name]:
        return {'message': 'File already indexed'}

    with open(source_file, 'r') as f:
        data = json.load(f)
        # data = [x[text_field] for x in data]

    if index_exists:
        search_index = Embeddings()
        print('INDEX FILE IN INDEX EMBEDDING')
        print(index_file)
        print('WOEOWEIJWOEITGHALDGJIOWOIETHEDASDFI')
        search_index.load(index_file.as_posix())
        search_index.upsert(data)
        search_index.save(index_file.as_posix())
        config_data[collection_name].append(source_file.name)
        with open(config_file, 'w') as f:
            json.dump(config_data, f)
        return {'message': 'Index updated'}
    else:
        search_index = Embeddings(path="sentence-transformers/all-MiniLM-L6-v2", content=True, keyword='hybrid')
        search_index.index(data)
        search_index.save(index_file.as_posix())
        config_data[collection_name].append(source_file.name)
        with open(config_file, 'w') as f:
            json.dump(config_data, f)
        
        return {'message': 'Index created and data loaded'}

