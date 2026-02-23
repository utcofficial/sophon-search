"""
=============================================================================
                    SEARCH ENGINE CONFIGURATION MODULE
=============================================================================
Yeh file poori search engine ki configuration handle karti hai.
Isme saari settings, paths, aur constants define hain jo baaki modules use karenge.

Architecture Pattern: Singleton Configuration Pattern
Isse ensure hota hai ki saari settings ek jagah se manage ho, aur koi bhi 
module easily access kar sake bina hardcoding ke.
=============================================================================
"""

import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Set
import json


@dataclass
class CrawlerConfig:
    """
    Crawler ke liye specific settings.
    Yeh decide karta hai ki kaunse documents crawl karne hain aur kaise.
    """
    # Kaunse file extensions support karein (text files hi lete hain)
    SUPPORTED_EXTENSIONS: Set[str] = field(default_factory=lambda: {'.txt', '.md', '.json'})
    
    # Maximum file size in bytes (10 MB se zyada ke files skip karenge)
    MAX_FILE_SIZE: int = 10 * 1024 * 1024
    
    # Recursive crawling enable hai ya nahi
    RECURSIVE_CRAWLING: bool = True
    
    # Ignore patterns - yeh folders/files skip karenge
    IGNORE_PATTERNS: List[str] = field(default_factory=lambda: [
        '__pycache__', '.git', 'node_modules', '.env', 'venv'
    ])


@dataclass
class IndexerConfig:
    """
    Indexing algorithm ke liye configuration.
    Yeh TF-IDF aur inverted index ki settings control karta hai.
    """
    # Minimum word length (2 letter se chhote words ignore)
    MIN_WORD_LENGTH: int = 2
    
    # Maximum word length (30 letter se bade words spam hote hain usually)
    MAX_WORD_LENGTH: int = 30
    
    # Case sensitive search chahiye ya nahi (False = case insensitive better hai)
    CASE_SENSITIVE: bool = False
    
    # Stop words list - yeh common words index mein nahi jayenge
    STOP_WORDS: Set[str] = field(default_factory=lambda: {
        'hai', 'hain', 'tha', 'the', 'ho', 'hu', 'hoga', 'hogi',  # Hindi common
        'is', 'are', 'was', 'were', 'be', 'been', 'being',        # English common
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at',
        'to', 'for', 'of', 'with', 'by', 'from', 'as', 'it', 'this',
        'that', 'these', 'those', 'i', 'you', 'he', 'she', 'we', 'they'
    })
    
    # TF-IDF ka smoothing parameter (divide by zero se bachne ke liye)
    SMOOTHING_FACTOR: float = 1.0


@dataclass
class SearcherConfig:
    """
    Search algorithm ki tuning parameters.
    Yeh ranking aur relevance scoring ko control karta hai.
    """
    # Top kitne results dikhane hain
    TOP_K_RESULTS: int = 10
    
    # Minimum relevance score (isse kam wale results filter ho jayenge)
    MIN_RELEVANCE_SCORE: float = 0.01
    
    # BM25 parameters (Okapi BM25 algorithm ke liye)
    BM25_K1: float = 1.5  # Term frequency saturation
    BM25_B: float = 0.75  # Length normalization
    
    # Query expansion enable hai ya nahi (synonyms add karna)
    ENABLE_QUERY_EXPANSION: bool = False
    
    # Fuzzy matching ka threshold (0.8 = 80% match chahiye)
    FUZZY_MATCH_THRESHOLD: float = 0.8


class SearchEngineConfig:
    """
    Main configuration class jo saari sub-configurations ko manage karti hai.
    Isse poori application ki settings centralized ho jati hain.
    
    Usage:
        config = SearchEngineConfig()
        print(config.paths.DOCUMENTS_DIR)  # Documents ka path milega
    """
    
    def __init__(self):
        # Project root directory ka path nikal rahe hain
        # Yeh file backend/config.py mein hai, toh 2 level up jayenge
        self.ROOT_DIR: Path = Path(__file__).parent.parent.absolute()
        
        # Saare important paths define kar rahe hain
        self.paths = self._setup_paths()
        
        # Sub-configurations initialize kar rahe hain
        self.crawler = CrawlerConfig()
        self.indexer = IndexerConfig()
        self.searcher = SearcherConfig()
        
        # Runtime settings
        self.DEBUG: bool = os.getenv('DEBUG', 'false').lower() == 'true'
        self.LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')
        
    def _setup_paths(self) -> Dict[str, Path]:
        """
        Saare directory paths setup karta hai.
        Agar koi directory exist nahi karti toh create bhi kar deta hai.
        """
        paths = {
            'BACKEND_DIR': self.ROOT_DIR / 'backend',
            'STORAGE_DIR': self.ROOT_DIR / 'backend' / 'storage',
            'DATA_DIR': self.ROOT_DIR / 'data',
            'DOCUMENTS_DIR': self.ROOT_DIR / 'data' / 'documents',
            'FRONTEND_DIR': self.ROOT_DIR / 'frontend',
        }
        
        # Ensure all directories exist
        for path_name, path_obj in paths.items():
            if not path_obj.exists():
                path_obj.mkdir(parents=True, exist_ok=True)
                print(f"[INFO] Directory create ki gayi: {path_obj}")
                
        return paths
    
    def get_storage_path(self, filename: str) -> Path:
        """
        Storage folder mein kisi bhi file ka complete path return karta hai.
        
        Args:
            filename: Jis file ka path chahiye (e.g., 'index.json')
            
        Returns:
            Path object with full path
        """
        return self.paths['STORAGE_DIR'] / filename
    
    def to_dict(self) -> Dict:
        """
        Poori configuration ko dictionary mein convert karta hai.
        Useful hai debugging ke liye ya config export karne ke liye.
        """
        return {
            'paths': {k: str(v) for k, v in self.paths.items()},
            'crawler': self.crawler.__dict__,
            'indexer': self.indexer.__dict__,
            'searcher': self.searcher.__dict__,
            'debug': self.DEBUG,
            'log_level': self.LOG_LEVEL
        }


# Global config instance - isse poori application mein import karke use karenge
# Singleton pattern follow ho raha hai yahan
CONFIG = SearchEngineConfig()

# Agar is file ko directly run karein toh config print hogi (testing ke liye)
if __name__ == "__main__":
    print("🔧 Search Engine Configuration:")
    print(json.dumps(CONFIG.to_dict(), indent=2, default=str))