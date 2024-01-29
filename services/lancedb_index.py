import json
from sentence_transformers import SentenceTransformer
from pydantic.main import ModelMetaclass
from pathlib import Path
import pandas as pd
import sqlite3
from uuid import uuid4
import lancedb

encoder = SentenceTransformer('all-MiniLM-L6-v2')

data_folder = Path('data/collections')
config_file = Path('data/config/indexes.yaml')
index_folder = Path('indexes')

lance_folder = Path('indexes')
lance_folder.mkdir(parents=True, exist_ok=True)

sqlite_folder = Path('data/indexes/')

class LanceDBDocument():
    def __init__(self, document:dict, title:str, text:str, fields, tags=None, date=None, file_path=None):
        self.document = self.fill_missing_fields(document, text, title, tags, date)
        # self.text = document[text]
        # self.tags = document[tags] if tags is not None else list()
        # self.date = document[date] if date is not None else None
        self.file_path = file_path
        self.metadata = {k:document[k] for k in fields if k not in [title, text, tags, date]}
        self.uuid = str(uuid4())
        self.save_uuids = list()
        self.sqlite_fields = list()
        self.lance_exclude = list()

    def fill_missing_fields(self, document, text, title, tags, date):
        if title not in document:
            self.title = ''
        else:
            self.title = document[title]

        if text not in document:
            self.text = ''
        else:
            self.text = document[text]

        if date not in document:
            self.date = ''
        else:
            self.date = document[date]

        if tags not in document:
            self.tags = list()
        else:
            self.tags = document[tags]


    def create_json_document(self, text, uuids=None):
        """Creates a custom dictionary object that can be used for both sqlite and lancedb
        The full document is always stored in sqlite where fixed fields are:
            title
            text
            date
            filepath
            document_uuid - used for retrieval from lancedb results

            Json field contains the whole document for retrieval and display
            Lancedb only gets searching text, vectorization of that, and filter fields
        """
        _document = {'title':self.title,
                     'text':text,
                     'tags':self.tags,
                     'date':self.date,
                     'file_path':str(self.file_path),
                     'uuid':self.uuid,
                     'metadata': self.metadata}

        self._enforce_tags_schema()
        for field in ['title','date','file_path']:
            self.enforce_string_schema(field, _document)
        return _document

    def enforce_string_schema(self, field, test_document):
        if not isinstance(test_document[field], str):
            self.lance_exclude.append(field)

    def _enforce_tags_schema(self):
        # This enforces a simple List[str] format for the tags to match what lancedb can use for filtering
        # If they are of type List[Dict] as a nested field, they are stored in sqlite for retrieval
        if isinstance(self.tags, list):
            tags_are_list = True
            for _tag in self.tags:
                if not isinstance(_tag, str):
                    tags_are_list = False
                    break
        if not tags_are_list:
            self.lance_exclude.append('tags')

    def return_document(self):
        document = self.create_json_document(self.text)
        return document

class SqlLiteIngest():
    def __init__(self, documents, source_file, db_location, index_name, overwrite):
        self.documents = documents
        self.source_file = source_file
        self.db_location = db_location
        self.index_name = index_name
        self.overwrite = overwrite

    def initialize(self):
        self.connection = sqlite3.connect(self.db_location)
        if self.overwrite:
            self.connection.execute(f"""DROP TABLE IF EXISTS {self.index_name};""")

        table_exists = self.connection.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{self.index_name}';").fetchall()

        if len(table_exists) == 0:
            self.connection.execute(f"""
            CREATE TABLE {self.index_name}(
            id INTEGER PRIMARY KEY NOT NULL,
            uuid STRING NOT NULL,
            text STRING NOT NULL,
            title STRING,
            date STRING,
            source_file STRING,
            metadata JSONB);""")

    def insert(self, document):
        self.connection.execute(f"""INSERT INTO 
        {self.index_name} (uuid, text, title, date, source_file, metadata)
        VALUES ('{document.uuid.replace("'","''")}', '{document.text.replace("'","''")}', 
        '{document.title.replace("'","''")}', '{document.date.replace("'","''")}', 
        '{self.index_name.replace("'","''")}', '{json.dumps(document.metadata).replace("'","''")}');""")

    def bulk_insert(self):
        for document in self.documents:
            self.insert(document)
        self.connection.commit()
        self.connection.close()


