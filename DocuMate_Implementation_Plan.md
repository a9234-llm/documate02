# DocuMate — RAG-ассистент по документации FastAPI
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

---

## ДЕНЬ 2 — Retrieval flow + Retrieval evaluation

### Задача 2.1 — Dense retriever
- В `src/retrieval/dense.py`: функция `dense_search(query: str, top_k=5) -> list[chunk]`, эмбеддит запрос той же моделью и ищет в Qdrant.
- **DoD:** возвращает список чанков с score.

### Задача 2.2 — BM25 retriever
- В `src/retrieval/bm25.py`: функция `bm25_search(query: str, top_k=5) -> list[chunk]`, грузит сохранённый индекс, токенизирует запрос, возвращает top-k по score.
- **DoD:** аналогично, релевантные чанки по ключевым словам (например, точное совпадение `BackgroundTasks`).

### Задача 2.3 — Hybrid retriever (best practice #1)
- В `src/retrieval/hybrid.py`: реализовать **Reciprocal Rank Fusion (RRF)**:
```
score(doc) = sum(1 / (k + rank_i(doc)))  для каждого метода, k=60 (стандарт)
```
- Функция `hybrid_search(query, top_k=5)`, объединяющая ранги dense и bm25 через RRF.
- **DoD:** возвращает разумный top-5, отличный от чисто dense/bm25 в спорных случаях.

### Задача 2.4 — Генерация eval-датасета (синтетический QA)
- В `src/eval/generate_qa.py`: для случайной выборки ~100-150 чанков (не всех — для эффективности) отправить в Groq промпт вида:
> "Ты помогаешь создать тестовый датасет для системы вопрос-ответ по документации FastAPI. На основе следующего фрагмента документации сгенерируй ОДИН конкретный вопрос, ответ на который содержится в этом фрагменте. Верни только вопрос, без преамбулы. Фрагмент: {chunk_text}"
- Сохранить результат в `data/eval_qa.jsonl`: `{"chunk_id": ..., "question": ..., "source_file": ...}`.
- **DoD:** файл с ~100-150 парами (question, ground_truth_chunk_id), просмотрен вручную на 10-15 примерах — вопросы адекватны.

### Задача 2.5 — Метрики retrieval evaluation
- В `src/eval/retrieval_eval.py`: реализовать `hit_rate@k` и `MRR` (mean reciprocal rank) — для каждого вопроса из eval-датасета проверяем, попал ли `ground_truth_chunk_id` в top-k результатов ретривера, и на какой позиции.
- **DoD:** функция `evaluate_retriever(retriever_fn, eval_data, k=5) -> {"hit_rate": ..., "mrr": ...}`.

### Задача 2.6 — Прогнать сравнение трёх подходов
- Скрипт `scripts/run_retrieval_eval.py`: прогоняет `dense_search`, `bm25_search`, `hybrid_search` через `evaluate_retriever`, печатает таблицу.
- Пример ожидаемого вывода:
```
Method    | Hit Rate@5 | MRR
dense     | 0.78       | 0.62
bm25      | 0.71       | 0.55
hybrid    | 0.85       | 0.69   <- winner
```
- Зафиксировать результат (таблицу) в `docs/retrieval_evaluation_results.md` — это прямое доказательство для пункта "Retrieval evaluation" в README.
- **DoD:** таблица с реальными числами, явно указан выбранный метод по умолчанию для продакшена (обычно hybrid).

### Задача 2.7 (опционально, если есть время) — Reranking (best practice #2)
- Добавить cross-encoder reranker (`cross-encoder/ms-marco-MiniLM-L-6-v2` через `sentence-transformers`), который переранжирует top-20 от hybrid retriever до top-5.
- Добавить в сравнение как 4-й метод `hybrid+rerank`.
- **DoD:** таблица дополнена строкой, видно, улучшил ли rerank метрики.

**Конец Дня 2 — контрольная точка:** есть 3 (или 4) реализованных retriever'а, метрики посчитаны и задокументированы, выбран победитель.

---

## ДЕНЬ 3 — RAG-flow, LLM evaluation, интерфейс

### Задача 3.1 — Groq client
- В `src/llm/groq_client.py`: обёртка над `groq.Groq()` клиентом, функция `generate(prompt: str, model="llama-3.3-70b-versatile", temperature=0.2) -> str`.
- **DoD:** тестовый вызов возвращает текст без ошибок.

### Задача 3.2 — Промпт-шаблоны (минимум 2-3 варианта)
- В `src/llm/prompts.py` определить несколько вариантов системного промпта:
  1. **baseline** — просто "ответь на вопрос, используя контекст ниже".
  2. **expert_role** — "Ты — опытный Python/FastAPI-разработчик, объясняешь новичку. Используй только контекст. Если ответа нет в контексте — скажи, что не знаешь."
  3. **structured** — вариант, требующий формат ответа с примером кода, если применимо, + ссылкой на источник.
