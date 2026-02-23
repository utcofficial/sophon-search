"""
=============================================================================
                    INVERTED INDEX ENGINE MODULE
=============================================================================
Yeh module search engine ka core hai - Inverted Index banata hai.
Inverted Index matlab: Word -> Documents mapping (jaise book ka index hota hai)

Algorithms Implemented:
    1. Tokenization & Normalization
     2. Inverted Index Construction
    3. TF-IDF Scoring
    4. BM25 Ready Structure
    5. Index Persistence (JSON)

Performance Optimizations:
    - Memory efficient postings lists
    - Batch processing for large corpora
    - Incremental indexing support
=============================================================================
"""
import os 
import re
import json
import math
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional, Iterator
from collections import defaultdict, Counter
from datetime import datetime
import pickle

# Local imports
from models import Document, IndexEntry, IndexMetadata
from config import CONFIG


class TextPreprocessor:
    """
    Text preprocessing ka kaam sambhalta hai.
    Tokenization, normalization, aur cleaning yahan hoti hai.
    
    Yeh class stateless hai - har baar fresh process karta hai.
    """
    
    def __init__(self):
        # Compile regex patterns for efficiency
        # Word boundary ke saath alphanumeric sequences match karenge
        self.token_pattern = re.compile(r'\b[a-zA-Z0-9\u0900-\u097F]+\b')
        
        # Stop words load karte hain config se
        self.stop_words = CONFIG.indexer.STOP_WORDS
        
        # Case sensitivity flag
        self.case_sensitive = CONFIG.indexer.CASE_SENSITIVE
    
    def tokenize(self, text: str) -> List[str]:
        """
        Text ko tokens mein todta hai.
        
        Process:
        1. Regex se words extract karte hain
        2. Case normalize karte hain (agar case insensitive mode hai)
        3. Length filter lagate hain
        
        Args:
            text: Raw text string
            
        Returns:
            List of tokens (words)
        """
        # Case normalization
        if not self.case_sensitive:
            text = text.lower()
        
        # Token extraction using regex
        tokens = self.token_pattern.findall(text)
        
        # Length filtering
        min_len = CONFIG.indexer.MIN_WORD_LENGTH
        max_len = CONFIG.indexer.MAX_WORD_LENGTH
        
        filtered_tokens = [
            token for token in tokens 
            if min_len <= len(token) <= max_len
        ]
        
        return filtered_tokens
    
    def remove_stopwords(self, tokens: List[str]) -> List[str]:
        """
        Common stop words hata deta hai tokens se.
        
        Args:
            tokens: List of tokens
            
        Returns:
            Filtered list without stop words
        """
        return [token for token in tokens if token not in self.stop_words]
    
    def preprocess(self, text: str, remove_stops: bool = True) -> List[str]:
        """
        Complete preprocessing pipeline.
        
        Args:
            text: Raw text
            remove_stops: Stop words remove karna hai?
            
        Returns:
            Cleaned tokens list
        """
        tokens = self.tokenize(text)
        
        if remove_stops:
            tokens = self.remove_stopwords(tokens)
        
        return tokens
    
    def extract_ngrams(self, tokens: List[str], n: int = 2) -> List[str]:
        """
        N-grams generate karta hai tokens se.
        Future mein phrase search ke liye useful hoga.
        
        Args:
            tokens: List of tokens
            n: N-gram size (2 = bigrams, 3 = trigrams)
            
        Returns:
            List of n-grams (joined by space)
        """
        if len(tokens) < n:
            return []
        
        ngrams = []
        for i in range(len(tokens) - n + 1):
            ngram = ' '.join(tokens[i:i + n])
            ngrams.append(ngram)
        
        return ngrams


