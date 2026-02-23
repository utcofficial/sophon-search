"""
=============================================================================
                    DATA MODELS & SCHEMAS MODULE
=============================================================================
Yeh file saari data structures define karti hai jo search engine use karega.
Pydantic models ka use kar rahe hain jo automatic validation provide karte hain.

Design Philosophy:
    - Type safety maintain karna zaroori hai
    - JSON serialization/deserialization smooth hona chahiye
    - Models extensible hone chahiye future features ke liye
=============================================================================
"""

from datetime import datetime
from typing import List, Dict, Optional, Any, Set
from pydantic import BaseModel, Field, field_validator
from enum import Enum
import hashlib
import json


class DocumentType(str, Enum):
    """
    Document ke types define kar rahe hain.
    Future mein PDF, HTML, etc. add kar sakte hain.
    """
    TEXT = "text"
    MARKDOWN = "markdown"
    JSON = "json"
    HTML = "html"
    PDF = "pdf"  # Future ke liye placeholder


class IndexEntry(BaseModel):
    """
    Inverted Index ka ek entry represent karta hai.
    Har word ke liye kaunse documents mein hai aur kitni baar hai.
    
    Example:
        word: "python"
        postings: {
            "doc1.txt": {"frequency": 5, "positions": [10, 25, 30, 45, 60]},
            "doc2.txt": {"frequency": 2, "positions": [5, 15]}
        }
    """
    word: str = Field(..., description="Index kiya gaya word")
    
    # Postings list: {doc_id: {frequency: int, positions: List[int]}}
    postings: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict,
        description="Kaunse documents mein hai aur metadata"
    )
    
    # Document frequency: kitne unique docs mein ye word hai
    doc_frequency: int = Field(default=0, description="Document frequency")
    
    # Inverse document frequency (TF-IDF ke liye)
    idf_score: float = Field(default=0.0, description="IDF score")
    
    def add_posting(self, doc_id: str, position: int, frequency: int = 1):
        """
        Naya posting add karta hai ya existing ko update karta hai.
        
        Args:
            doc_id: Document ka unique identifier (filename)
            position: Word ka position document mein (0-indexed)
            frequency: Kitni baar word aaya hai
        """
        if doc_id not in self.postings:
            self.postings[doc_id] = {
                'frequency': 0,
                'positions': []
            }
        
        self.postings[doc_id]['frequency'] += frequency
        self.postings[doc_id]['positions'].append(position)
        self.doc_frequency = len(self.postings)
    
    model_config = {
        "extra": "forbid"
    }


class Document(BaseModel):
    """
    Ek document ko represent karta hai jo index hoga.
    Saari metadata aur content yahan store hoga.
    """
    # Unique document ID (filename se generate hoga)
    doc_id: str = Field(..., description="Unique document identifier")
    
    # Original file path
    file_path: str = Field(..., description="Document ka original path")
    
    # Document type
    doc_type: DocumentType = Field(default=DocumentType.TEXT)
    
    # Raw content
    content: str = Field(default="", description="Document ka raw text")
    
    # Preprocessed content (tokenized, cleaned)
    tokens: List[str] = Field(default_factory=list, description="Tokenized words")
    
    # Document ka size bytes mein
    file_size: int = Field(default=0, description="File size in bytes")
    
    # Metadata
    title: Optional[str] = Field(default=None, description="Document title")
    author: Optional[str] = Field(default=None, description="Document author")
    created_at: datetime = Field(default_factory=datetime.now)
    modified_at: datetime = Field(default_factory=datetime.now)
    indexed_at: Optional[datetime] = Field(default=None)
    
    # Document statistics
    word_count: int = Field(default=0, description="Total words in document")
    unique_words: int = Field(default=0, description="Unique words count")
    
    # Content hash for change detection
    content_hash: Optional[str] = Field(default=None, description="MD5 hash of content")
    
    def compute_hash(self) -> str:
        """
        Content ka MD5 hash calculate karta hai.
        Isse pata chalta hai ki document change hua hai ya nahi.
        """
        self.content_hash = hashlib.md5(self.content.encode('utf-8')).hexdigest()
        return self.content_hash
    
    def extract_title(self) -> str:
        """
        Document se title extract karne ki koshish karta hai.
        Pehli line ko title maan sakte hain agar chhoti ho.
        """
        lines = self.content.strip().split('\n')
        if lines and len(lines[0]) < 100:  # 100 chars se chhota ho toh title hai
            self.title = lines[0].strip()
        else:
            self.title = self.doc_id  # Fallback to filename
        return self.title
    
    def update_stats(self):
        """
        Document ki statistics update karta hai.
        """
        self.word_count = len(self.tokens)
        self.unique_words = len(set(self.tokens))
    
    model_config = {
        "json_encoders": {
            datetime: lambda v: v.isoformat()
        }
    }


