import React from 'react'
import { useState, useEffect } from 'react'
import { fetchArticles } from '../../services/ApiClient'

// Old results page
// THIS PAGE IS NOT USED IN THE CURRENT UI

const ResultsPage = () => {
    const [articles, setArticles] = useState([])

    // I thought this was helpful: https://www.youtube.com/watch?v=iEVcCdbF1WQ
    useEffect(() => {
      const getArticles = async () => {
        const articlesFromServer = await fetchArticles()
        setArticles(articlesFromServer)
      }
      getArticles()
    }, [])

    // In the real app, we'll want to show subfigures, not articles. You 
    // can retrieve them from their figure urls, and then you'll have to crop
    // them. The old ui had an image only results page that I liked, and one
    // with the resolved metadata (caption, scale, label, etc.). This is where
    // something like https://mui.com/components/data-grid/ and/or
    // https://mui.com/components/image-list/#masonry-image-list will come in
    // handy (masonry is good because it will allow images with different sizes
    // to fit together well)
    return (
        <div>
            {articles.length > 0 ? (
                <div>
                    {articles.map((article) =>(
                        <li><a href={article.url}>{article.title}</a></li>
                    ))}
                </div>
            ) : (
                'No articles available'
            )}
        </div>
    )
}

export default ResultsPage;