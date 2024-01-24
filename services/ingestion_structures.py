from uuid import uuid4
import json
import pandas as pd
class Document():
    def __init__(self, document:dict, title:str, text:str, fields, tags=None, date=None, file_path=None, splitter=None):
        self.title = document[title]
        self.text = document[text]
        self.tags = document[tags] if tags is not None else list()
        self.date = document[date] if date is not None else None
        self.file_path = file_path
        self.extra = {k:document[k] for k in fields if k not in [title, text, tags, date]}
        self.uuid = uuid4()
        self.save_uuids = list()
        self.splitter = splitter

    def split_text(self):
        self.text = self.splitter(self.text)

    def create_json_document(self, text, uuids=None):
        _document = {'title':self.title,
                     'text':text,
                     'tags':self.tags,
                     'date':self.date,
                     'file_path':str(self.file_path),
                     'document_uuid':self.uuid,
                     'save_uuid': uuids if uuids is not None else uuid4()}
        for field, value in self.extra.items():
            _document[field] = value
        return _document
    def save(self, file_path=None):
        if file_path is None: file_path = self.file_path

        if isinstance(self.text, list):
            _document = self.create_json_document('\n'.join(self.text), self.save_uuids)
        else:
            _document = self.create_json_document(self.text, self.save_uuids)

        with open(file_path, 'w') as f:
            json.dump(_document, f)

    def return_index_document(self, split_text=False):
        # modify this to use a new system where split text can be 'keep' for current structure, 'combine' for list tolerance, and 'split' for segmentation
        documents_to_index = list()
        if split_text and self.splitter is None:
            raise "No splitter has been provided"
        elif split_text and self.splitter is not None:
            self.split_text()

        if isinstance(self.text, str):
            _document = self.create_json_document(self.text)
            documents_to_index.append(_document)
            # save_document = _document
        elif isinstance(self.text, list):
            for _text_chunk in self.text:
                _document = self.create_json_document(_text_chunk)
                self.save_uuids.append(_document['save_uuid'])
                yield _document
            # save_document = self.create_json_document('\n'.join(self.text), save_uuid=self.save_uuids)

        # self.save(self.file_path)
        return documents_to_index

class CsvDocument():
    def __init__(self, title:str, text:str, fields, tags=None, date=None, file_path=None, save_path=None, splitter=None):
        self.title = title
        self.text = text
        self.tags = tags
        self.date = date
        self.fields = fields
        self.extra = [k for k in fields if k not in [title, text, tags, date]]
        self.file_path = file_path
        self.splitter = splitter
        self.save_path = save_path
        self.documents = pd.read_csv(file_path)

    def return_index_document(self, document, split_text=False):
        _document = Document(document, self.title, self.text, self.fields, self.tags, self.date, self.save_path, self.splitter)
        return _document.return_index_document(_document, split_text=split_text)

    def return_documents(self):
        for document in self.documents.to_dict(orient='records'):
            yield self.return_index_document(document, split_text=True if self.splitter is not None else False)

class JsonDocument():
    def __init__(self, title:str, text:str, fields, tags=None, date=None, file_path=None, save_path=None, splitter=None):
        self.title = title
        self.text = text
        self.tags = tags
        self.date = date
        self.fields = fields
        self.extra = [k for k in fields if k not in [title, text, tags, date]]
        self.file_path = file_path
        self.splitter = splitter
        self.save_path = save_path

    def return_index_document(self, document, split_text=False):
        _document = Document(document, self.title, self.text, self.fields, self.tags, self.date, self.save_path, self.splitter)
        return _document.return_index_document(_document, split_text=split_text)

    def return_documents(self):
        with open(self.file_path, 'r') as f:
            self.documents = json.load(f)
        if isinstance(self.documents, list):
            for document in self.documents:
                yield self.return_index_document(document, split_text=True if self.splitter is not None else False)
        else:
            return self.return_index_document(self.documents, split_text=True if self.splitter is not None else False)