class SearchResult(BaseModel):
    """
    Ek search result ko represent karta hai.
    User ko dikhane ke liye saari information yahan hogi.
    """
    # Document reference
    doc_id: str = Field(..., description="Document ID")
    title: str = Field(..., description="Document title")
    
    # Relevance score (0.0 to 1.0)
    score: float = Field(..., description="Relevance score")
    
    # Matching details
    matched_terms: List[str] = Field(
        default_factory=list, 
        description="Kaunse query terms match hue"
    )
    
    # Snippet generation ke liye
    snippet: str = Field(default="", description="Content snippet with highlights")
    
    # Content field for snippet generation - IMPORTANT FIX!
    content: Optional[str] = Field(default=None, description="Document content for snippet generation")
    
    # Match positions for highlighting
    highlight_positions: List[tuple] = Field(
        default_factory=list,
        description="Start, end positions for highlighting"
    )
    
    # Document metadata
    file_path: str = Field(..., description="Full file path")
    file_size: int = Field(default=0)
    modified_at: Optional[datetime] = Field(default=None)
    
    # BM25 specific scores (debugging ke liye)
    tf_score: float = Field(default=0.0, description="Term frequency component")
    idf_score: float = Field(default=0.0, description="IDF component")
    length_norm: float = Field(default=0.0, description="Length normalization")
    
    def generate_snippet(self, query_terms: List[str], snippet_length: int = 150):
        """
        Query terms ke around ek relevant snippet generate karta hai.
        
        Args:
            query_terms: Query mein aaye words
            snippet_length: Kitne characters ka snippet chahiye
        """
        if not self.content:
            self.snippet = "No content available"
            return
        
        content_lower = self.content.lower()
        best_pos = 0
        max_matches = 0
        
        # Sabse zyada matches wala section dhoondh rahe hain
        for i in range(0, len(content_lower) - snippet_length, 10):
            window = content_lower[i:i + snippet_length]
            matches = sum(1 for term in query_terms if term.lower() in window)
            if matches > max_matches:
                max_matches = matches
                best_pos = i
        
        # Snippet extract karte hain
        start = max(0, best_pos - 20)  # Thoda context pehle se
        end = min(len(self.content), best_pos + snippet_length)
        
        snippet = self.content[start:end]
        
        # Ellipsis add karenge agar start/end mein hai
        if start > 0:
            snippet = "..." + snippet
        if end < len(self.content):
            snippet = snippet + "..."
        
        self.snippet = snippet
    
    model_config = {
        "json_encoders": {
            float: lambda v: round(v, 4)
        }
    }


class SearchQuery(BaseModel):
    """
    User ki search query ko represent karta hai.
    Validation aur preprocessing yahan hoti hai.
    """
    # Raw query string
    query: str = Field(..., min_length=1, max_length=500, description="Search query")
    
    # Preprocessing options
    case_sensitive: bool = Field(default=False, description="Case sensitive search")
    fuzzy_match: bool = Field(default=False, description="Enable fuzzy matching")
    
    # Pagination
    page: int = Field(default=1, ge=1, description="Page number")
    per_page: int = Field(default=10, ge=1, le=50, description="Results per page")
    
    # Filters
    doc_types: Optional[List[DocumentType]] = Field(
        default=None, 
        description="Filter by document types"
    )
    date_from: Optional[datetime] = Field(default=None, description="Start date filter")
    date_to: Optional[datetime] = Field(default=None, description="End date filter")
    
    @field_validator('query')
    def validate_query(cls, v):
        """
        Query validation - empty ya sirf special characters nahi hone chahiye.
        """
        # Strip karte hain
        v = v.strip()
        
        # Minimum 1 alphanumeric character hona chahiye
        if not any(c.isalnum() for c in v):
            raise ValueError("Query mein kam se kam ek alphanumeric character hona chahiye")
        
        return v
    
    def get_terms(self) -> List[str]:
        """
        Query ko individual terms mein todta hai.
        """
        # Simple tokenization - production mein isse advanced hona chahiye
        import re
        terms = re.findall(r'\b\w+\b', self.query.lower())
        return terms


