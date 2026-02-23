"""
=============================================================================
                    SEARCH & RANKING ENGINE MODULE
=============================================================================
Yeh module user queries ko process karta hai aur ranked results return karta hai.

Ranking Algorithms Implemented:
    1. Boolean Retrieval (AND/OR/NOT operations)
    2. Vector Space Model (TF-IDF Cosine Similarity)
    3. BM25 (Best Matching 25) - Industry Standard
    4. Phrase Matching with Proximity Scoring

Query Processing:
    - Tokenization aur normalization
    - Query expansion (future scope)
    - Spell checking suggestions (future scope)

Performance:
    - O(1) term lookup via hash index
    - Efficient top-K retrieval using heap
    - Early termination optimizations
=============================================================================
"""

import heapq
import math
import time
import traceback
from typing import List, Dict, Set, Tuple, Optional
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime

# Local imports
from models import (
    SearchQuery, SearchResult, SearchResponse, 
    Document, IndexEntry
)
from indexer import InvertedIndex, TextPreprocessor
from config import CONFIG


@dataclass
class ScoringFactors:
    """
    Ranking algorithm ke weights ko store karta hai.
    Inhe tune karke search quality adjust kar sakte hain.
    """
    tf_weight: float = 1.0          # Term frequency importance
    idf_weight: float = 1.0         # IDF importance
    length_norm_weight: float = 0.5 # Document length normalization
    proximity_weight: float = 0.3   # Term proximity bonus
    freshness_weight: float = 0.1   # Recency bonus (future use)


class BM25Scorer:
    """
    BM25 (Best Matching 25) scoring algorithm.
    Yeh modern search engines (Elasticsearch, Solr) mein use hota hai.
    
    Formula:
        score = IDF * (f * (k1 + 1)) / (f + k1 * (1 - b + b * (dl / avgdl)))
    
    Where:
        f = term frequency in document
        dl = document length
        avgdl = average document length
        k1, b = tuning parameters
    """
    
    def __init__(self, k1: float = None, b: float = None):
        # Config se parameters lete hain ya default use karte hain
        self.k1 = k1 or CONFIG.searcher.BM25_K1
        self.b = b or CONFIG.searcher.BM25_B
    
    def calculate_idf(self, term: str, index: InvertedIndex) -> float:
        """
        BM25 specific IDF calculation.
        
        Formula: log(1 + (N - n + 0.5) / (n + 0.5))
        Where N = total docs, n = docs with term
        """
        try:
            N = index.metadata.total_documents
            
            entry = index.get_term_postings(term)
            if not entry:
                return 0.0
            
            n = entry.doc_frequency
            
            # BM25 IDF (slightly different from standard TF-IDF)
            idf = math.log(1 + (N - n + 0.5) / (n + 0.5))
            
            return idf
        except Exception as e:
            print(f"[BM25 ERROR] calculate_idf failed for term '{term}': {e}")
            return 0.0
    
    def score_term(self, term: str, doc_id: str, index: InvertedIndex) -> float:
        """
        Single term ka BM25 score calculate karta hai.
        
        Args:
            term: Query term
            doc_id: Document ID
            index: InvertedIndex instance
            
        Returns:
            BM25 score for this term-document pair
        """
        try:
            # Get term frequency
            entry = index.get_term_postings(term)
            if not entry or doc_id not in entry.postings:
                return 0.0
            
            f = entry.postings[doc_id]['frequency']
            
            # Document length
            doc = index.get_document(doc_id)
            if not doc:
                return 0.0
            
            dl = doc.word_count or 1          # Guard against zero length
            avgdl = index.metadata.avg_doc_length or 1.0   # Guard against zero avg
            
            # BM25 calculation
            idf = self.calculate_idf(term, index)
            
            # Term frequency component
            tf_component = (f * (self.k1 + 1)) / (f + self.k1 * (1 - self.b + self.b * (dl / avgdl)))
            
            score = idf * tf_component
            
            # Guard against NaN / Inf
            if math.isnan(score) or math.isinf(score):
                return 0.0
            
            return score
        except Exception as e:
            print(f"[BM25 ERROR] score_term failed for term '{term}', doc '{doc_id}': {e}")
            return 0.0


