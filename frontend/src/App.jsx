import { useState, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import Search from './components/Search/Search'
import Results from './components/Results/Results'
import Footer from './components/Footer/Footer'
import styles from './App.module.css'

function App() {
    const [searchParams, setSearchParams] = useSearchParams()
    const [results, setResults] = useState([])
    const [totalResults, setTotalResults] = useState(0)
    const [searchTime, setSearchTime] = useState(0)
    const [hasSearched, setHasSearched] = useState(false)
    const [isLoading, setIsLoading] = useState(false)
    const [error, setError] = useState(null)
    const [expectedCount, setExpectedCount] = useState(3)

    const handleSearchResults = (data) => {
        setResults(data.results || [])
        setTotalResults(data.total_results || 0)
        setSearchTime(data.search_time_ms || 0)
        setHasSearched(true)
        setIsLoading(false)
        setError(null)
    }

    const handleLoading = () => {
        setIsLoading(true)
        setError(null)
        setResults([])
    }

    const handleError = (err) => {
        setError(err.message || 'Search failed')
        setIsLoading(false)
        setResults([])
    }

    const handleExpectedCount = (count) => {
        setExpectedCount(Math.min(count, 5))
    }

    const handleLogoClick = () => {
        window.location.href = '/'
    }

    return (
        <div className={styles.app}>
            <header className={styles.header}>
                <h1 className={styles.logo} onClick={handleLogoClick} style={{cursor: 'pointer'}}>
                    Sophon Search
                </h1>
            </header>
            
            <main className={styles.main}>
                <Search 
                    onResults={handleSearchResults}
                    onLoading={handleLoading}
                    onError={handleError}
                    onExpectedCount={handleExpectedCount}
                />
                
                {!hasSearched && !isLoading && (
                    <div className={styles.welcome}>
                        <p>Start typing to search...</p>
                    </div>
                )}
                
                {error && (
                    <div className={styles.error}>{error}</div>
                )}
                
                {(hasSearched || isLoading) && !error && (
                    <Results 
                        results={results}
                        totalResults={totalResults}
                        searchTime={searchTime}
                        isLoading={isLoading}
                        expectedCount={expectedCount}
                    />
                )}
            </main>
            
            <Footer />
        </div>
    )
}

export default App