class IndexMetadata(BaseModel):
    """
    Poori index ki metadata store karta hai.
    Indexing statistics aur versioning ke liye useful hai.
    """
    # Index version (future migrations ke liye)
    version: str = Field(default="1.0.0", description="Index format version")
    
    # Statistics
    total_documents: int = Field(default=0, description="Total indexed documents")
    total_terms: int = Field(default=0, description="Total unique terms")  # vocabulary size
    total_tokens: int = Field(default=0, description="Total tokens across all docs")
    
    # Timing
    created_at: datetime = Field(default_factory=datetime.now)
    last_updated: datetime = Field(default_factory=datetime.now)
    
    # Average document length (BM25 ke liye zaroori)
    avg_doc_length: float = Field(default=0.0, description="Average document length")
    
    # Document IDs set for quick lookup
    document_ids: List[str] = Field(default_factory=list)  # Set ki jagah List use karo (JSON-friendly)
    
    def update_stats(self, documents: List[Document]):
        """
        Documents list se statistics calculate karta hai.
        """
        self.total_documents = len(documents)
        self.total_tokens = sum(doc.word_count for doc in documents)
        
        if self.total_documents > 0:
            self.avg_doc_length = self.total_tokens / self.total_documents
        
        self.document_ids = [doc.doc_id for doc in documents]  # List mein convert
        self.last_updated = datetime.now()
    
    def add_document(self, doc: Document):
        """
        Naya document add karte waqt stats update karta hai.
        """
        self.total_documents += 1
        self.total_tokens += doc.word_count
        self.document_ids.append(doc.doc_id)  # List mein append
        
        # Recalculate average
        self.avg_doc_length = self.total_tokens / self.total_documents
        self.last_updated = datetime.now()
    
    model_config = {
        "json_encoders": {
            datetime: lambda v: v.isoformat()
        }
    }


class SearchResponse(BaseModel):
    """
    Complete search response jo API return karega.
    """
    # Results
    results: List[SearchResult] = Field(default_factory=list)
    total_results: int = Field(default=0, description="Total matching documents")
    
    # Query info
    query: str = Field(..., description="Processed query")
    search_time_ms: float = Field(..., description="Search execution time in milliseconds")
    
    # Pagination info
    page: int = Field(default=1)
    per_page: int = Field(default=10)
    total_pages: int = Field(default=0)
    
    # Suggestions
    suggestions: Optional[List[str]] = Field(
        default=None, 
        description="Query suggestions (if available)"
    )
    
    # Debug info (only in debug mode)
    debug_info: Optional[Dict[str, Any]] = Field(default=None)


# Utility functions for serialization
def serialize_index_entry(entry: IndexEntry) -> Dict:
    """IndexEntry ko JSON-serializable dict mein convert karta hai."""
    return entry.model_dump()


def deserialize_index_entry(data: Dict) -> IndexEntry:
    """Dict se IndexEntry object create karta hai."""
    return IndexEntry(**data)


# Testing ke liye
if __name__ == "__main__":
    # Test document creation
    doc = Document(
        doc_id="test.txt",
        file_path="/data/test.txt",
        content="Python is awesome. Python is easy to learn.",
        tokens=["python", "is", "awesome", "python", "is", "easy", "to", "learn"]
    )
    doc.compute_hash()
    doc.update_stats()
    print(f"Test Document: {doc.model_dump_json(indent=2)}")
    
    # Test search result
    result = SearchResult(
        doc_id="test.txt",
        title="Test Document",
        score=0.95,
        file_path="/data/test.txt"
    )
    print(f"\nTest Result: {result.model_dump_json(indent=2)}")