- **DoD:** три функции/константы, каждая принимает `(question, context_chunks) -> full_prompt`.

### Задача 3.3 — RAG chain
- В `src/llm/rag_chain.py`: функция `answer_question(question, retriever=hybrid_search, prompt_variant="expert_role") -> {"answer": ..., "sources": [...]}`.
- Флоу: retrieve top-5 → собрать контекст (с указанием source_file/heading) → построить промпт → вызвать Groq → вернуть ответ + список источников.
- **DoD:** ручной тест на 5 вопросах — ответы разумные, источники релевантны.

### Задача 3.4 — LLM evaluation (LLM-as-judge)
- В `src/eval/llm_eval.py`: взять 30-50 вопросов из `data/eval_qa.jsonl` (можно переиспользовать), для каждого сгенерировать ответ **тремя вариантами промпта**.
- Судья: отдельный вызов Groq с промптом вида:
> "Оцени качество ответа на вопрос по шкале 1-5 по критериям: релевантность, точность (соответствие контексту), полнота. Вопрос: {q}. Контекст: {context}. Ответ: {answer}. Верни только JSON: {\"relevance\": X, \"accuracy\": X, \"completeness\": X}"
- Усреднить оценки по каждому варианту промпта.
- **DoD:** `docs/llm_evaluation_results.md` с таблицей вида:
```
Prompt variant | Avg Relevance | Avg Accuracy | Avg Completeness
baseline       | 3.8           | 3.5          | 3.2
expert_role    | 4.3           | 4.1          | 4.0   <- winner
structured     | 4.1           | 4.4          | 3.9
```
- Зафиксировать выбор победителя как дефолтного промпта в `rag_chain.py`.

### Задача 3.5 — Postgres-схема для логов
- В `src/app/db.py`: SQL-таблица `interactions`:
```sql
CREATE TABLE interactions (
  id SERIAL PRIMARY KEY,
  timestamp TIMESTAMP DEFAULT now(),
  question TEXT,
  answer TEXT,
  retrieval_method TEXT,
  prompt_variant TEXT,
  response_time_ms INT,
  sources JSONB,
  feedback SMALLINT  -- NULL, 1 (up), -1 (down)
);
```
- Функции `log_interaction(...)` и `update_feedback(interaction_id, feedback)`.
- **DoD:** запись и чтение из локального Postgres (через docker-compose) работает.

### Задача 3.6 — Streamlit-интерфейс
- В `src/app/streamlit_app.py`:
  - Поле ввода вопроса, кнопка "Спросить".
  - Вывод ответа + список источников (кликабельные ссылки на fastapi.tiangolo.com).
  - Под ответом — кнопки 👍/👎, вызывающие `update_feedback`.
  - Замер времени ответа (для лога и для UI, "ответ за X.X сек").
- **DoD:** `streamlit run src/app/streamlit_app.py` — рабочий чат, вопрос-ответ, фидбек пишется в Postgres (проверить через `psql`/DBeaver).

**Конец Дня 3 — контрольная точка:** есть работающий end-to-end продукт (вопрос в UI → ответ с источниками), фидбек логируется, LLM-evaluation задокументирован.

---

## ДЕНЬ 4 — Мониторинг, контейнеризация, документация, (опционально агент)

### Задача 4.1 — Дашборд мониторинга (5+ графиков)
- Вариант A (проще): вторая страница в Streamlit (`pages/dashboard.py`) с графиками через `plotly`/`matplotlib`, читающая из Postgres.
- Вариант B (более "по-взрослому", доп. балл за впечатление, не обязателен): Grafana поверх Postgres datasource.
- Минимум 5 графиков, например:
  1. Количество запросов по дням (time series).
  2. Распределение response_time_ms (гистограмма).
  3. Доля 👍 vs 👎 (pie/bar).
  4. Топ-10 самых частых вопросов/тем (bar chart, можно кластеризовать по source_file).
  5. Динамика среднего фидбека по дням (line chart).
  6. (опц.) Распределение по retrieval_method / prompt_variant, если тестируешь разные варианты в проде.
- **DoD:** дашборд открывается, показывает реальные данные (накопи 20-30 тестовых запросов заранее вручную/скриптом для наглядности).

### Задача 4.2 — Dockerfile для приложения
- В `docker/Dockerfile`: python:3.11-slim база, установка зависимостей, копирование кода, `CMD ["streamlit", "run", "src/app/streamlit_app.py", "--server.address=0.0.0.0"]`.
- **DoD:** `docker build` проходит без ошибок.