class TFIDFScorer:
    """
    Classic TF-IDF Cosine Similarity scorer.
    Simple aur effective baseline algorithm.
    """
    
    def score(self, query_terms: List[str], doc_id: str, index: InvertedIndex) -> float:
        """
        Document ka TF-IDF score calculate karta hai query ke against.
        
        Args:
            query_terms: Tokenized query terms
            doc_id: Document to score
            index: InvertedIndex instance
            
        Returns:
            Cosine similarity score
        """
        try:
            doc = index.get_document(doc_id)
            if not doc:
                return 0.0
            
            # Agar document mein tokens hi nahi hain to score 0
            if not doc.tokens:
                return 0.0
            
            # Query vector (simplified - binary weights)
            query_vector = {term: 1 for term in query_terms}
            
            # Document vector (TF-IDF weights)
            doc_vector = {}
            for term in set(doc.tokens):
                tf = index.get_term_frequency(term, doc_id) or 0.0  # guard
                entry = index.index.get(term)
                idf = entry.idf_score if entry else 0.0
                doc_vector[term] = tf * idf
            
            # Dot product
            score = 0.0
            for term in query_terms:
                if term in doc_vector:
                    score += query_vector[term] * doc_vector[term]
            
            return score
        except Exception as e:
            print(f"[TFIDF ERROR] score failed for doc '{doc_id}': {e}")
            return 0.0


class BooleanRetriever:
    """
    Boolean retrieval operations (AND, OR, NOT).
    Precise matching ke liye useful hai.
    """
    
    def __init__(self, index: InvertedIndex):
        self.index = index
    
    def and_operation(self, terms: List[str]) -> Set[str]:
        """
        AND operation - saare terms hone chahiye document mein.
        
        Args:
            terms: List of terms (AND mein join honge)
            
        Returns:
            Set of document IDs matching ALL terms
        """
        try:
            if not terms:
                return set()
            
            # Pehle term se shuru karte hain
            result = self._get_doc_ids(terms[0])
            
            # Baaki terms ke saath intersect karte hain
            for term in terms[1:]:
                term_docs = self._get_doc_ids(term)
                result = result.intersection(term_docs)
                
                # Agar empty ho gaya toh early return
                if not result:
                    return set()
            
            return result
        except Exception as e:
            print(f"[BOOLEAN ERROR] and_operation failed: {e}")
            return set()
    
    def or_operation(self, terms: List[str]) -> Set[str]:
        """
        OR operation - koi bhi term chalega.
        
        Args:
            terms: List of terms (OR mein join honge)
            
        Returns:
            Set of document IDs matching ANY term
        """
        try:
            result = set()
            
            for term in terms:
                result = result.union(self._get_doc_ids(term))
            
            return result
        except Exception as e:
            print(f"[BOOLEAN ERROR] or_operation failed: {e}")
            return set()
    
    def not_operation(self, docs: Set[str], exclude_terms: List[str]) -> Set[str]:
        """
        NOT operation - certain terms nahi hone chahiye.
        
        Args:
            docs: Initial document set
            exclude_terms: Terms jo nahi hone chahiye
            
        Returns:
            Filtered document set
        """
        try:
            for term in exclude_terms:
                exclude_docs = self._get_doc_ids(term)
                docs = docs - exclude_docs
            return docs
        except Exception as e:
            print(f"[BOOLEAN ERROR] not_operation failed: {e}")
            return docs
    
    def _get_doc_ids(self, term: str) -> Set[str]:
        """Term ke saare document IDs return karta hai."""
        try:
            entry = self.index.get_term_postings(term)
            if entry:
                return set(entry.postings.keys())
            return set()
        except Exception as e:
            print(f"[BOOLEAN ERROR] _get_doc_ids failed for term '{term}': {e}")
            return set()