from lancedb.pydantic import LanceModel, Vector, List

class LanceDBSchema384(LanceModel):
    uuid: str
    text: str
    title: str
    tags: List[str]
    vector: Vector(384)

class LanceDBSchema512(LanceModel):
    uuid: str
    text: str
    title: str
    tags: List[str]
    vector: Vector(512)

class LanceDBIngest():
    def __init__(self, documents, lance_location, index_name, overwrite, encoder, schema):
        self.documents = documents
        self.lance_location = lance_location
        self.index_name = index_name
        self.overwrite = overwrite
        self.encoder = encoder
        self.schema = schema

    def initialize(self):
        self.db = lancedb.connect(self.lance_location)
        existing_tables = self.db.table_names()
        self.documents = [self.prep_documents(document) for document in self.documents]
        if self.overwrite:
            self.table = self.db.create_table(self.index_name, data=self.documents, mode='overwrite', schema=self.schema.to_arrow_schema())
        else:
            if self.index_name in existing_tables:
                self.table = self.db.open_table(self.index_name)
                self.table.add(self.documents)
            else:
                self.table = self.db.create_table(self.index_name, data=self.documents, schema=self.schema.to_arrow_schema())

    def prep_documents(self, document):
        lance_document = dict()
        lance_document['text'] = document.text
        lance_document['vector'] = self.encoder.encode(document.text)
        lance_document['uuid'] = document.uuid
        lance_document['title'] = document.title
        lance_document['tags'] = document.tags
        return lance_document

    def insert(self, document):
        document['vector'] = self.encoder.encode(document.text)
        self.table.add(document)
    def bulk_insert(self, create_vectors=False):
        if create_vectors:
            self.table.create_index(vector_column_name='vector', metric='cosine')

        self.table.create_fts_index(field_names=['title','text'], replace=True)
        return self.table

class IndexDocuments():
    def __init__(self,field_mapping, source_file, index_name, overwrite):
        self.field_mapping = field_mapping
        self.source_file = source_file
        self.index_name = index_name
        self.overwrite = overwrite

    def open_json(self):
        with open(self.source_file, 'r') as f:
            self.data = json.load(f)
            print(self.data)

    def open_csv(self):
        self.data = pd.read_csv(self.source_file)

    def create_document(self, document):
        document = LanceDBDocument(document,
                                   text=self.field_mapping['text'],
                                   title=self.field_mapping['title'],
                                   tags=self.field_mapping['tags'],
                                   date=self.field_mapping['date'],
                                   fields=list(document.keys()),
                                   file_path=self.source_file
                                   )
        return document

    def create_documents(self):
        self.documents = [self.create_document(document) for document in self.data]

    def ingest(self, overwrite=False):
        # lance_path = Path(f'../indexes/lance')
        lance_folder.mkdir(parents=True, exist_ok=True)
        lance_ingest = LanceDBIngest(documents=self.documents,
                                     lance_location=lance_folder,
                                     # field_mapping=self.field_mapping,
                                     index_name=self.index_name,
                                     overwrite=self.overwrite,
                                     encoder=encoder,
                                     schema=LanceDBSchema384)
        lance_ingest.initialize()
        if len(self.documents) <= 256:
            _table = lance_ingest.bulk_insert(create_vectors=False)
        else:
            _table = lance_ingest.bulk_insert(create_vectors=True)

        sql_path = sqlite_folder.joinpath('documents.sqlite')

        sqlite_ingest = SqlLiteIngest(documents=self.documents,
                                      source_file=self.source_file,
                                      db_location=sql_path,
                                      index_name=self.index_name,
                                      overwrite=self.overwrite)
        sqlite_ingest.initialize()
        sqlite_ingest.bulk_insert()