class InvertedIndex:
    """
    Inverted Index ka main class.
    Isme saari indexing logic aur data structure hai.
    
    Data Structure:
        {
            "word1": IndexEntry(postings={doc1: {...}, doc2: {...}}),
            "word2": IndexEntry(...),
            ...
        }
    """
    
    def __init__(self):
        # Main index dictionary: word -> IndexEntry
        self.index: Dict[str, IndexEntry] = {}
        
        # Metadata about the index
        self.metadata = IndexMetadata()
        
        # Preprocessor instance
        self.preprocessor = TextPreprocessor()
        
        # Document store: doc_id -> Document (for quick lookup)
        self.documents: Dict[str, Document] = {}
        
        # Statistics
        self.indexing_stats = {
            'terms_indexed': 0,
            'postings_created': 0,
            'time_taken_ms': 0
        }
    
    def _calculate_tf(self, term: str, tokens: List[str]) -> int:
        """
        Term Frequency calculate karta hai.
        Kitni baar term appear hota hai tokens mein.
        
        Args:
            term: Word to search
            tokens: Document tokens
            
        Returns:
            Frequency count
        """
        return tokens.count(term)
    
    def _calculate_idf(self, term: str) -> float:
        """
        Inverse Document Frequency calculate karta hai.
        Formula: log(N / df) where N = total docs, df = docs with term
        
        Rare terms ka high IDF hota hai (zyada important)
        Common terms ka low IDF hota hai (kam important)
        
        Args:
            term: Word ka IDF calculate karna hai
            
        Returns:
            IDF score
        """
        if term not in self.index:
            return 0.0
        
        # Document frequency
        df = self.index[term].doc_frequency
        
        # Total documents
        N = self.metadata.total_documents
        
        # IDF calculation with smoothing
        idf = math.log((N + 1) / (df + 0.5))  # Smoothed IDF
        
        return idf
    
    def _update_idf_scores(self):
        """
        Saare terms ke IDF scores recalculate karta hai.
        Naya document add karne ke baad call karna chahiye.
        """
        for term, entry in self.index.items():
            entry.idf_score = self._calculate_idf(term)
    
    def add_document(self, doc: Document) -> None:
        """
        Single document ko index mein add karta hai.
        
        Process:
        1. Document tokenize karta hai
        2. Har token ke liye posting add karta hai
        3. Document store mein save karta hai
        4. Stats update karta hai
        
        Args:
            doc: Document object jo index karna hai
        """
        # Check karein ki document already indexed toh nahi
        if doc.doc_id in self.documents:
            print(f"[WARNING] Document already indexed: {doc.doc_id}")
            return
        
        # Preprocessing
        tokens = self.preprocessor.preprocess(doc.content)
        doc.tokens = tokens
        doc.update_stats()
        doc.indexed_at = datetime.now()
        
        # Unique terms aur unki positions track karte hain
        term_positions: Dict[str, List[int]] = defaultdict(list)
        
        for pos, token in enumerate(tokens):
            term_positions[token].append(pos)
        
        # Index mein har unique term ke liye entry add karte hain
        for term, positions in term_positions.items():
            if term not in self.index:
                self.index[term] = IndexEntry(word=term)
            
            # Posting add karte hain
            frequency = len(positions)
            for pos in positions:
                self.index[term].add_posting(doc.doc_id, pos, 1)
            
            self.indexing_stats['postings_created'] += 1
        
        # Document store mein add karte hain
        self.documents[doc.doc_id] = doc
        
        # Metadata update
        self.metadata.add_document(doc)
        self.indexing_stats['terms_indexed'] += len(term_positions)
        
        print(f"[INDEXED] {doc.doc_id} - {len(tokens)} tokens, {len(term_positions)} unique terms")
    
    def add_documents(self, documents: Iterator[Document]) -> None:
        """
        Multiple documents ko batch mein index karta hai.
        
        Args:
            documents: Iterator of Document objects
        """
        start_time = datetime.now()
        doc_count = 0
        
        print(f"\n🚀 Batch indexing shuru...")
        
        for doc in documents:
            self.add_document(doc)
            doc_count += 1
            
            # Har 100 documents ke baad progress dikhate hain
            if doc_count % 100 == 0:
                print(f"   Progress: {doc_count} documents indexed...")
        
        # IDF scores update karte hain sab documents ke baad
        print("   Updating IDF scores...")
        self._update_idf_scores()
        
        # Time calculate karte hain
        end_time = datetime.now()
        time_taken = (end_time - start_time).total_seconds() * 1000
        self.indexing_stats['time_taken_ms'] = time_taken
        
        print(f"✅ Indexing complete! {doc_count} documents in {time_taken:.2f}ms")
    
    def get_term_postings(self, term: str) -> Optional[IndexEntry]:
        """
        Kisi term ka index entry return karta hai.
        
        Args:
            term: Search term
            
        Returns:
            IndexEntry ya None agar term nahi mila
        """
        # Normalize karte hain term ko
        if not self.preprocessor.case_sensitive:
            term = term.lower()
        
        return self.index.get(term)
    
    def get_document(self, doc_id: str) -> Optional[Document]:
        """
        Document ID se Document object return karta hai.
        
        Args:
            doc_id: Document identifier
            
        Returns:
            Document object ya None
        """
        return self.documents.get(doc_id)
    
    def get_term_frequency(self, term: str, doc_id: str) -> int:
        """
        Kisi specific document mein term ki frequency return karta hai.
        
        Args:
            term: Word
            doc_id: Document ID
            
        Returns:
            Frequency count (0 agar nahi mila)
        """
        entry = self.get_term_postings(term)
        if not entry or doc_id not in entry.postings:
            return 0
        
        return entry.postings[doc_id]['frequency']
    
    def get_document_vector(self, doc_id: str) -> Dict[str, float]:
        """
        Document ka TF-IDF vector return karta hai.
        Machine learning/similarity ke liye useful hai.
        
        Args:
            doc_id: Document ID
            
        Returns:
            Dictionary of {term: tfidf_score}
        """
        if doc_id not in self.documents:
            return {}
        
        vector = {}
        doc = self.documents[doc_id]
        
        for term in set(doc.tokens):
            tf = self.get_term_frequency(term, doc_id)
            entry = self.index.get(term)
            idf = entry.idf_score if entry else 0.0
            
            # TF-IDF calculation (raw count * IDF)
            vector[term] = tf * idf
        
        return vector
    
    def save(self, filepath: Optional[str] = None) -> bool:
        """
        Index ko disk pe save karta hai JSON format mein.
        
        Args:
            filepath: Kahan save karna hai (default: config se)
        
        Returns:
            True agar successful, False otherwise
        """
        try:
            if filepath is None:
                filepath = str(CONFIG.get_storage_path('index.json'))
            
            # Directory ensure karo
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            # Metadata update
            self.metadata.total_documents = len(self.documents)
            self.metadata.total_terms = len(self.index)
            self.metadata.total_terms = len(self.index)
            self.metadata.document_ids = list(self.documents.keys())  # Set nahi, List use karo
            self.metadata.last_updated = datetime.now()
            
            # Serialize karte hain
            data = {
                'metadata': self.metadata.model_dump(),
                'index': {
                    term: entry.model_dump() for term, entry in self.index.items()
                },
                'documents': {
                    doc_id: doc.model_dump() for doc_id, doc in self.documents.items()
                },
                'stats': self.indexing_stats
            }
            
            # JSON mein save karte hain
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, default=str)
            
            print(f"💾 Index saved: {filepath}")
            print(f"   Terms: {len(self.index)}")
            print(f"   Documents: {len(self.documents)}")
            return True
            
        except Exception as e:
            print(f"[ERROR] Index save karne mein error: {e}")
            return False
    
    def load(self, filepath: Optional[str] = None) -> bool:
        """
        Disk se index load karta hai.
        
        Args:
            filepath: Kahan se load karna hai
            
        Returns:
            True agar successful, False otherwise
        """
        if filepath is None:
            filepath = str(CONFIG.get_storage_path('index.json'))
        
        path = Path(filepath)
        if not path.exists():
            print(f"[WARNING] Index file nahi mili: {filepath}")
            return False
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Metadata load karte hain
            self.metadata = IndexMetadata(**data['metadata'])
            
            # Index load karte hain
            self.index = {}
            for term, entry_data in data['index'].items():
                self.index[term] = IndexEntry(**entry_data)
            
            # Documents load karte hain
            self.documents = {}
            for doc_id, doc_data in data['documents'].items():
                self.documents[doc_id] = Document(**doc_data)
            
            # Stats load karte hain
            self.indexing_stats = data.get('stats', {})
            
            print(f"📂 Index loaded: {filepath}")
            print(f"   Terms: {len(self.index)}")
            print(f"   Documents: {len(self.documents)}")
            return True
            
        except Exception as e:
            print(f"[ERROR] Index load karne mein error: {e}")
            return False
    
    def clear(self):
        """Poora index clear karta hai."""
        self.index.clear()
        self.documents.clear()
        self.metadata = IndexMetadata()
        self.indexing_stats = {
            'terms_indexed': 0,
            'postings_created': 0,
            'time_taken_ms': 0
        }
        print("🗑️  Index cleared")
    
    def get_statistics(self) -> Dict:
        """Index ki detailed statistics return karta hai."""
        avg_terms_per_doc = 0
        if self.documents:
            avg_terms_per_doc = sum(len(doc.tokens) for doc in self.documents.values()) / len(self.documents)
        
        return {
            'total_terms': len(self.index),
            'total_documents': len(self.documents),
            'avg_terms_per_doc': avg_terms_per_doc,
            'index_size_mb': 0.0,
            'metadata': self.metadata.model_dump(),
            'indexing_stats': self.indexing_stats
        }


