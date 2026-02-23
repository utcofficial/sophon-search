"""
=============================================================================
                    DOCUMENT CRAWLER MODULE
=============================================================================
Yeh module file system se documents read karta hai aur unhe process karta hai.
Crawler recursive hai - subdirectories mein bhi jaayega.

Key Features:
    - Multiple file format support (txt, md, json)
    - File size validation
    - Duplicate detection via content hashing
    - Error handling with graceful degradation
    - Progress tracking for large corpora

Architecture:
    Strategy Pattern use kar rahe hain different file types ke liye
=============================================================================
"""

import os
import json
from pathlib import Path
from typing import List, Iterator, Optional, Callable
from datetime import datetime
import mimetypes
from collections import defaultdict

# Local imports
from models import Document, DocumentType
from config import CONFIG


class FileHandler:
    """
    Base class for different file type handlers.
    Har file type ke liye alag handler hoga iska subclass banake.
    """
    
    def can_handle(self, file_path: Path) -> bool:
        """Check karta hai ki yeh handler iss file type ko handle kar sakta hai."""
        raise NotImplementedError
    
    def extract_content(self, file_path: Path) -> str:
        """File se text content extract karta hai."""
        raise NotImplementedError
    
    def get_doc_type(self) -> DocumentType:
        """Document type return karta hai."""
        raise NotImplementedError


class TextFileHandler(FileHandler):
    """
    Plain text files (.txt) handle karta hai.
    Encoding detection ke saath - UTF-8 prefer karte hain.
    """
    
    def can_handle(self, file_path: Path) -> bool:
        return file_path.suffix.lower() == '.txt'
    
    def extract_content(self, file_path: Path) -> str:
        """
        Text file read karta hai with encoding fallback.
        Pehle UTF-8 try karte hain, fail ho toh latin-1.
        """
        encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
        
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    return f.read()
            except UnicodeDecodeError:
                continue
        
        # Agar sab fail ho gaye toh binary read karke decode karenge
        # errors='ignore' se problematic characters skip ho jayenge
        with open(file_path, 'rb') as f:
            return f.read().decode('utf-8', errors='ignore')
    
    def get_doc_type(self) -> DocumentType:
        return DocumentType.TEXT


class MarkdownFileHandler(FileHandler):
    """
    Markdown files (.md) handle karta hai.
    Future mein YAML frontmatter bhi parse kar sakte hain.
    """
    
    def can_handle(self, file_path: Path) -> bool:
        return file_path.suffix.lower() == '.md'
    
    def extract_content(self, file_path: Path) -> str:
        # Same as text file for now, but can add markdown-specific processing
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    def get_doc_type(self) -> DocumentType:
        return DocumentType.MARKDOWN


