# DocuMate02

Simple ingestion pipeline for a FastAPI documentation RAG assistant.

## Quick start

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
docker compose up -d qdrant postgres
python flows/ingestion_flow.py
python scripts/sanity_check.py
```

The pipeline downloads Markdown documentation from FastAPI's GitHub repository,
splits it at `##` headings, creates 384-dimensional local embeddings, and
stores both dense (Qdrant) and lexical (BM25) indexes.


```bash
python flows/ingestion_flow.py
```

```bash
python flows/ingestion_flow.py
06:55:40.682 | INFO    | prefect - Starting temporary server on http://127.0.0.1:8413
See https://docs.prefect.io/v3/concepts/server#how-to-guides for more information on running a dedicated Prefect server.
06:55:50.187 | INFO    | Flow run 'witty-guillemot' - Beginning flow run 'witty-guillemot' for flow 'ingest-fastapi-docs'
06:56:52.394 | INFO    | Task run 'fetch_task-d39' - Fetched 155 files
06:56:52.398 | INFO    | Task run 'fetch_task-d39' - Finished in state Completed()
06:56:52.458 | INFO    | Task run 'chunk_task-cbf' - Created 925 chunks
06:56:52.464 | INFO    | Task run 'chunk_task-cbf' - Finished in state Completed()
Warning: You are sending unauthenticated requests to the HF Hub. Please set a HF_TOKEN to enable higher rate limits and faster downloads.
06:57:07.076 | WARNING | huggingface_hub.utils._http - Warning: You are sending unauthenticated requests to the HF Hub. Please set a HF_TOKEN to enable higher rate limits and faster downloads.
modules.json: 100%|| 349/349 [00:00<00:00, 1.73MB/s]
config_sentence_transformers.json: 100%|| 116/116 [00:00<00:00, 605kB/s]
README.md: 100%|[00:00<00:00, 27.9MB/s]
sentence_bert_config.json: 100%|[00:00<00:00, 357kB/s]
config.json: 100%|612/612 [00:00<00:00, 3.54MB/s]
model.safetensors: downloading bytes: 85.0MB, 8.04MB/s  
model.safetensors: reconstructing file: 100%|90.9MB / 90.9MB, 8.77MB/s  
Loading weights: 100%|103/103 [00:00<00:00, 7770.72it/s]
tokenizer_config.json: 100%|350/350 [00:00<00:00, 2.45MB/s]
vocab.txt: 100%|232k/232k [00:00<00:00, 68.3MB/s]
tokenizer.json: 100%|466k/466k [00:00<00:00, 96.1MB/s]
special_tokens_map.json: 100%|112/112 [00:00<00:00, 588kB/s]
config.json: 100%|190/190 [00:00<00:00, 985kB/s]
06:57:57.673 | INFO    | Task run 'embed_task-321' - Finished in state Completed()
06:58:02.124 | INFO    | Task run 'index_task-0c0' - Indexed 925 points
06:58:02.129 | INFO    | Task run 'index_task-0c0' - Finished in state Completed()
06:58:02.845 | INFO    | Flow run 'witty-guillemot' - Finished in state Completed()
06:58:02.865 | INFO    | prefect - Stopping temporary server on http://127.0.0.1:8413
```

```bash
python scripts/sanity_check.py
```
```bash
$ python scripts/sanity_check.py
Warning: You are sending unauthenticated requests to the HF Hub. Please set a HF_TOKEN to enable higher rate limits and faster downloads.
Loading weights: 100%|| 103/103 [00:00<00:00, 7308.51it/s]
0.584362 docs/en/docs/tutorial/dependencies/sub-dependencies.md Recap { #recap }
0.5843266 docs/en/docs/tutorial/dependencies/index.md What is "Dependency Injection" { #what-is-dependency-injection }
0.5031692 docs/en/docs/tutorial/dependencies/index.md Simple usage { #simple-usage }
0.46812811 docs/en/docs/tutorial/dependencies/index.md First Steps { #first-steps }
0.46269995 docs/en/docs/tutorial/dependencies/classes-as-dependencies.md Use it { #use-it }
```