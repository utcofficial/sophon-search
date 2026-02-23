const API_URL = 'http://127.0.0.1:8000';

// Main search API call
export const searchDocuments = async (query, page = 1, perPage = 10) => {
    try {
        const response = await fetch(`${API_URL}/api/search`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                query: query,
                page: page,
                per_page: perPage
            })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        return await response.json();
    } catch (error) {
        console.error('Search error:', error);
        throw error;
    }
};

// Get only count (fast call for skeleton)
export const getSearchCount = async (query) => {
    try {
        const response = await fetch(`${API_URL}/api/search`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                query: query,
                page: 1,
                per_page: 1
            })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        return data.total_results || 0;
    } catch (error) {
        console.error('Count error:', error);
        return 3;
    }
};

// Get autocomplete suggestions
export const getSuggestions = async (query) => {
    if (!query || query.length < 2) return [];
    
    try {
        const response = await fetch(`${API_URL}/api/suggest?q=${encodeURIComponent(query)}`);
        const data = await response.json();
        return data.suggestions || [];
    } catch (error) {
        console.error('Suggestions error:', error);
        return [];
    }
};

// Get health status
export const getHealth = async () => {
    try {
        const response = await fetch(`${API_URL}/health`);
        return await response.json();
    } catch (error) {
        console.error('Health check error:', error);
        return null;
    }
};