class JSONFileHandler(FileHandler):
    """
    JSON files handle karta hai.
    Nested JSON se text fields extract kar sakta hai.
    """
    
    def can_handle(self, file_path: Path) -> bool:
        return file_path.suffix.lower() == '.json'
    
    def extract_content(self, file_path: Path) -> str:
        """
        JSON file se text content extract karta hai.
        Agar 'content' ya 'text' field hai toh woh lete hain,
        warna poora JSON stringify kar dete hain.
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Agar string hai toh directly return
        if isinstance(data, str):
            return data
        
        # Agar dict hai toh common text fields check karte hain
        if isinstance(data, dict):
            for key in ['content', 'text', 'body', 'description', 'data']:
                if key in data and isinstance(data[key], str):
                    return data[key]
            
            # Koi specific field nahi mila toh poora JSON as text
            return json.dumps(data, indent=2)
        
        # List ya koi aur type hai toh JSON stringify
        return json.dumps(data, indent=2)
    
    def get_doc_type(self) -> DocumentType:
        return DocumentType.JSON


class DocumentCrawler:
    """
    Main crawler class jo file system traverse karti hai.
    
    Usage:
        crawler = DocumentCrawler()
        documents = list(crawler.crawl_directory("/path/to/docs"))
        
    Yeh generator return karta hai taaki memory efficient ho -
    saare documents ek saath load nahi honge.
    """
    
    def __init__(self):
        # Saare file handlers register kar rahe hain
        self.handlers: List[FileHandler] = [
            TextFileHandler(),
            MarkdownFileHandler(),
            JSONFileHandler(),
        ]
        
        # Statistics tracking
        self.stats = {
            'files_processed': 0,
            'files_skipped': 0,
            'errors': 0,
            'total_size': 0
        }
        
        # Duplicate detection ke liye
        self.seen_hashes: set = set()
        
        # Callback for progress updates (optional)
        self.progress_callback: Optional[Callable] = None
    
    def set_progress_callback(self, callback: Callable[[str, int, int], None]):
        """
        Progress updates ke liye callback set karta hai.
        
        Args:
            callback: Function jo (message, current, total) receive karega
        """
        self.progress_callback = callback
    
    def _report_progress(self, message: str, current: int, total: int):
        """Internal method jo callback ko call karta hai agar set hai."""
        if self.progress_callback:
            try:
                self.progress_callback(message, current, total)
            except Exception as e:
                print(f"[WARNING] Progress callback error: {e}")
    
    def _get_handler(self, file_path: Path) -> Optional[FileHandler]:
        """
        File path ke hisaab se suitable handler dhoondhta hai.
        
        Args:
            file_path: File ka path
            
        Returns:
            Suitable FileHandler ya None agar koi handler nahi mila
        """
        for handler in self.handlers:
            if handler.can_handle(file_path):
                return handler
        return None
    
    def _should_process_file(self, file_path: Path) -> bool:
        """
        Check karta hai ki file process karni hai ya nahi.
        Size, extension, aur ignore patterns check karta hai.
        
        Args:
            file_path: Check karne ke liye file path
            
        Returns:
            True agar process karni hai, False otherwise
        """
        # Check karein ki file exist karti hai aur readable hai
        if not file_path.exists() or not file_path.is_file():
            return False
        
        # Extension check
        if file_path.suffix.lower() not in CONFIG.crawler.SUPPORTED_EXTENSIONS:
            self.stats['files_skipped'] += 1
            return False
        
        # File size check
        file_size = file_path.stat().st_size
        if file_size > CONFIG.crawler.MAX_FILE_SIZE:
            print(f"[SKIP] File bohot badi hai: {file_path} ({file_size} bytes)")
            self.stats['files_skipped'] += 1
            return False
        
        # Ignore patterns check
        path_str = str(file_path)
        for pattern in CONFIG.crawler.IGNORE_PATTERNS:
            if pattern in path_str:
                self.stats['files_skipped'] += 1
                return False
        
        return True
    
    def _create_document(self, file_path: Path) -> Optional[Document]:
        """
        File se Document object create karta hai.
        
        Args:
            file_path: Document file ka path
            
        Returns:
            Document object ya None agar error aaya
        """
        handler = self._get_handler(file_path)
        if not handler:
            return None
        
        try:
            # Content extract karte hain
            content = handler.extract_content(file_path)
            
            # Agar content empty hai toh skip karenge
            if not content or not content.strip():
                print(f"[SKIP] Empty file: {file_path}")
                return None
            
            # File stats lete hain
            file_stat = file_path.stat()
            
            # Document ID generate karte hain (relative path use karte hain)
            try:
                doc_id = str(file_path.relative_to(CONFIG.ROOT_DIR))
            except ValueError:
                # Agar relative path nahi ban sakta toh absolute use karenge
                doc_id = str(file_path)
            
            # Document object create karte hain
            doc = Document(
                doc_id=doc_id,
                file_path=str(file_path.absolute()),
                doc_type=handler.get_doc_type(),
                content=content,
                file_size=file_stat.st_size,
                modified_at=datetime.fromtimestamp(file_stat.st_mtime),
                created_at=datetime.fromtimestamp(file_stat.st_ctime)
            )
            
            # Content hash calculate karte hain (duplicate detection ke liye)
            content_hash = doc.compute_hash()
            
            # Duplicate check
            if content_hash in self.seen_hashes:
                print(f"[SKIP] Duplicate file: {file_path}")
                return None
            
            self.seen_hashes.add(content_hash)
            
            # Title extract karte hain
            doc.extract_title()
            
            self.stats['files_processed'] += 1
            self.stats['total_size'] += file_stat.st_size
            
            return doc
            
        except Exception as e:
            print(f"[ERROR] File process karne mein error: {file_path} - {str(e)}")
            self.stats['errors'] += 1
            return None
    
    def crawl_file(self, file_path: str) -> Optional[Document]:
        """
        Single file crawl karta hai.
        
        Args:
            file_path: File ka path (string)
            
        Returns:
            Document object ya None
        """
        path = Path(file_path)
        
        if not self._should_process_file(path):
            return None
        
        return self._create_document(path)
    
    def crawl_directory(self, directory_path: str) -> Iterator[Document]:
        """
        Directory recursively crawl karta hai aur documents yield karta hai.
        
        Args:
            directory_path: Root directory ka path
            
        Yields:
            Document objects one by one (memory efficient)
        """
        root_path = Path(directory_path)
        
        if not root_path.exists():
            raise FileNotFoundError(f"Directory nahi mili: {directory_path}")
        
        if not root_path.is_dir():
            raise NotADirectoryError(f"Yeh directory nahi hai: {directory_path}")
        
        print(f"\n🕷️  Crawling shuru: {root_path}")
        
        # Saari files collect karte hain pehle taaki progress track kar sakein
        all_files = []
        
        if CONFIG.crawler.RECURSIVE_CRAWLING:
            # Recursive walk
            for file_path in root_path.rglob('*'):
                if file_path.is_file():
                    all_files.append(file_path)
        else:
            # Sirf top level
            for file_path in root_path.iterdir():
                if file_path.is_file():
                    all_files.append(file_path)
        
        total_files = len(all_files)
        print(f"📁 Total files mil gayi: {total_files}")
        
        # Ab har file process karte hain
        for idx, file_path in enumerate(all_files, 1):
            self._report_progress(f"Processing {file_path.name}", idx, total_files)
            
            if not self._should_process_file(file_path):
                continue
            
            doc = self._create_document(file_path)
            if doc:
                yield doc
        
        print(f"\n✅ Crawling complete!")
        print(f"   Processed: {self.stats['files_processed']}")
        print(f"   Skipped: {self.stats['files_skipped']}")
        print(f"   Errors: {self.stats['errors']}")
        print(f"   Total size: {self.stats['total_size'] / 1024:.2f} KB")
    
    def get_statistics(self) -> dict:
        """Crawling statistics return karta hai."""
        return self.stats.copy()
    
    def reset_statistics(self):
        """Statistics reset karta hai."""
        self.stats = {
            'files_processed': 0,
            'files_skipped': 0,
            'errors': 0,
            'total_size': 0
        }
        self.seen_hashes.clear()


# Convenience function for quick crawling
def crawl_documents(path: str, recursive: bool = True) -> List[Document]:
    """
    Quick helper function jo given path se saare documents return karta hai.
    
    Args:
        path: File ya directory ka path
        recursive: Subdirectories mein bhi crawl karna hai?
        
    Returns:
        List of Document objects
    """
    crawler = DocumentCrawler()
    
    # Config update agar recursive flag diya hai
    original_recursive = CONFIG.crawler.RECURSIVE_CRAWLING
    CONFIG.crawler.RECURSIVE_CRAWLING = recursive
    
    try:
        path_obj = Path(path)
        
        if path_obj.is_file():
            # Single file
            doc = crawler.crawl_file(path)
            return [doc] if doc else []
        
        elif path_obj.is_dir():
            # Directory
            return list(crawler.crawl_directory(path))
        
        else:
            print(f"[ERROR] Invalid path: {path}")
            return []
    
    finally:
        # Config restore karte hain
        CONFIG.crawler.RECURSIVE_CRAWLING = original_recursive


# Testing ke liye
if __name__ == "__main__":
    import sys
    
    # Test directory
    test_dir = CONFIG.paths['DOCUMENTS_DIR']
    
    if len(sys.argv) > 1:
        test_dir = sys.argv[1]
    
    print("=" * 60)
    print("DOCUMENT CRAWLER TEST")
    print("=" * 60)
    
    try:
        documents = crawl_documents(str(test_dir))
        
        print(f"\n📊 Test Results:")
        print(f"Total documents: {len(documents)}")
        
        for i, doc in enumerate(documents[:3], 1):  # Sirf pehle 3 dikhate hain
            print(f"\n{i}. {doc.doc_id}")
            print(f"   Title: {doc.title}")
            print(f"   Type: {doc.doc_type}")
            print(f"   Size: {doc.file_size} bytes")
            print(f"   Words: {doc.word_count}")
            print(f"   Content preview: {doc.content[:100]}...")
            
    except Exception as e:
        print(f"[ERROR] Test failed: {e}")