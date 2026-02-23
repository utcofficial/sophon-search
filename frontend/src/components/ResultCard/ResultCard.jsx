import styles from './ResultCard.module.css'

function ResultCard({ result, isSkeleton = false }) {
    // Skeleton card
    if (isSkeleton) {
        return (
            <article className={`${styles.resultCard} ${styles.skeletonCard}`}>
                <div className={styles.resultHeader}>
                    <div className={styles.fileInfo}>
                        <div className={`${styles.skeletonIcon} ${styles.shimmer}`}></div>
                        <div className={`${styles.skeletonText} ${styles.shimmer} ${styles.skeletonPath}`}></div>
                    </div>
                    <div className={`${styles.skeletonScore} ${styles.shimmer}`}></div>
                </div>
                
                <div className={`${styles.skeletonTitle} ${styles.shimmer}`}></div>
                
                <div className={styles.skeletonSnippet}>
                    <div className={`${styles.skeletonLine} ${styles.shimmer}`}></div>
                    <div className={`${styles.skeletonLine} ${styles.shimmer}`}></div>
                    <div className={`${styles.skeletonLineShort} ${styles.shimmer}`}></div>
                </div>
                
                <div className={styles.meta}>
                    <div className={`${styles.skeletonMeta} ${styles.shimmer}`}></div>
                </div>
            </article>
        )
    }

    // Normal result
    const highlightSnippet = (snippet, matchedTerms) => {
        if (!matchedTerms || matchedTerms.length === 0) return snippet
        
        let highlighted = snippet
        matchedTerms.forEach(term => {
            const regex = new RegExp(`(${term})`, 'gi')
            highlighted = highlighted.replace(regex, '<mark>$1</mark>')
        })
        
        return highlighted
    }

    const highlightedSnippet = highlightSnippet(
        result.snippet || 'No preview available',
        result.matched_terms || []
    )

    return (
        <article className={styles.resultCard}>
            <div className={styles.resultHeader}>
                <div className={styles.fileInfo}>
                    <svg 
                        className={styles.fileIcon}
                        viewBox="0 0 24 24" 
                        fill="none" 
                        stroke="currentColor" 
                        strokeWidth="2"
                    >
                        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                        <polyline points="14 2 14 8 20 8"></polyline>
                    </svg>
                    <span className={styles.filePath}>{result.doc_id}</span>
                </div>
                <span className={styles.score}>
                    Score: {result.score?.toFixed(4) || '0.0000'}
                </span>
            </div>
            
            <h3 className={styles.title}>{result.title || 'Untitled'}</h3>
            
            <p 
                className={styles.snippet}
                dangerouslySetInnerHTML={{ __html: highlightedSnippet }}
            />
            
            <div className={styles.meta}>
                <span className={styles.metaItem}>
                    {result.file_size ? `${(result.file_size / 1024).toFixed(1)} KB` : 'Size unknown'}
                </span>
                {result.matched_terms && result.matched_terms.length > 0 && (
                    <span className={styles.metaItem}>
                        Matched: {result.matched_terms.join(', ')}
                    </span>
                )}
            </div>
        </article>
    )
}

export default ResultCard