import ResultCard from '../ResultCard/ResultCard'
import styles from './Results.module.css'

function Results({ localResults, webResults, totalResults, searchTime, isLoading, expectedCount }) {

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

    const hasLocal = localResults && localResults.length > 0
    const hasWeb = webResults && (webResults.wikipedia || (webResults.web_results && webResults.web_results.length > 0))

    if (!hasLocal && !hasWeb) {
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
            
            {/* Wikipedia Answer Box */}
            {webResults.wikipedia && (
                <div className={styles.wikipediaBox}>
                    <h3>{webResults.wikipedia.title}</h3>
                    <p>{webResults.wikipedia.extract}</p>
                    <a href={webResults.wikipedia.url} target="_blank" rel="noopener noreferrer">
                        Read more on Wikipedia →
                    </a>
                </div>
            )}
            
            {/* Web Results */}
            {webResults.web_results && webResults.web_results.length > 0 && (
                <div className={styles.section}>
                    <h4 className={styles.sectionTitle}>From the web</h4>
                    {webResults.web_results.map((result, index) => (
                        <div key={index} className={styles.webResult}>
                            <a href={result.url} target="_blank" rel="noopener noreferrer" className={styles.webTitle}>
                                {result.title}
                            </a>
                            <p className={styles.webSnippet}>{result.snippet}</p>
                            <span className={styles.webUrl}>{result.url}</span>
                        </div>
                    ))}
                </div>
            )}
            
            {/* Local File Results */}
            {hasLocal && (
                <div className={styles.section}>
                    <h4 className={styles.sectionTitle}>From the documents</h4>
                    <div className={styles.resultsList}>
                        {localResults.map((result, index) => (
                            <ResultCard key={result.doc_id || index} result={result} />
                        ))}
                    </div>
                </div>
            )}
        </div>
    )
}

export default Results