# streamSearchable 
#### *It's about augmentation, not automation*

## Motivation
Research is often different than normal search we encounter every day. 
In normal search, there is an assumption that there is a set of relevant documents that are supposed to be the top results.
In research, relevance is far more ambiguous, especially when working with primary documents and you don't have a clear
thesis or concept of the document's utility yet. A specialized search for this needs to account for the different workflow.
Documents must be found from a collection, but those initial results can involve long and tedious reading to find any relevant bits.
By treating the search as a knowledge filtering, where a document is scanned for information and considered "interesting"
and meant for later review or analysis, LLMs can act as an intermediary to speed up that second part by summarizing or 
through relationships to other documents, important to an overall web of information.

streamSearchable is meant to be a stripped down streamlit app that incorporates traditional search with llm capabilities. 
This is meant to be a merger between generative models that are used for chat, and the current logical workflows we use for research.

The development workflow is to build a well functioning, though not necessarily fully featured, Streamlit ui.
Streamlit is selected because it's easily customized and good for prototyping changes.
But, it isn't that great for more advanced work. This is pushing the limits of what I think it can do.

In the process, the backend will be refined and will become reSearchable Core and support a more advanced StreamSync ui.

**Why no chat interface?**

Chat interfaces are great for directly working on a piece of text, but it's often the case that you need to find the relevant text first. 
Chat systems don't lend themselves to organization of thoughts, notes, key details, and the output is still unstructured unless more powerful models are used. Even then, prompt tuning is a major part of the effort.

Prompt engineering is a laborious task. There is some amount of prompt engineering that is involved for this for the templates.
But, there will be a set of default templates for different kinds of summarization activities.
This results in a search system that acts as a knowledge filtering system as well as a knowledge discovery system.
Researching notes can be in-depth, but it can be improved by scanning a search result and pushing it into a note collection.
In that note collection, batch extraction, summarization, and/or other services can be run automatically to speed up the review of that document.

streamSearchable focuses on speeding up the process of identifying relevant data and drawing the contours of what is important. It leverages LLMs, embeddings, vector/fts/hybrid search, to sort the mass of text in front of us when starting a research project. 

## Current Status
GPT4All is the current generative backend because, well, it works and they've got some great models that can fit onto even an older GPU.

KeyBert is a phrase extractor, by default using the all-MiniLM-L6-v2 as the base.

Spacy does entity extraction, by default using en_web_core_sm.

LanceDB and Sqlite are used as the main search backend. Txtai's embedded index is legacy, though it is a nice db+index system.

## Future work
streamSearchable is meant to be quick to get running and functional for the average user. 
Because it's built on Streamlit, there are many core functions that aren't possible.

It's backend will be reusable in time, but standardization will happen after the reSearchable ui is built.

But first things first: Let's get the basics up and running.

## TODO
* [x] Clean up file and index creation to a single page

* [x] Clean up data file distribution for collections and indexes

* [x] Add initial Yaml configuration and index tracking

* [x] Merge bulk indexing and file indexing inmemory search

* [x] Notes are additive for summaries and entities

* [x] Schema mapping input on upload to map to a standardized schema (Partially complete)

* [x] Standardize note schema

* [x] Free form note taking

* [x] Post-analysis auto-fill free form notes
* [x] Llama-CPP backend
  * [ ] Directions for linux llama cpp install with install bash script

* [x] ~~Standardize file naming schema for hard copies of notes~~

* [x] Accept csvs and tar/gz json files

* [x] Dynamically configurable schema (remove hardcoding)
   * [x] Model backend configurations
   * [x] Dynamic indexing for json and csv

* [x] ~~Weaviate/Qdrant/Milvus backend support~~ LanceDB and SQLite provide the embedded search/db qualities better

* [x] Full embedded database and index backend for local hosting data

* [x] OpenRouter external model api for low-cost non-llama_cpp models

* [ ] Add limited chat-with-notes / chat-with-document capabilities

* [ ] Add babyAGI style task decomposition for research

* [ ] Yeah.... Need a requirements and test file....

* [ ] Prompt development in-browser (both writing and experimenting)

* [ ] Add analysis for mapping extracted information and entities

* [ ] Add graphing of entity maps - Kuzu Backend

* [ ] Add aggregation functionality for statistical analysis of frequency/timeseries/etc