class IncrementalIndexer:
    """
    Incremental indexing support ke liye class.
    Naye documents add karna bina poora reindex kiye.
    
    Future enhancement: Deleted/updated documents handle karna
    """
    
    def __init__(self, base_index: InvertedIndex):
        self.index = base_index
        self.pending_documents: List[Document] = []
    
    def stage_document(self, doc: Document):
        """Document ko staging area mein add karta hai."""
        self.pending_documents.append(doc)
    
    def commit(self):
        """Saare staged documents ko index mein add karta hai."""
        for doc in self.pending_documents:
            self.index.add_document(doc)
        
        self.index._update_idf_scores()
        count = len(self.pending_documents)
        self.pending_documents.clear()
        
        print(f"✅ Committed {count} documents to index")
        return count


# Testing ke liye
if __name__ == "__main__":
    import os
    from crawler import crawl_documents
    
    print("=" * 60)
    print("INVERTED INDEX ENGINE TEST")
    print("=" * 60)
    
    # Index create karte hain
    index = InvertedIndex()
    
    # Test documents crawl karte hain
    docs_dir = CONFIG.paths['DOCUMENTS_DIR']
    
    if docs_dir.exists():
        documents = crawl_documents(str(docs_dir))
        
        if documents:
            # Indexing
            index.add_documents(iter(documents))
            
            # Save karte hain
            index.save()
            
            # Test search
            print("\n🔍 Testing index lookup:")
            test_terms = ['python', 'search', 'engine']
            
            for term in test_terms:
                entry = index.get_term_postings(term)
                if entry:
                    print(f"\nTerm: '{term}'")
                    print(f"  Document Frequency: {entry.doc_frequency}")
                    print(f"  IDF Score: {entry.idf_score:.4f}")
                    print(f"  Documents: {list(entry.postings.keys())[:3]}...")  # Pehle 3
                else:
                    print(f"\nTerm: '{term}' - Not found in index")
            
            # Statistics
            print(f"\n📊 Index Statistics:")
            stats = index.get_statistics()
            for key, value in stats.items():
                if key not in ['metadata', 'indexing_stats']:
                    print(f"  {key}: {value}")
        else:
            print("❌ Koi documents nahi mile!")
    else:
        print(f"❌ Documents directory nahi mili: {docs_dir}")