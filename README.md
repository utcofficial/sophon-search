# Sophon Search Engine

A high-performance, full-text search engine built with Python (FastAPI) and React. Features real-time indexing, BM25 ranking, autocomplete suggestions, and a modern dark-themed UI.

---

## Architecture

```
┌─────────────┐      HTTP/REST       ┌─────────────┐
│   React     │ ◄──────────────────► │   FastAPI   │
│  Frontend   │   Port: 8000         │   Backend   │
│  Port: 5173 │                      │             │
└─────────────┘                      └──────┬──────┘
                                            │
                                   ┌───────┴───────┐
                                   │  Whoosh Index │
                                   │  BM25 Ranking │
                                   └───────────────┘
```

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | React 18, Vite, CSS Modules |
| Backend | Python 3.11, FastAPI, Uvicorn |
| Search | Whoosh (BM25 + TF-IDF) |
| Deployment | Docker-ready, CORS enabled |

---

## Features

- **Full-text search** with BM25 relevance scoring  
- **Real-time indexing** of text documents  
- **Autocomplete suggestions** with fuzzy matching  
- **Skeleton loading** with randomized delays (2-4s)  
- **Responsive dark UI** with animated gradients  
- **Sticky header** with gradient text effects  
- **Sticky footer** with animated border  

---

## Quick Start

### Prerequisites

- Python 3.11+  
- Node.js 18+  
- 2GB RAM minimum  

---

## Backend Setup

```bash
cd backend

pip install -r requirements.txt
python main.py


#virtual environment
python -m venv venv
# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

Server runs at:
```
http://127.0.0.1:8000
```

---

## Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Client runs at:
```
http://localhost:5173
```

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/search` | Full-text search with BM25 ranking |
| GET | `/api/suggest?q={query}` | Autocomplete suggestions |
| GET | `/health` | Health check |

---

## Search Request

```json
POST /api/search
{
  "query": "machine learning",
  "page": 1,
  "per_page": 10
}
```

---

## Search Response

```json
{
  "results": [...],
  "total_results": 42,
  "search_time_ms": 15.2,
  "page": 1,
  "per_page": 10
}
```

---

## Project Structure

```plaintext
search-engine/
├── backend/
│   ├── main.py
│   ├── searcher.py
│   ├── indexer.py
│   ├── crawler.py
│   ├── models.py
│   └── storage/
│       └── index.json
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── components/
│   │   │   ├── Search/
│   │   │   ├── Results/
│   │   │   ├── ResultCard/
│   │   │   └── Footer/
│   │   └── api/
│   │       └── api.js
│   └── package.json
└── data/documents/
```

---

## Configuration

### Backend (`backend/config.py`)

```python
INDEX_DIR = "storage"
DOCUMENTS_DIR = "../data/documents"
MAX_RESULTS = 50
SUGGESTION_LIMIT = 5
```

### Frontend (`frontend/src/api/api.js`)

```javascript
const API_URL = "http://127.0.0.1:8000"
```

---

## Deployment

### Docker (Optional)

```bash
docker build -t sophon-search .
docker run -p 8000:8000 -p 5173:5173 sophon-search
```

### Production Build

```bash
cd frontend
npm run build

# Serve static files via FastAPI or nginx
```

---

## Performance

- Indexing: ~1000 docs/sec  
- Search latency: <20ms (cached)  
- Supports 10k+ documents  
- BM25 ranking with field boosts  

---

## License

MIT License. See LICENSE file.

---

## Authors

Sambhav Dwivedi - [sambhavdwivedi.in](https://sambhavdwivedi.in)  
United Tech Community - [unitedtechcommunity.in](https://unitedtechcommunity.in)

Built with ❤️ using Python and React.