class SearchEngine:
    """
    Main search engine class jo saari functionality integrate karti hai.
    
    Usage:
        engine = SearchEngine()
        engine.load_index()
        results = engine.search("python tutorial")
    """
    
    def __init__(self):
        self.index = InvertedIndex()
        self.preprocessor = TextPreprocessor()
        self.bm25_scorer = BM25Scorer()
        self.tfidf_scorer = TFIDFScorer()
        self.boolean_retriever = BooleanRetriever(self.index)
        
        # Scoring weights
        self.scoring = ScoringFactors()
        
        # Cache for frequent queries (simple dict, LRU can be added)
        self.query_cache: Dict[str, SearchResponse] = {}
        self.cache_max_size = 100
    
    def load_index(self, filepath: Optional[str] = None) -> bool:
        """
        Index load karta hai disk se.
        
        Args:
            filepath: Index file ka path
            
        Returns:
            True agar successful
        """
        try:
            success = self.index.load(filepath)
            if success:
                # Boolean retriever ko updated index do
                self.boolean_retriever = BooleanRetriever(self.index)
            return success
        except Exception as e:
            print(f"[ERROR] load_index failed: {e}")
            return False
    
    def build_index(self, documents):
        """
        Fresh index build karta hai documents se.
        
        Args:
            documents: List/Iterator of Document objects
        """
        try:
            self.index.clear()
            self.index.add_documents(documents)
            self.boolean_retriever = BooleanRetriever(self.index)
        except Exception as e:
            print(f"[ERROR] build_index failed: {e}")
    
    def _tokenize_query(self, query: str) -> List[str]:
        """
        Query ko tokens mein convert karta hai.
        
        Args:
            query: Raw query string
            
        Returns:
            List of processed tokens
        """
        try:
            # Same preprocessing jo indexing mein use ki thi
            tokens = self.preprocessor.preprocess(query)
            return tokens
        except Exception as e:
            print(f"[ERROR] _tokenize_query failed for '{query}': {e}")
            return []
    
    def _retrieve_candidates(self, query_terms: List[str]) -> Set[str]:
        """
        Initial candidate documents retrieve karta hai.
        HYBRID APPROACH: AND + OR dono results combine karta hai.
        
        Args:
            query_terms: Tokenized query
            
        Returns:
            Set of candidate document IDs
        """
        try:
            if not query_terms:
                return set()
            
            # Step 1: AND operation - exact matches (saare terms)
            and_candidates = self.boolean_retriever.and_operation(query_terms)
            
            # Step 2: OR operation - partial matches (koi bhi term)
            or_candidates = self.boolean_retriever.or_operation(query_terms)
            
            # Step 3: Dono ko combine kar do
            all_candidates = and_candidates.union(or_candidates)
            
            print(f"[DEBUG] AND results: {len(and_candidates)}, OR results: {len(or_candidates)}, Total: {len(all_candidates)}")
            
            return all_candidates
            
        except Exception as e:
            print(f"[ERROR] _retrieve_candidates failed: {e}")
            return set()
    
    def _rank_documents(
        self, 
        candidates: Set[str], 
        query_terms: List[str],
        scoring_algorithm: str = 'bm25'
    ) -> List[Tuple[str, float]]:
        """
        Candidate documents ko rank karta hai relevance ke hisaab se.
        
        Args:
            candidates: Document IDs to rank
            query_terms: Query terms
            scoring_algorithm: 'bm25' ya 'tfidf'
            
        Returns:
            Sorted list of (doc_id, score) tuples
        """
        try:
            scores = []
            
            for doc_id in candidates:
                try:
                    if scoring_algorithm == 'bm25':
                        # BM25 scoring (sum of all query terms)
                        score = sum(
                            self.bm25_scorer.score_term(term, doc_id, self.index)
                            for term in query_terms
                        )
                    else:
                        # TF-IDF scoring
                        score = self.tfidf_scorer.score(query_terms, doc_id, self.index)
                    
                    # Minimum threshold check
                    if score >= CONFIG.searcher.MIN_RELEVANCE_SCORE:
                        scores.append((doc_id, score))
                except Exception as e:
                    print(f"[ERROR] Scoring failed for doc {doc_id}: {e}")
                    continue
            
            # Sort by score descending
            scores.sort(key=lambda x: x[1], reverse=True)
            
            return scores
        except Exception as e:
            print(f"[ERROR] _rank_documents failed: {e}")
            return []
    
    def _create_search_result(
        self, 
        doc_id: str, 
        score: float, 
        query_terms: List[str]
    ) -> Optional[SearchResult]:
        """
        Document ID se SearchResult object create karta hai.
        
        Args:
            doc_id: Document identifier
            score: Relevance score
            query_terms: Original query terms
            
        Returns:
            SearchResult object ya None agar document missing ho
        """
        try:
            doc = self.index.get_document(doc_id)
            
            if not doc:
                # Missing document ko silently skip karo, crash nahi
                return None
            
            # Kaunse terms match hue - guard for missing tokens
            matched_terms = []
            if doc.tokens:
                doc_tokens_lower = [t.lower() if t else "" for t in doc.tokens if t]
                matched_terms = [
                    term for term in query_terms 
                    if term in doc_tokens_lower
                ]
            
            # Result object create karte hain
            result = SearchResult(
                doc_id=doc_id,
                title=doc.title or doc_id,
                score=score,
                matched_terms=matched_terms,
                file_path=doc.file_path,
                file_size=doc.file_size,
                modified_at=doc.modified_at,
                content=doc.content  # Snippet generation ke liye
            )
            
            # Snippet generate karte hain - sirf agar content exist karta hai
            if result.content:
                try:
                    result.generate_snippet(query_terms)
                except Exception as e:
                    print(f"[ERROR] Snippet generation failed for {doc_id}: {e}")
            
            # Detailed scores for debugging - safe sum
            tf_sum = 0.0
            for term in query_terms:
                tf = self.index.get_term_frequency(term, doc_id)
                if tf:
                    tf_sum += tf
            result.tf_score = tf_sum
            
            # IDF sum safely - pehle check karo term exists ya nahi
            idf_sum = 0.0
            for term in query_terms:
                entry = self.index.index.get(term)
                if entry:
                    idf_sum += entry.idf_score
            result.idf_score = idf_sum
            
            return result
        except Exception as e:
            print(f"[ERROR] _create_search_result failed for doc {doc_id}: {e}")
            traceback.print_exc()
            return None
    
    def search(self, query_obj: SearchQuery) -> SearchResponse:
        """
        Main search method jo pura pipeline execute karti hai.
        
        Pipeline:
        1. Query validation aur tokenization
        2. Cache check
        3. Candidate retrieval (Boolean)
        4. Ranking (BM25/TF-IDF)
        5. Result formatting
        6. Caching
        
        Args:
            query_obj: SearchQuery object with all parameters
            
        Returns:
            SearchResponse object
        """
        start_time = time.time()
        
        try:
            # Cache key generate karte hain
            cache_key = f"{query_obj.query}:{query_obj.page}:{query_obj.per_page}"
            
            # Cache check (simple implementation)
            if cache_key in self.query_cache:
                print(f"[CACHE HIT] Query: '{query_obj.query}'")
                return self.query_cache[cache_key]
            
            # Step 1: Query preprocessing
            query_terms = self._tokenize_query(query_obj.query)
            
            if not query_terms:
                return SearchResponse(
                    results=[],
                    total_results=0,
                    query=query_obj.query,
                    search_time_ms=0,
                    page=query_obj.page,
                    per_page=query_obj.per_page,
                    total_pages=0,
                    suggestions=["Kripya koi valid search term enter karein"]
                )
            
            print(f"[SEARCH] Query: '{query_obj.query}' -> Terms: {query_terms}")
            
            # DEBUG: Check if terms exist in index
            for term in query_terms:
                entry = self.index.get_term_postings(term)
                if entry:
                    print(f"[DEBUG] Term '{term}' exists with {entry.doc_frequency} docs")
                else:
                    print(f"[DEBUG] Term '{term}' NOT FOUND in index")
            
            # Step 2: Candidate retrieval - UPDATED HYBRID METHOD
            candidates = self._retrieve_candidates(query_terms)
            
            if not candidates:
                search_time = (time.time() - start_time) * 1000
                return SearchResponse(
                    results=[],
                    total_results=0,
                    query=query_obj.query,
                    search_time_ms=round(search_time, 2),
                    page=query_obj.page,
                    per_page=query_obj.per_page,
                    total_pages=0,
                    suggestions=self._generate_suggestions(query_obj.query)
                )
            
            # Step 3: Ranking
            ranked = self._rank_documents(
                candidates, 
                query_terms,
                scoring_algorithm='bm25'
            )
            
            # Agar ranking ke baad bhi koi result nahi bacha toh early return
            if not ranked:
                search_time = (time.time() - start_time) * 1000
                return SearchResponse(
                    results=[],
                    total_results=0,
                    query=query_obj.query,
                    search_time_ms=round(search_time, 2),
                    page=query_obj.page,
                    per_page=query_obj.per_page,
                    total_pages=0,
                    suggestions=self._generate_suggestions(query_obj.query)
                )
            
            # Step 4: Pagination
            total_results = len(ranked)
            total_pages = (total_results + query_obj.per_page - 1) // query_obj.per_page
            
            start_idx = (query_obj.page - 1) * query_obj.per_page
            end_idx = start_idx + query_obj.per_page
            
            page_results = ranked[start_idx:end_idx]
            
            # Step 5: Result objects create karte hain
            results = []
            for doc_id, score in page_results:
                result = self._create_search_result(doc_id, score, query_terms)
                if result:
                    results.append(result)
            
            # Step 6: Timing aur response creation
            search_time = (time.time() - start_time) * 1000
            
            response = SearchResponse(
                results=results,
                total_results=total_results,
                query=query_obj.query,
                search_time_ms=round(search_time, 2),
                page=query_obj.page,
                per_page=query_obj.per_page,
                total_pages=total_pages,
                suggestions=None if results else self._generate_suggestions(query_obj.query)
            )
            
            # Cache mein store karte hain
            if len(self.query_cache) >= self.cache_max_size:
                self.query_cache.clear()  # Simple clear, LRU implementation possible
            self.query_cache[cache_key] = response
            
            print(f"[RESULTS] Found {total_results} docs in {search_time:.2f}ms")
            
            return response
            
        except Exception as e:
            # Last resort error handling
            print(f"[CRITICAL] Unhandled exception in search: {e}")
            traceback.print_exc()
            
            # Return empty results instead of crashing
            search_time = (time.time() - start_time) * 1000
            return SearchResponse(
                results=[],
                total_results=0,
                query=query_obj.query,
                search_time_ms=round(search_time, 2),
                page=query_obj.page,
                per_page=query_obj.per_page,
                total_pages=0,
                suggestions=["Search temporarily unavailable"]
            )
    
    def quick_search(self, query_string: str, top_k: int = 10) -> List[SearchResult]:
        """
        Quick search method for simple use cases.
        
        Args:
            query_string: Raw query
            top_k: Kitne results chahiye
            
        Returns:
            List of SearchResult objects
        """
        try:
            query_obj = SearchQuery(query=query_string, per_page=top_k)
            response = self.search(query_obj)
            return response.results
        except Exception as e:
            print(f"[ERROR] quick_search failed: {e}")
            return []
    
    def _generate_suggestions(self, query: str) -> List[str]:
        """
        Query suggestions generate karta hai agar koi result nahi mila.
        
        Simple implementation: similar terms suggest karta hai index se.
        Future mein spell checking add kar sakte hain.
        
        Args:
            query: Original query
            
        Returns:
            List of suggestion strings
        """
        try:
            suggestions = []
            tokens = self._tokenize_query(query)
            
            # Har token ke liye index mein similar terms dhoondhte hain
            for token in tokens:
                for indexed_term in self.index.index.keys():
                    # Simple prefix matching
                    if indexed_term.startswith(token[:3]) and indexed_term != token:
                        suggestions.append(indexed_term)
                        if len(suggestions) >= 3:
                            break
            
            return suggestions[:3]  # Max 3 suggestions
        except Exception as e:
            print(f"[ERROR] _generate_suggestions failed: {e}")
            return []
    
    def get_index_stats(self) -> Dict:
        """Index ki statistics return karta hai."""
        try:
            return self.index.get_statistics()
        except Exception as e:
            print(f"[ERROR] get_index_stats failed: {e}")
            return {}
    
    def get_document_by_id(self, doc_id: str) -> Optional[Document]:
        """Document ID se full document return karta hai."""
        try:
            return self.index.get_document(doc_id)
        except Exception as e:
            print(f"[ERROR] get_document_by_id failed for {doc_id}: {e}")
            return None


# Testing ke liye
if __name__ == "__main__":
    print("=" * 60)
    print("SEARCH ENGINE TEST")
    print("=" * 60)
    
    engine = SearchEngine()
    
    # Index load karte hain
    if engine.load_index():
        # Test searches
        test_queries = [
            "python",
            "search engine",
            "tutorial",
            "machine learning"
        ]
        
        for query in test_queries:
            print(f"\n{'='*50}")
            print(f"Query: '{query}'")
            print('='*50)
            
            results = engine.quick_search(query, top_k=3)
            
            if results:
                for i, result in enumerate(results, 1):
                    print(f"\n{i}. {result.title} (Score: {result.score:.4f})")
                    print(f"   Path: {result.file_path}")
                    print(f"   Matched: {result.matched_terms}")
                    snippet = result.snippet[:100] if result.snippet else "No snippet"
                    print(f"   Snippet: {snippet}...")
            else:
                print("   Koi results nahi mile!")
                if results is not None:
                    suggestions = engine._generate_suggestions(query)
                    if suggestions:
                        print(f"   Suggestions: {suggestions}")
    else:
        print("❌ Index load nahi hui! Pehle indexer.py run karein.")