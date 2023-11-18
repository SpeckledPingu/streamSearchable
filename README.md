# streamSearchable 
#### *It's about augmentation, not automation*

## Motivation
streamSearchable is meant to be a stripped down streamlit app that incorporates traditional search with llm capabilities. This is meant to be a merger between generative models that are used for chat, and the current logical workflows we use for research.

Chat interfaces are great for directly working on a piece of text, but it's often the case that you need to find the relevant text first. Chat systems don't lend themselves to organization of thoughts, notes, key details, and the output is still unstructured unless more powerful models are used. Even then, prompt tuning is a major part of the effort.

Rather than developing prompts, we can accept lower quality results if it's in a predefined structure for note taking and referencing. In the end, when we're researching, the researcher is doing the synthesis and will do it better than any current LLM.

streamSearchable focuses on speeding up the process of identifying relevant data and drawing the contours of what is important. It leverages LLMs, embeddings, vector/fts/hybrid search, to sort the mass of text in front of us when starting a research project. 

## Current Status
GPT4All is the current generative backend because, well, it works and they've got some great models that can fit onto even an older GPU.

KeyBert is a phrase extractor, by default using the all-MiniLM-L6-v2 as the base.

Spacy does entity extraction, by default using en_web_core_sm.

txtai is used as the search backend.

Currently, these are hardcoded to get a poc moving. But in time it'll expand out.

## Future work
streamSearchable is meant to be quick to get running and functional for the average user. Because it's built on Streamlit, there are many core functions that aren't possible.

reSearchable will be a companion app that is more functional and capable, but first things first: Let's get the basics up and running.

## TODO
* [x] Clean up file and index creation to a single page

* [x] Clean up data file distribution for collections and indexes

* [x] Add initial Yaml configuration and index tracking

* [x] Merge bulk indexing and file indexing inmemory search

* [ ] Notes are additive for summaries and entities

* [ ] Standardize file naming schema for hard copies of notes

* [ ] Accept csvs and tar/gz json files

* [ ] Dynamically configurable schema (remove hardcoding)

* [ ] Schema mapping input on upload to map to a standardized schema

* [ ] Standardize note schema

* [ ] Add analysis for mapping extracted information and entities

* [ ] Add graphing of entity maps

* [ ] Add aggregation functionality for statistical analysis of frequency/timeseries/etc

* [ ] Free form note taking

* [ ] Post-analysis auto-fill free form notes

* [ ] Weaviate/Qdrant/Milvus backend support
