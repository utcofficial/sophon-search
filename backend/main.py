"""
=============================================================================
                    SEARCH ENGINE API SERVER (FASTAPI)
=============================================================================
Yeh file main entry point hai - FastAPI server start hota hai yahan se.
REST API endpoints provide karta hai frontend ke liye.

API Endpoints:
    - POST /api/search         : Search karna
    - GET  /api/documents/{id} : Specific document get karna
    - GET  /api/stats          : Index statistics
    - POST /api/index          : Documents index karna (admin)
    - GET  /health             : Health check

Architecture:
    - FastAPI for high performance async API
    - CORS enabled for frontend communication
    - Automatic API documentation at /docs
    - Request/Response validation via Pydantic
    
Production Ready Features:
    - Error handling with proper HTTP codes
    - Request logging
    - Rate limiting ready structure
    - Graceful shutdown
=============================================================================
"""

import os
import sys
import requests
from pathlib import Path
from contextlib import asynccontextmanager
from typing import List, Optional

# FastAPI imports
from fastapi import FastAPI, HTTPException, Query, BackgroundTasks, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from web_search import search_wikipedia, search_duckduckgo

# Ensure backend modules import ho sakein
backend_dir = Path(__file__).parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

# Local imports
from models import SearchQuery, SearchResponse, Document
from searcher import SearchEngine
from indexer import InvertedIndex
from crawler import crawl_documents
from config import CONFIG


# =============================================================================
# GLOBAL STATE MANAGEMENT
# =============================================================================

class AppState:
    """
    Application state manage karta hai.
    FastAPI lifespan events mein initialize aur cleanup hota hai.
    """
    def __init__(self):
        self.search_engine: Optional[SearchEngine] = None
        self.is_ready: bool = False
        self.startup_time: Optional[str] = None
    
    def initialize(self):
        """Search engine initialize karta hai."""
        print("🚀 Application state initialize ho rahi hai...")
        
        self.search_engine = SearchEngine()
        
        # Try to load existing index
        index_loaded = self.search_engine.load_index()
        
        if not index_loaded:
            print("⚠️  Existing index nahi mili. Naya index banega documents se.")
            # Auto-indexing enabled hai toh documents se bana lenge
            docs_dir = CONFIG.paths['DOCUMENTS_DIR']
            if docs_dir.exists() and any(docs_dir.iterdir()):
                print(f"   Auto-indexing shuru: {docs_dir}")
                documents = crawl_documents(str(docs_dir))
                if documents:
                    self.search_engine.build_index(documents)
                    self.search_engine.index.save()
                    print("   Auto-indexing complete!")
        
        self.is_ready = True
        from datetime import datetime
        self.startup_time = datetime.now().isoformat()
        
        print("✅ Application ready!")
    
    def cleanup(self):
        """Cleanup resources."""
        print("🛑 Application shutdown ho rahi hai...")
        self.is_ready = False


# Global state instance
app_state = AppState()



# =============================================================================
# FASTAPI LIFESPAN MANAGEMENT
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan context manager.
    Startup pe initialize, shutdown pe cleanup.
    """
    # Startup
    app_state.initialize()
    yield
    # Shutdown
    app_state.cleanup()


# =============================================================================
# FASTAPI APPLICATION CREATION
# =============================================================================

app = FastAPI(
    title="Search Engine API",
    description="""
    Ek poora search engine jo documents index karke unmein search karta hai.
    
    Features:
    - Full-text search with BM25 ranking
    - Real-time indexing
    - REST API for frontend integration
    
    Made with ❤️  in India
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS middleware - frontend ko allow karne ke liye
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Production mein specific domain dena chahiye
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# REQUEST/RESPONSE MODELS (API Specific)
# =============================================================================

class SearchRequest(BaseModel):
    """
    Search API ke liye request body.
    """
    query: str = Field(..., min_length=1, max_length=500, description="Search query")
    page: int = Field(default=1, ge=1, description="Page number")
    per_page: int = Field(default=10, ge=1, le=50, description="Results per page")
    
    class Config:
        json_schema_extra = {
            "example": {
                "query": "python tutorial",
                "page": 1,
                "per_page": 10
            }
        }


class IndexRequest(BaseModel):
    """
    Indexing API ke liye request body.
    """
    path: str = Field(..., description="Directory path to index")
    recursive: bool = Field(default=True, description="Crawl subdirectories")
    
    class Config:
        json_schema_extra = {
            "example": {
                "path": "./data/documents",
                "recursive": True
            }
        }


