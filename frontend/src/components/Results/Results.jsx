import ResultCard from '../ResultCard/ResultCard'
import styles from './Results.module.css'

function Results({ results, totalResults, searchTime, isLoading, expectedCount }) {

    if (isLoading) {
        return (
            <div className={styles.resultsContainer}>
                <div className={styles.resultsHeader}>
                    <span className={`${styles.stats} ${styles.skeletonStats}`}>
                        Searching...
                    </span>
                </div>
                
                <div className={styles.resultsList}>
                    {Array.from({ length: expectedCount }, (_, index) => (
                        <ResultCard key={`skeleton-${index}`} isSkeleton={true} />
                    ))}
                </div>
            </div>
        )
    }

    if (results.length === 0) {
        return (
            <div className={styles.noResults}>
                <p>No results found</p>
            </div>
        )
    }

    return (
        <div className={styles.resultsContainer}>
            <div className={styles.resultsHeader}>
                <span className={styles.stats}>
                    About {totalResults} results ({(searchTime / 1000).toFixed(3)} seconds)
                </span>
            </div>
            
            <div className={styles.resultsList}>
                {results.map((result, index) => (
                    <ResultCard key={result.doc_id || index} result={result} />
                ))}
            </div>
        </div>
    )
}

export default Results