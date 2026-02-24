import { useState, useEffect, useRef } from 'react'
import { useSearchParams } from 'react-router-dom'
import { getSuggestions } from '../../api/api'  // searchDocuments hata diya kyunki App.jsx mein hai
import styles from './Search.module.css'

// Naye props: onSearch (performSearch ka reference), initialQuery (URL se)
function Search({ onSearch, onExpectedCount, initialQuery }) {
    const [searchParams, setSearchParams] = useSearchParams()
    // initialQuery prop se set karo, ya URL se lo
    const [query, setQuery] = useState(initialQuery || searchParams.get('q') || '')
    const [suggestions, setSuggestions] = useState([])
    const [showSuggestions, setShowSuggestions] = useState(false)
    const [activeSuggestion, setActiveSuggestion] = useState(-1)
    const inputRef = useRef(null)
    const suggestionsRef = useRef(null)
    const justSearched = useRef(false)

    // URL query change hone pe update karo
    useEffect(() => {
        if (initialQuery !== undefined) {
            setQuery(initialQuery)
        }
    }, [initialQuery])

    // Suggestions fetch karo
    useEffect(() => {
        // Agar abhi search hua hai toh mat fetch karo
        if (justSearched.current) {
            justSearched.current = false
            return
        }

        const fetchSuggestions = async () => {
            if (query.length >= 2) {
                const data = await getSuggestions(query)
                setSuggestions(data)
                setShowSuggestions(data.length > 0)
            } else {
                setSuggestions([])
                setShowSuggestions(false)
            }
        }

        const timeoutId = setTimeout(fetchSuggestions, 150)
        return () => clearTimeout(timeoutId)
    }, [query])

    // Form submit - App.jsx ke performSearch ko call karo
    const handleSubmit = (e) => {
        e.preventDefault()
        if (!query.trim()) return
        
        // Suggestions hide karo
        setShowSuggestions(false)
        setSuggestions([])
        justSearched.current = true
        
        // Parent ko bolo search kare
        onSearch(query)
    }

    // Suggestion click - direct search
    const handleSuggestionClick = (suggestion) => {
        setQuery(suggestion)
        setShowSuggestions(false)
        setSuggestions([])
        justSearched.current = true
        
        // Parent ko bolo search kare
        onSearch(suggestion)
    }

    // Keyboard navigation
    const handleKeyDown = (e) => {
        if (!showSuggestions) return

        switch (e.key) {
            case 'ArrowDown':
                e.preventDefault()
                setActiveSuggestion(prev => 
                    prev < suggestions.length - 1 ? prev + 1 : prev
                )
                break
            case 'ArrowUp':
                e.preventDefault()
                setActiveSuggestion(prev => prev > 0 ? prev - 1 : -1)
                break
            case 'Enter':
                if (activeSuggestion >= 0) {
                    e.preventDefault()
                    handleSuggestionClick(suggestions[activeSuggestion])
                }
                break
            case 'Escape':
                setShowSuggestions(false)
                break
        }
    }

    // Click outside pe suggestions band karo
    useEffect(() => {
        const handleClickOutside = (e) => {
            if (suggestionsRef.current && !suggestionsRef.current.contains(e.target)) {
                setShowSuggestions(false)
            }
        }

        document.addEventListener('mousedown', handleClickOutside)
        return () => document.removeEventListener('mousedown', handleClickOutside)
    }, [])

    return (
        <div className={styles.searchContainer} ref={suggestionsRef}>
            <form onSubmit={handleSubmit} className={styles.searchForm}>
                <div className={styles.inputWrapper}>
                    <svg 
                        className={styles.searchIcon} 
                        viewBox="0 0 24 24" 
                        fill="none" 
                        stroke="currentColor" 
                        strokeWidth="2"
                    >
                        <circle cx="11" cy="11" r="8"></circle>
                        <path d="m21 21-4.35-4.35"></path>
                    </svg>
                    
                    <input
                        ref={inputRef}
                        type="text"
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                        onKeyDown={handleKeyDown}
                        onFocus={() => {
                            if (query.length >= 2 && !justSearched.current) {
                                setShowSuggestions(true)
                            }
                        }}
                        placeholder="Search..."
                        className={styles.searchInput}
                        autoComplete="off"
                    />
                    
                    {query && (
                        <button 
                            type="button"
                            className={styles.clearButton}
                            onClick={() => {
                                setQuery('')
                                setSuggestions([])
                                setShowSuggestions(false)
                                justSearched.current = false
                                inputRef.current.focus()
                            }}
                        >
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                <line x1="18" y1="6" x2="6" y2="18"></line>
                                <line x1="6" y1="6" x2="18" y2="18"></line>
                            </svg>
                        </button>
                    )}
                </div>
                
                <button type="submit" className={styles.searchButton}>
                    Search
                </button>
            </form>

            {showSuggestions && suggestions.length > 0 && (
                <ul className={styles.suggestionsList}>
                    {suggestions.map((suggestion, index) => (
                        <li
                            key={index}
                            className={`${styles.suggestionItem} ${
                                index === activeSuggestion ? styles.active : ''
                            }`}
                            onClick={() => handleSuggestionClick(suggestion)}
                            onMouseEnter={() => setActiveSuggestion(index)}
                        >
                            <svg 
                                className={styles.suggestionIcon}
                                viewBox="0 0 24 24" 
                                fill="none" 
                                stroke="currentColor" 
                                strokeWidth="2"
                            >
                                <circle cx="11" cy="11" r="8"></circle>
                                <path d="m21 21-4.35-4.35"></path>
                            </svg>
                            <span>{suggestion}</span>
                        </li>
                    ))}
                </ul>
            )}
        </div>
    )
}

export default Search