### Задача 4.3 — Финальный docker-compose.yml
- Сервисы: `app` (Streamlit), `qdrant`, `postgres`, (опц. `grafana`), `ingestion` (можно как одноразовый job/profile, либо отдельная инструкция "запустить перед стартом").
- Проверить, что все переменные окружения пробрасываются из `.env`.
- **DoD:** `docker compose up --build` с нуля (на чистой машине/новом volume) поднимает всё, UI доступен на `localhost:8501`, ingestion можно прогнать командой `docker compose run ingestion`.

### Задача 4.4 — README.md
Структура (важно для "Problem description" и общей документации):
1. **Проблема** — 2-3 абзаца: зачем нужен ассистент по FastAPI-докам, для кого (разработчики, изучающие FastAPI).
2. **Данные** — откуда, как ингестятся.
3. **Архитектура** — диаграмма (можно текстом/ASCII или картинкой) + описание технологий и **зачем каждая** (объяснить Prefect, Qdrant, Groq, RRF hybrid search для тех, кто не проходил курс).
4. **Как это оценивается** — явно перечисли критерии оценки курса и укажи, в каком файле/разделе смотреть доказательства (например: "Retrieval evaluation → см. `docs/retrieval_evaluation_results.md`").
5. **Как запустить** — ссылка на `setup.md`.
6. **Как пользоваться** — ссылка на `usage.md`, + 2-3 скриншота UI и dashboard.
7. **Structure** — дерево папок с пояснениями.
- **DoD:** прочитать README глазами человека, который никогда не слышал про курс — понятно ли всё без домыслов?

### Задача 4.5 — setup.md и usage.md
- `setup.md`: пошагово — clone → `.env` заполнение (какие ключи нужны и откуда взять) → `docker compose up` → первый запуск ingestion → открыть UI.
- `usage.md`: примеры вопросов и ответов (скриншоты), объяснение источников/ссылок в ответе, как оставить фидбек, как посмотреть дашборд.
- **DoD:** оба файла существуют, содержат скриншоты (сделать через любой скриншотер, положить в `docs/screenshots/`).

### Задача 4.6 — Финальный чек-лист по критериям оценки
Пройтись по каждому пункту и явно вписать в `docs/evaluation_checklist.md`, где что искать:
- [ ] Problem description → README §1
- [ ] Retrieval flow (KB + LLM) → `src/llm/rag_chain.py`
- [ ] Retrieval evaluation (сравнение подходов) → `docs/retrieval_evaluation_results.md`
- [ ] LLM evaluation (сравнение промптов) → `docs/llm_evaluation_results.md`
- [ ] Interface (UI) → Streamlit, `src/app/streamlit_app.py`
- [ ] Ingestion pipeline (автоматизированный) → Prefect flow
- [ ] Monitoring (фидбек + дашборд 5+ графиков) → §4.1
- [ ] Containerization (docker-compose) → §4.3
- [ ] Reproducibility → `requirements.txt`/`pyproject.toml` версии зафиксированы, `.env.example`, setup.md
- [ ] Best practices: hybrid search ✅ (и rerank, если сделал в 2.7)
- **DoD:** ни один пункт не остался без ссылки на конкретный файл/раздел.

### Задача 4.7 (стретч, если есть запас времени) — Добавить агента
- Идея: tool `check_latest_fastapi_version()`, дергающий PyPI JSON API (`https://pypi.org/pypi/fastapi/json`), чтобы ассистент мог сказать "актуальный релиз FastAPI — X.Y.Z, эта документация может не отражать последние изменения" при релевантных вопросах.
- Реализация: простой function-calling через Groq (проверить, какие модели на Groq поддерживают tool use — на момент реализации свериться в доке Groq) или ручной роутинг (LLM решает вызвать tool через structured output, ты сам делаешь вызов и подставляешь результат обратно в промпт).
- **DoD:** отдельный флаг/режим в UI "agent mode", видно в чате, что был вызван tool (например, "🔧 Проверил актуальную версию FastAPI...").
- Это НЕ обязательно для полного балла по обязательным пунктам — делай, только если основное уже готово и стабильно.

---

## Общие правила по ходу работы

- После каждой **контрольной точки** (конец дня) — присылай мне: что сделано, что не получилось, любые ошибки/логи. Сверим с чеклистом.
- Если Copilot предлагает решение, которое расходится с этим планом (например, другую БД или другой способ чанкинга) — не принимай молча, спроси меня, не потеряется ли балл или логика пайплайна.
- Коммить после каждой завершённой задачи (не в конце дня одним огромным коммитом) — это тоже часть "Reproducibility"/аккуратности проекта.