class HealthResponse(BaseModel):
    """
    Health check response.
    """
    status: str
    is_ready: bool
    startup_time: Optional[str]
    index_stats: Optional[dict]


class ErrorResponse(BaseModel):
    """
    Error response format.
    """
    error: str
    detail: Optional[str] = None


# =============================================================================
# API ENDPOINTS
# =============================================================================

@app.get("/", tags=["Root"])
async def root():
    """
    Root endpoint - API info return karta hai.
    """
    return {
        "message": "Sophon Search Engine mein aapka swagat hai!",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/api/web-search", tags=["Search"])
async def web_search(q: str = Query(..., min_length=1)):
    results = {
        'wikipedia': None,
        'web_results': []
    }
    
    wiki = search_wikipedia(q)
    if wiki:
        results['wikipedia'] = wiki
    
    web = search_duckduckgo(q)
    if web:
        results['web_results'] = web
    
    return results


@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check():
    """
    Health check endpoint - system status batata hai.
    
    Returns:
        Health status with index statistics
    """
    if not app_state.is_ready:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service abhi initialize ho raha hai..."
        )
    
    stats = app_state.search_engine.get_index_stats()
    
    return HealthResponse(
        status="healthy",
        is_ready=app_state.is_ready,
        startup_time=app_state.startup_time,
        index_stats=stats
    )


@app.post(
    "/api/search",
    response_model=SearchResponse,
    tags=["Search"],
    responses={
        200: {"description": "Search successful"},
        400: {"model": ErrorResponse, "description": "Invalid query"},
        503: {"model": ErrorResponse, "description": "Service not ready"}
    }
)
async def search_documents(request: SearchRequest):
    """
    **Main Search Endpoint**
    
    Documents mein search karta hai aur ranked results return karta hai.
    
    Algorithm:
    1. Query ko tokenize karta hai
    2. Boolean AND se candidates retrieve karta hai
    3. BM25 scoring se rank karta hai
    4. Paginated results return karta hai
    
    Returns:
        SearchResponse with results, metadata, aur timing info
    """
    if not app_state.is_ready:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Search engine abhi ready nahi hai"
        )
    
    try:
        # SearchQuery object banate hain
        search_query = SearchQuery(
            query=request.query,
            page=request.page,
            per_page=request.per_page
        )
        
        # Search execute karte hain
        response = app_state.search_engine.search(search_query)
        
        return response
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search mein error: {str(e)}"
        )


@app.get(
    "/api/documents/{doc_id}",
    tags=["Documents"],
    responses={
        200: {"description": "Document found"},
        404: {"description": "Document not found"}
    }
)
async def get_document(doc_id: str):
    """
    Specific document ID se full document retrieve karta hai.
    
    Args:
        doc_id: URL-encoded document ID (usually file path)
        
    Returns:
        Document object with full content
    """
    if not app_state.is_ready:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service not ready"
        )
    
    # URL decode karte hain doc_id ko
    import urllib.parse
    decoded_id = urllib.parse.unquote(doc_id)
    
    document = app_state.search_engine.get_document_by_id(decoded_id)
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document nahi mila: {decoded_id}"
        )
    
    return document


@app.get("/api/stats", tags=["System"])
async def get_statistics():
    """
    Index ki detailed statistics return karta hai.
    
    Returns:
        Statistics about documents, terms, aur index size
    """
    if not app_state.is_ready:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service not ready"
        )
    
    return app_state.search_engine.get_index_stats()


@app.post(
    "/api/index",
    tags=["Admin"],
    responses={
        200: {"description": "Indexing started/complete"},
        202: {"description": "Indexing in progress (background)"},
        400: {"description": "Invalid path"}
    }
)
async def index_documents(
    request: IndexRequest,
    background_tasks: BackgroundTasks
):
    """
    **Admin Endpoint** - Documents ko index karta hai.
    
    Naya ya updated documents ko index mein add karta hai.
    Agar documents zyada hain toh background mein process hota hai.
    
    Args:
        request: IndexRequest with path and options
        
    Returns:
        Status message with indexing details
    """
    if not app_state.is_ready:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service not ready"
        )
    
    path = Path(request.path)
    
    if not path.exists():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Path exist nahi karti: {request.path}"
        )
    
    # Check karte hain ki kitni files hain
    if path.is_file():
        doc_count = 1
    else:
        # Estimate count
        doc_count = len(list(path.glob('**/*.txt'))) + \
                   len(list(path.glob('**/*.md')))
    
    # Agar zyada documents hain toh background mein karenge
    if doc_count > 10:
        background_tasks.add_task(
            _background_indexing,
            str(path),
            request.recursive
        )
        
        return {
            "status": "indexing_started",
            "message": f"Background indexing shuru ho gayi hai ({doc_count} estimated files)",
            "path": str(path)
        }
    else:
        # Direct indexing
        try:
            documents = crawl_documents(str(path), request.recursive)
            
            if documents:
                # Existing index mein add karte hain
                for doc in documents:
                    app_state.search_engine.index.add_document(doc)
                
                # Save karte hain
                app_state.search_engine.index.save()
                
                return {
                    "status": "indexing_complete",
                    "message": f"{len(documents)} documents successfully indexed",
                    "documents_indexed": len(documents)
                }
            else:
                return {
                    "status": "no_documents",
                    "message": "Koi documents nahi mile indexing ke liye"
                }
                
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Indexing mein error: {str(e)}"
            )


