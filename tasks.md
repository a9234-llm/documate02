# DocuMate02 — RAG-ассистент по документации FastAPI
## Подробный план реализации (4 дня, по задачам)
 
> Как пользоваться: копируй формулировку задачи в GitHub Copilot Chat / inline-подсказки как контекст. После каждой задачи есть "Definition of Done" — сверяйся с ней, прежде чем идти дальше. Если что-то не сходится — приходи ко мне с кодом/ошибкой.
 
---
 
## ДЕНЬ 0 (за 1-2 часа до старта) — Настройка окружения
 
### Задача 0.1 — Создать репозиторий и структуру проекта
- Создать новый **отдельный** приватный/публичный репозиторий на GitHub (не форк и не копия старых проектов), например `documate-fastapi-rag`.
- Локально создать структуру:
```
documate/
├── flows/              # Prefect flows (ingestion)
├── src/
│   ├── ingestion/       # fetch, chunk, embed, index
│   ├── retrieval/       # dense, bm25, hybrid retrievers
│   ├── llm/             # prompts, rag_chain, groq_client
│   ├── eval/            # retrieval_eval.py, llm_eval.py, generate_qa.py
│   └── app/             # streamlit app + monitoring dashboard
├── data/                # локальный кэш документов (gitignore)
├── docker/              # Dockerfile(s)
├── docker-compose.yml
├── requirements.txt / pyproject.toml
├── .env.example
├── README.md
├── setup.md
├── usage.md
└── notebooks/           # опционально, для экспериментов
```
- **DoD:** репозиторий запушен, структура папок создана с `.gitkeep` в пустых, `.gitignore` включает `data/`, `.env`, `__pycache__`, `.venv`.
### Задача 0.2 — Зависимости и окружение
- Создать `.venv`, `requirements.txt` (или `pyproject.toml` через `uv`/`poetry` — версионирование зависимостей важно для "Reproducibility").
- Базовый набор пакетов: `prefect`, `qdrant-client`, `rank-bm25`, `sentence-transformers`, `groq`, `streamlit`, `psycopg2-binary` (или `sqlalchemy`), `pydantic`, `python-dotenv`, `pandas`, `tqdm`.
- **DoD:** `pip install -r requirements.txt` отрабатывает без ошибок в чистом venv.
### Задача 0.3 — API-ключи и конфиг
- Зарегистрироваться на [console.groq.com](https://console.groq.com), получить `GROQ_API_KEY`.
- Создать `.env.example` с плейсхолдерами: `GROQ_API_KEY=`, `QDRANT_URL=`, `QDRANT_PORT=`, `POSTGRES_*`.
- Создать `src/config.py`, читающий переменные через `pydantic-settings` или `python-dotenv`.
- **DoD:** `python -c "from src.config import settings; print(settings.groq_api_key[:4])"` работает.
### Задача 0.4 — Решить, что такое "чанк" в этом проекте
- Изучить структуру `https://github.com/tiangolo/fastapi/tree/master/docs/en/docs` — это markdown-файлы с заголовками `#`, `##`, кодовыми блоками.
- Решение: чанкать **по заголовкам второго уровня (`##`)** внутри каждого файла, сохраняя путь файла и заголовок как метаданные (пригодится для цитирования источника в UI).
- **DoD:** written decision записана в `docs/design_decisions.md` (2-3 предложения) — потребуется потом для README.
---
 
## ДЕНЬ 1 — Ingestion pipeline (Prefect) + индексация
 
### Задача 1.1 — Fetcher: скачать документацию
- В `src/ingestion/fetch.py`: функция, которая через GitHub API (`GET /repos/tiangolo/fastapi/contents/docs/en/docs`, рекурсивно) или через `git clone --depth 1` скачивает все `.md` файлы в `data/raw/`.
- Использовать GitHub API, а не git clone, если хочешь показать "работу с API" явно (можно и то, и другое — но не усложняй).
- **DoD:** после запуска в `data/raw/` лежит ~200+ md-файлов, повторяющих структуру репозитория.
### Задача 1.2 — Чанкер
- В `src/ingestion/chunk.py`: парсер markdown (можно `markdown-it-py` или простой regex по `^## `), который для каждого файла возвращает список чанков вида:
```python
{
  "id": "<file_path>__<chunk_index>",
  "text": "...",
  "source_file": "docs/en/docs/tutorial/dependencies.md",
  "heading": "Sub-dependencies",
  "url": "https://fastapi.tiangolo.com/tutorial/dependencies/"  # для UI-ссылок
}
```
- Обработать edge-case: файлы без `##` — оставить как один чанк.
- Отфильтровать слишком короткие чанки (< 50 символов) — это шум.
- **DoD:** unit-тест `tests/test_chunk.py`, проверяющий, что на тестовом md-файле получается ожидаемое число чанков.
### Задача 1.3 — Embedding-модель
- Использовать **локальную** модель `sentence-transformers/all-MiniLM-L6-v2` (бесплатно, без API, быстро). Groq не делает эмбеддинги — только LLM-инференс, это нормально и ожидаемо.
- В `src/ingestion/embed.py`: функция `embed_texts(texts: list[str]) -> list[list[float]]`, батчами по 32-64.
- **DoD:** на 5 тестовых строках возвращается список векторов размерности 384.
### Задача 1.4 — Qdrant: dense-индекс
- Поднять Qdrant локально (докер, см. Задачу 1.6) или временно через `qdrant-client` in-memory (`:memory:`) для разработки.
- В `src/ingestion/vector_store.py`: функция `upsert_chunks(chunks, embeddings)`, создающая коллекцию `fastapi_docs` (cosine distance, size=384) и загружающая point'ы с payload = метаданные чанка.
- **DoD:** после запуска `qdrant-client` показывает `collection.points_count == len(chunks)`.
### Задача 1.5 — BM25-индекс
- В `src/ingestion/bm25_store.py`: построить `rank_bm25.BM25Okapi` по токенизированным чанкам (простая токенизация: lowercase + split по non-alphanumeric).
- Сериализовать индекс + список chunk_id в pickle/json в `data/bm25_index.pkl`, чтобы retrieval-слой мог его грузить без пересчёта.
- **DoD:** `bm25.get_scores(query_tokens)` возвращает массив длиной = число чанков.
### Задача 1.6 — Docker для Qdrant (и Postgres заранее)
- В `docker-compose.yml` (начальная версия) добавить сервисы `qdrant` (image `qdrant/qdrant`) и `postgres` (image `postgres:16`) с volume для персистентности.
- **DoD:** `docker compose up qdrant postgres` — оба поднимаются, Qdrant UI доступен на `localhost:6333/dashboard`.
### Задача 1.7 — Собрать всё в Prefect flow
- В `flows/ingestion_flow.py`: определить `@flow` `ingest_fastapi_docs()`, состоящий из `@task`: `fetch_docs`, `chunk_docs`, `embed_chunks`, `upsert_to_qdrant`, `build_bm25_index`.
- Добавить логирование через `prefect.get_run_logger()` на каждом шаге (число файлов, чанков, точек).
- **DoD:** `python flows/ingestion_flow.py` (или `prefect deployment run`) выполняет весь пайплайн end-to-end и виден в Prefect UI (`prefect server start` → `localhost:4200`) с зелёными тасками.
### Задача 1.8 — Проверка результата
- Написать `scripts/sanity_check.py`: делает тестовый запрос в Qdrant (`search`) с эмбеддингом фразы "How do I use dependency injection?" и печатает топ-5 результатов.
- **DoD:** результаты релевантны на глаз (chunk про `Depends`/dependencies).
**Конец Дня 1 — контрольная точка:** ingestion работает от начала до конца через Prefect, данные в Qdrant и BM25-индексе, докер поднимает Qdrant+Postgres. Если что-то не готово — не переходи на День 2, лучше договорим здесь.