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

In the process, the backend will be refined and will become reSearchable Core and support a more advanced StreamSync UI.

Part of the inspiration for this app was because of the firehose of news and developments during the trump administration. It was a flood of news and developments, and it's part of the reason why I'm still planning to add graphs (so that a researcher can connect people, actions, things like that). So, you'll see "trump" on a number of these, I've been using a dataset I scraped of all of the Secretary of State press releases under the trump administration. I'll upload it and all of Biden's and Obama's in a simplified format so that it's easy to get things set up. Otherwise, you can get it over on Kaggle.

[Secretary of State Press Releases: Trump](https://www.kaggle.com/datasets/speckledpingu/secretary-of-state-press-releases-trump/data)

[Secretary of State Press Releases: Biden](https://www.kaggle.com/datasets/speckledpingu/secretary-of-state-press-releases-biden/data)

[Secretary of State Press Releases: Obama](https://www.kaggle.com/datasets/speckledpingu/secretary-of-state-press-releases-obama/data)

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
llama_cpp and OpenRouter are the current generative backend because, well, it works and they're free-ish.

KeyBert is a phrase extractor, by default using the all-MiniLM-L6-v2 as the base.

Spacy does entity extraction, by default using en_web_core_lg.

LanceDB and Sqlite are used as the main search backend. Txtai's embedded index is legacy, though it is a nice db+index system.

SQLite does the full document storage.

As this becomes more developed, a backend will be split off so that the UI is independent of the research functionality. That'd allow multiple front ends for different situations to be more easily built, customized, and new features adapted.

-----

## Future work
streamSearchable is meant to be quick to get running and functional for the average user. 
Because it's built on Streamlit, there are many core functions that aren't possible.

It's backend will be reusable in time, but standardization will happen after the reSearchable ui is built.

But first things first: Let's get the basics up and running.

-----

# Use
streamSearchable is meant to be a local search system for researching data you have. 


***Main Search with Lexical, Semantic, and Hybrid search options***
![image](https://github.com/SpeckledPingu/streamSearchable/assets/9573410/6b28bc22-bf7b-4145-a939-2a8b21910423)

***Search Result - 10 Blue Links style that expands to the full article without needing to navigate away***

*If the article is interesting, you can save it to a notes folder to search and process iteratively*
![image](https://github.com/SpeckledPingu/streamSearchable/assets/9573410/1bc6576b-c645-4069-acdd-f3f5d98dcc1c)

-----

***Notes Search - Allows you to open saved articles (search for this is forthcoming)***

*Batch extraction allows phrases, entities (courtesy of Spacy), and automatic summaries to be extracted by an LLM*
![image](https://github.com/SpeckledPingu/streamSearchable/assets/9573410/0c8280a4-04c5-4f27-af64-266a6bfd11bc)

***AutoNotes - Text fields allow for taking notes yourself, and options to get it started by using NLP tools to autogenerate options for you to review***
![image](https://github.com/SpeckledPingu/streamSearchable/assets/9573410/4aa42d2a-167c-4bd1-b6c2-80961ceed60b)


-----

***AutoResearch is a system to replace the standard chat interface with a sequence of language models performing different research activities***

*Special thanks to babyAGI for being the initial code for me to start building this and moving to my own methodology*

AutoResearch decomposes a query into 3 tasks. Those tasks have a plan of action, expected outcomes, and considerations as context for the downstream language models. They are saved with the task to guide the language model to a small part of the overall research and to provide potential ideas for the user to do further research on.

For each task, 3 (current) queries are formulated by a language model to research the task. Each is run against the index you've selected and the top 3 results are fed to a summarize model. This summary provides a quick distillation of the results as well as the results it was based on.

Each sub-query can be expanded to read through.

From each sub-query, the 3 summaries are synthesized into a single task summary. Currently there is this summarized-summary result and a result that is all 9 results fed into a single summarizing task. So far, the summary of summaries provides better results on a Mistral 7B Instruct.

***AutoResearch Output***

![image](https://github.com/SpeckledPingu/streamSearchable/assets/9573410/a498ef27-9535-44ec-baa7-33112262f9b0)

***Task Decomposition***

![image](https://github.com/SpeckledPingu/streamSearchable/assets/9573410/9995ffb7-c9fc-43d8-9053-12243f0920aa)

***Subquery Expansion***

![image](https://github.com/SpeckledPingu/streamSearchable/assets/9573410/42d2db7c-aa67-4c1f-9705-83b3e17c8b8a)

-----

***Different prompt templates for the AutoNote summary can be used. Prompt Templates editing and creation in browser is coming soon.***

Prompt Templating (in-browser coming soon)
![image](https://github.com/SpeckledPingu/streamSearchable/assets/9573410/0b7bbcec-fc09-42b2-8337-a955e0cb7d6a)

***Indexing***

To make setting up an index easier, if your data is in json, you can drag and drop it and map the text, title, date, and tags field for searching. All other fields are put into a metadata field that can be used later and expanded in the search results.

Note: I'm still new to LanceDB, but more capable indexing will come after moving to a more compatible UI. Typesense is also roadmapped to be used as an index and mongo as a document store to replace SQLite.

Drag and Drop indexing with lexical, semantic, and hybrid search using LanceDB and SQLite

![image](https://github.com/SpeckledPingu/streamSearchable/assets/9573410/20f91538-9d39-46e7-ab32-c40b7f1ff453)




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

* [x] Add limited chat-with-notes / chat-with-document capabilities

* [x] Add babyAGI style task decomposition for research

* [ ] Database support for tracking auto-research

* [ ] Yeah.... Need a requirements and test file....

* [ ] Prompt development in-browser (both writing and experimenting)

* [ ] ~~Add analysis for mapping extracted information and entities~~ *Extraction navigation to come later in a non-streamlit version*

* [ ] ~~Add graphing of entity maps - Kuzu Backend~~ *Graphing to come in a non-streamlit system*

* [ ] ~~Add aggregation functionality for statistical analysis of frequency/timeseries/etc~~ *Time series to come in a non-streamlit system*
