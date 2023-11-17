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

class IndexFile(BaseModel):
    file_name: str
    collection_name: str
    text_field: str

class IndexCollection(BaseModel):
    collection_name: str
    text_field: str

class Query(BaseModel):
    collection_name: str
    query: str

data_folder = Path('data/collections')
config_file = Path('data/config/indexed.json')
index_folder = Path('data/indexes')
index_name = 'index.tar.gz'


class SharedIndexes():
    def __init__(self, index_folder, data_folder, index_name='index.tar.gz'):
        self.index_folder = index_folder
        self.data_folder = data_folder
        self.index_name = index_name
        self.indexes = dict()

    def load_indexes(self):
        for _collection in self.index_folder.glob('*'):
            if _collection.is_dir():
                index_path = _collection.joinpath(self.index_name)
                if index_path.exists():
                    search_index = Embeddings()
                    search_index.load(index_path.as_posix())
                    self.indexes[_collection.name] = search_index

    def reload_index(self, collection_name):
        index_path = self.index_folder.joinpath(collection_name).joinpath(self.index_name)
        if index_path.exists():
            search_index = Embeddings()
            search_index.load(index_path.as_posix())
            self.indexes[collection_name] = search_index


indexes = SharedIndexes(index_folder, data_folder, index_name)

@app.post("/query")
def index_query(query: Query):
    print(query.collection_name)
    query_index = indexes.indexes[query.collection_name]
    print(query.query)
    print(type(query.query))
    # results = query_index.search(query.query)
    results = query_index.search(f"select * from txtai where similar('{query.query}')")
    print(len(results))
    return results


def index_multi_documents(filenames):
    print(filenames)
    for file in filenames:
        with open(file,'r') as f:
            data = json.load(f)
            if isinstance(data, dict):
                yield data
            else:
                for row in data:
                    print(row)
                    yield row

@app.post('/batch_index')
def batch_index(index: IndexCollection):
    collection_name = index.collection_name
    text_field = index.text_field
    source_file = data_folder.joinpath(collection_name)
    collection_folder = index_folder.joinpath(collection_name)
    index_file = collection_folder.joinpath('index.tar.gz')
    if index_file.exists():
        index_file.unlink()
    with open(config_file, 'r') as f:
        config_data = json.load(f)

    config_data[collection_name] = list()
    files_to_index = [x for x in source_file.glob('*') if x.is_file()]
    print(files_to_index)
    
    search_index = Embeddings(path="sentence-transformers/all-MiniLM-L6-v2", content=True, keyword='hybrid')
    search_index.index([x for x in index_multi_documents(files_to_index)])
    search_index.save(index_file.as_posix())
    
    config_data[collection_name] = [x.name for x in files_to_index]
    with open(config_file, 'w') as f:
        json.dump(config_data, f)

    indexes.indexes[collection_name] = search_index

    return search_index.config


@app.post('/index')
def index_file(index: IndexFile):
    file_name = index.file_name
    collection_name = index.collection_name
    # text_field = index.text_field
    source_file = data_folder.joinpath(collection_name).joinpath(file_name)
    print(source_file)
    collection_folder = index_folder.joinpath(collection_name)
    index_file = collection_folder.joinpath('index.tar.gz')

    with open(config_file, 'r') as f:
        config_data = json.load(f)

    if index_file.exists() and collection_name in config_data:
        index_exists = True
        search_index = indexes.indexes[collection_name]
    else:
        index_exists = False
        collection_folder.mkdir(parents=True, exist_ok=True)
        config_data[collection_name] = list()
        search_index = Embeddings(path="sentence-transformers/all-MiniLM-L6-v2", content=True, keyword='hybrid')
        indexes.indexes[collection_name] = search_index

    if file_name in config_data[collection_name]:
        return {'message': 'File already indexed'}
    else:
        with open(source_file, 'r') as f:
            data = json.load(f)

    if index_exists:
        search_index.upsert(data)
    else:
        search_index.index(data)

    search_index.save(index_file.as_posix())
    config_data[collection_name].append(source_file.name)
    with open(config_file, 'w') as f:
        json.dump(config_data, f)

    indexes.reload_index(collection_name)
    return search_index.config


