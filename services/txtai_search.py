import json
import gzip
from sentence_transformers import SentenceTransformer
from txtai.embeddings import Embeddings
from fastapi import FastAPI
from pydantic import BaseModel
from pathlib import Path
from tqdm.auto import tqdm
import yaml
from .ingestion_structures import Document, JsonDocument, CsvDocument

app = FastAPI()
models = SentenceTransformer('all-MiniLM-L6-v2')

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

data_folder = Path('../data/collections')
config_file = Path('../data/config/indexes.yaml')
index_folder = Path('../data/indexes')
index_name = 'index.tar.gz'

with open(config_file, 'r') as f:
    config = yaml.unsafe_load(f)

class SharedIndexes():
    def __init__(self, index_folder, data_folder, index_name='index.tar.gz'):
        self.index_folder = index_folder
        self.data_folder = data_folder
        self.index_name = index_name
        self.indexes = dict()

    def load_indexes(self):
        print([x for x in index_folder.glob('*')])
        for _collection in self.index_folder.glob('*'):
            if _collection.stem[0] == '.':
                continue
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
indexes.load_indexes()
print(indexes.indexes)
@app.post("/query")
def index_query(query: Query):
    print(query.collection_name)
    query_index = indexes.indexes[query.collection_name]
    print(query.query)
    print(type(query.query))
    # results = query_index.search(query.query)
    results = query_index.search(f"select * from txtai where similar('{query.query}')", limit=20)
    print(len(results))
    return results

@app.post('/batch_index')
def batch_index(index: IndexCollection):
    collection_name = index.collection_name
    fields = index.field_map
    source_file = data_folder.joinpath(collection_name)
    collection_folder = index_folder.joinpath(collection_name)
    index_file = collection_folder.joinpath('index.tar.gz')
    if index_file.exists():
        index_file.unlink()

    config[collection_name] = dict()
    files_to_index = [x for x in source_file.glob('*.json') if x.is_file()]

    search_index = Embeddings(models=models, content=True, keyword='hybrid',
                              device='gpu', batch_size=32)
    for file in files_to_index:
        documents = JsonDocument(title=fields['title'], text=fields['text'], tags=fields['tags'],
                                date=fields['date'], fields=fields, file_path=file)
        search_index.index([x for x in documents.return_documents()])

    search_index.save(index_file.as_posix())

    config[collection_name]['source_folder'] = source_file.name
    config[collection_name]['source_files'] = [x.name for x in files_to_index]
    config[collection_name]['fields'] = fields

    with open(config_file, 'w') as f:
        yaml.dump(config, f)

    indexes.indexes[collection_name] = search_index

    return search_index.config
