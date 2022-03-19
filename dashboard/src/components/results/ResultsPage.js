import React from 'react'
import { useState, useEffect } from 'react'
import { fetchArticles } from '../../services/ApiClient'

const ResultsPage = () => {
    const [articles, setArticles] = useState([])

    useEffect(() => {
      const getArticles = async () => {
        const articlesFromServer = await fetchArticles()
        setArticles(articlesFromServer)
      }
      getArticles()
    }, [])

    return (
        <div>
            {articles.length > 0 ? (
                'articles found'
            ) : (
                'No articles available'
            )}

        </div>
    )
}

export default ResultsPage;