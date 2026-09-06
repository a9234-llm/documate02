Вот пошаговые инструкции — по одной задаче за раз, как ты любишь. Сначала быстрая самопроверка (не для Copilot, просто в терминале), потом уже промпты для Copilot.

## Шаг 0 — проверь сам, прежде чем чинить

```bash
ls src/ingestion/
ls data/
grep -n "bm25" flows/ingestion_flow.py
```

Три варианта результата:
- **Файла `bm25_store.py` нет вообще** → используй Промпт A ниже.
- **Файл есть, но в `ingestion_flow.py` нет упоминания bm25** → используй только Промпт B.
- **Всё есть, но `data/bm25_index.pkl` не создался** → используй только Промпт C (диагностика).

Дальше — сами промпты для Copilot Chat (копируй целиком блок, включая заголовок задачи — так Copilot лучше понимает контекст).

---

## Промпт A — создать BM25-индекс модуль

```
Задача: реализовать построение BM25-индекса для проекта DocuMate (RAG по документации FastAPI).

Контекст: у меня уже есть чанки документов в формате списка словарей:
{
  "id": "<file_path>__<chunk_index>",
  "text": "...",
  "source_file": "...",
  "heading": "..."
}
Эти чанки создаются в src/ingestion/chunk.py.

Создай файл src/ingestion/bm25_store.py со следующим:
1. Функцию build_bm25_index(chunks: list[dict]) -> None:
   - токенизирует поле "text" каждого чанка (lowercase + split по не-буквенно-цифровым символам, простой regex, без внешних токенизаторов)
   - строит BM25Okapi из библиотеки rank_bm25 на токенизированных текстах
   - сохраняет в data/bm25_index.pkl через pickle СЛОВАРЬ вида:
     {"bm25": <объект BM25Okapi>, "chunk_ids": [список id в том же порядке, что тексты]}
   - создаёт директорию data/ если её нет
2. Функцию load_bm25_index() -> dict:
   - загружает и возвращает тот же словарь из data/bm25_index.pkl
   - кидает понятную ошибку (FileNotFoundError с текстом), если файл не найден

Используй logging через стандартный модуль logging, без print.
Добавь docstring к обеим функциям.
```

**DoD после этого шага:** файл `src/ingestion/bm25_store.py` существует, импортируется без ошибок (`python -c "from src.ingestion.bm25_store import build_bm25_index, load_bm25_index"`).

---

## Промпт B — подключить BM25-таск в Prefect flow

```
Задача: добавить пятый таск в существующий Prefect flow ingestion pipeline.

Контекст: в flows/ingestion_flow.py уже есть flow ingest_fastapi_docs() с тасками
fetch_task -> chunk_task -> embed_task -> index_task.
Нужно добавить ещё один @task build_bm25_task, который вызывается ПОСЛЕ chunk_task
(BM25 не требует эмбеддингов, только текст чанков) и может выполняться параллельно
с embed_task/index_task, либо последовательно — не критично.

Изменения:
1. Импортируй build_bm25_index из src.ingestion.bm25_store
2. Создай @task build_bm25_task(chunks) -> None:
   - вызывает build_bm25_index(chunks)
   - логирует через get_run_logger(): "Built BM25 index for {len(chunks)} chunks"
3. Вызови build_bm25_task(chunks) внутри flow ingest_fastapi_docs(), передавая туда
   результат chunk_task (тот же список chunks, что идёт в embed_task)
4. Не меняй существующие таски fetch_task/chunk_task/embed_task/index_task —
   только добавь новый вызов.
```

**DoD после этого шага:** в `flows/ingestion_flow.py` виден вызов `build_bm25_task`, и при `grep -n "build_bm25" flows/ingestion_flow.py` есть минимум 2 совпадения (определение таска + вызов).

---

## Промпт C — диагностика, если файл не создаётся

```
Задача: у меня есть src/ingestion/bm25_store.py с функцией build_bm25_index(chunks),
она вызывается из flows/ingestion_flow.py, но после запуска python flows/ingestion_flow.py
файл data/bm25_index.pkl не появляется.

Проверь и почини:
1. Правильно ли резолвится путь "data/bm25_index.pkl" относительно текущей рабочей
   директории (используй pathlib и Path(__file__).resolve().parent для абсолютного пути,
   а не относительный от cwd)
2. Действительно ли build_bm25_task вызывается внутри flow, а не только определён
3. Нет ли silent exception — оберни тело таска в try/except с логированием полного
   traceback через logger.exception(), если сейчас исключение проглатывается
```

---

## Финальная проверка (после A+B, или после C)

Прогони заново:

```bash
python flows/ingestion_flow.py
```

В логе должна появиться строка вида `Task run 'build_bm25_task-XXX' - Built BM25 index for 925 chunks`.

Потом проверь руками, что индекс реально работает:

```bash
python -c "
from src.ingestion.bm25_store import load_bm25_index
data = load_bm25_index()
print('chunks in index:', len(data['chunk_ids']))
tokens = 'how do i use dependency injection'.split()
scores = data['bm25'].get_scores(tokens)
print('scores length:', len(scores))
print('max score:', max(scores))
"
```

**DoD:** `chunks in index` == 925 (или сколько у тебя чанков сейчас), `scores length` совпадает, `max score` заметно больше нуля (не все нули — иначе токенизация где-то сломана).

Как только это пройдёт — присылай мне вывод, и переходим к Дню 2 (dense/BM25/hybrid retriever + retrieval evaluation).