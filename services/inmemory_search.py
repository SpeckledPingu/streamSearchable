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
from tqdm.auto import tqdm
import yaml

app = FastAPI()
models = SentenceTransformer('all-MiniLM-L6-v2')

# embedding_index = Embeddings()
# embedding_index.load('txtai_embedding_text.tar.gz')

class IndexFile(BaseModel):
    file_name: str
    collection_name: str
    text_field: str

class IndexCollection(BaseModel):
    collection_name: str
    text_field: str
    data_location: str

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


def index_multi_documents(filenames, split_on_list=False):
    print(filenames)
    for file in filenames:
        with open(file,'r') as f:
            data = json.load(f)
            if isinstance(data, dict):
                yield data
            else:
                print(data[0])
                for row in tqdm(data):
                    if 'tags' in row and isinstance(row['tags'], list):
                        _tags = ','.join([_tag['tag_name'] for _tag in row['tags']])
                        row['tags'] = _tags
                    else:
                        row['tags'] = ''

                    if isinstance(row['text'], list):
                        row['text'] = '\n\n'.join(row['text'])
                    # print(row)
                    yield row

@app.post('/batch_index')
def batch_index(index: IndexCollection):
    collection_name = index.collection_name
    text_field = index.text_field
    data_location = index.data_location
    source_file = data_folder.joinpath(collection_name)
    collection_folder = index_folder.joinpath(collection_name)
    index_file = collection_folder.joinpath('index.tar.gz')
    if index_file.exists():
        index_file.unlink()

    config[collection_name] = dict()
    files_to_index = [x for x in source_file.glob('*.json') if x.is_file()]

    search_index = Embeddings(models=models, content=True, keyword='hybrid',
                              device='gpu', batch_size=32)
    search_index.index([x for x in index_multi_documents(files_to_index)])
    search_index.save(index_file.as_posix())

    config[collection_name]['source_folder'] = source_file.name
    config[collection_name]['source_files'] = [x.name for x in files_to_index]

    with open(files_to_index[0],'r') as f:
        column_file = json.load(f)
    if isinstance(column_file, list):
        column_file = column_file[0]
    fields = list(column_file.keys())
    config[collection_name]['fields'] = fields

    with open(config_file, 'w') as f:
        yaml.dump(config, f)

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
        config = yaml.unsafe_load(f)

    if index_file.exists() and collection_name in config:
        index_exists = True
        search_index = indexes.indexes[collection_name]
    else:
        index_exists = False
        collection_folder.mkdir(parents=True, exist_ok=True)
        config[collection_name] = dict()
        config[collection_name]['source_folder'] = collection_name
        config[collection_name]['source_files'] = list()
        config[collection_name]['fields'] = list()
        search_index = Embeddings(models=models, content=True, keyword='hybrid')
        indexes.indexes[collection_name] = search_index

    if file_name in config[collection_name]['source_files']:
        return {'message': 'File already indexed'}
    else:
        with open(source_file, 'r') as f:
            data = json.load(f)

    if index_exists:
        search_index.upsert(data)
        current_fields = config[collection_name]['fields']
        for _field in list(data.keys()):
            if _field not in current_fields:
                current_fields.append(_field)
        config[collection_name]['fields'] = current_fields
    else:
        search_index.index(data)
        config[collection_name]['fields'] = list(data.keys())

    search_index.save(index_file.as_posix())
    config[collection_name]['source_files'].append(source_file.name)

    with open(config_file, 'w') as f:
        yaml.dump(config, f)

    indexes.reload_index(collection_name)
    return search_index.config