def _background_indexing(path: str, recursive: bool):
    """
    Background task jo heavy indexing handle karta hai.
    
    Args:
        path: Directory ya file path
        recursive: Subdirectories include karni hain?
    """
    print(f"[BACKGROUND] Indexing shuru: {path}")
    
    try:
        documents = crawl_documents(path, recursive)
        
        for doc in documents:
            app_state.search_engine.index.add_document(doc)
        
        app_state.search_engine.index.save()
        
        print(f"[BACKGROUND] Indexing complete: {len(documents)} documents")
        
    except Exception as e:
        print(f"[BACKGROUND ERROR] {e}")


@app.get("/api/suggest", tags=["Search"])
async def get_suggestions(q: str = Query(..., min_length=1)):
    suggestions = []
    
    # 1. Local index se - sahi tarike se access karo
    try:
        if app_state.is_ready and app_state.search_engine:
            local_terms = [
                term for term in app_state.search_engine.index.index.keys() 
                if term.startswith(q.lower())
            ][:2]
            suggestions.extend(local_terms)
    except Exception as e:
        print(f"Local suggest error: {e}")
    
    # 2. DuckDuckGo Suggest API
    try:
        duck_url = f"https://duckduckgo.com/ac/?q={q}&type=list"
        response = requests.get(
            duck_url, 
            timeout=3, 
            headers={'User-Agent': 'Mozilla/5.0'}
        )
        if response.status_code == 200:
            data = response.json()
            if len(data) > 1 and isinstance(data[1], list):
                duck_suggestions = data[1][:4]
                suggestions.extend(duck_suggestions)
    except Exception as e:
        print(f"DuckDuckGo suggest error: {e}")
    
    # 3. Wikipedia search suggestions
    try:
        wiki_url = f"https://en.wikipedia.org/w/api.php?action=opensearch&search={q}&limit=3&format=json"
        response = requests.get(wiki_url, timeout=3)
        if response.status_code == 200:
            data = response.json()
            if len(data) > 1 and isinstance(data[1], list):
                wiki_suggestions = data[1][:3]
                suggestions.extend(wiki_suggestions)
    except Exception as e:
        print(f"Wikipedia suggest error: {e}")
    
    # Remove duplicates
    seen = set()
    unique = []
    for s in suggestions:
        lower_s = s.lower()
        if lower_s not in seen:
            seen.add(lower_s)
            unique.append(s)
        if len(unique) >= 6:
            break
    
    return {"suggestions": unique}


# =============================================================================
# ERROR HANDLERS
# =============================================================================

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """
    Global exception handler - unexpected errors ko gracefully handle karta hai.
    """
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal server error",
            "detail": str(exc) if CONFIG.DEBUG else "Kuch galat ho gaya"
        }
    )


# =============================================================================
# STATIC FILES (OPTIONAL - for serving frontend build)
# =============================================================================

# Agar frontend build folder hai toh serve karenge
frontend_build_dir = CONFIG.ROOT_DIR / "frontend" / "dist"
if frontend_build_dir.exists():
    app.mount("/", StaticFiles(directory=str(frontend_build_dir), html=True), name="static")
    print(f"📁 Static files serve ho rahi hain: {frontend_build_dir}")


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    
    print("=" * 60)
    print("🔍 DESI SEARCH ENGINE SERVER")
    print("=" * 60)
    
    # Server configuration
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", 8000))
    reload = os.getenv("RELOAD", "false").lower() == "true"
    
    print(f"🌐 Server start ho raha hai: http://{host}:{port}")
    print(f"📚 API Documentation: http://{host}:{port}/docs")
    print("=" * 60)
    
    # Uvicorn server start karte hain
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info"
    )