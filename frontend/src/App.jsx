import { useState, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import Search from './components/Search/Search'
import Results from './components/Results/Results'
import Footer from './components/Footer/Footer'
import { searchDocuments, searchWeb } from './api/api'
import styles from './App.module.css'

function App() {
    const [searchParams, setSearchParams] = useSearchParams()
    const [localResults, setLocalResults] = useState([])
    const [webResults, setWebResults] = useState({ wikipedia: null, web_results: [] })
    const [totalResults, setTotalResults] = useState(0)
    const [searchTime, setSearchTime] = useState(0)
    const [hasSearched, setHasSearched] = useState(false)
    const [isLoading, setIsLoading] = useState(false)
    const [error, setError] = useState(null)
    const [expectedCount, setExpectedCount] = useState(3)

    // URL se query read karke auto search
    // useEffect(() => {
    //     const urlQuery = searchParams.get('q')
    //     if (urlQuery) {
    //         performSearch(urlQuery)
    //     }
    // }, [])

    const performSearch = async (query) => {
        if (!query.trim()) return
        
        setIsLoading(true)
        setError(null)
        setLocalResults([])
        setWebResults({ wikipedia: null, web_results: [] })

        try {
            // Dono search parallel mein
            const [localData, webData] = await Promise.all([
                searchDocuments(query),
                searchWeb(query)
            ])

            setLocalResults(localData.results || [])
            setWebResults(webData)
            setTotalResults((localData.total_results || 0) + (webData.web_results?.length || 0))
            setSearchTime(localData.search_time_ms || 0)
            setHasSearched(true)
            setSearchParams({ q: query })
        } catch (err) {
            setError(err.message || 'Search failed')
        } finally {
            setIsLoading(false)
        }
    }

    const handleSearchResults = (data) => {
        // Ab use nahi hoga, direct performSearch call hota hai
    }

    const handleLoading = () => {
        // Ab use nahi hoga
    }

    const handleError = (err) => {
        // Ab use nahi hoga
    }

    const handleExpectedCount = (count) => {
        setExpectedCount(Math.min(count, 5))
    }

    const handleLogoClick = () => {
        window.location.href = '/'
    }

    // Search component ko performSearch pass karo
    const handleSearch = (query) => {
        performSearch(query)
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
                    onSearch={handleSearch}
                    onExpectedCount={handleExpectedCount}
                    initialQuery={searchParams.get('q') || ''}
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
                        localResults={localResults}
                        webResults={webResults}
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