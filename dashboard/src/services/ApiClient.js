const baseUrl = "http://localhost:8000/api/v1";

export const fetchArticles = async () => {
    const res = await fetch(`${baseUrl}/articles/`)
    const data = await res.json()
    return data
}

export const fetchArticle = async (id) => {
    const res = await fetch(`${baseUrl}/articles/${id}/`)
    const data = await res.json()
    return data
}