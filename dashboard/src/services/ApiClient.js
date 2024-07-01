// some functions to get data from the API
const baseUrl = "http://localhost:8000/api/v1";

export const fetchArticles = async () => {
    const res = await fetch(`${baseUrl}/articles/`)
    const data = await res.json()
    return data.results
}

export const fetchArticle = async (id) => {
    const res = await fetch(`${baseUrl}/articles/${id}/`)
    const data = await res.json()
    return data
}

export const fetchFigures = async (num) => {
    const res = await fetch(`${baseUrl}/figures/?page=${num}`)
    const data = await res.json()
    return data
}

export const fetchSubFigures = async (num) => {
    const res = await fetch(`${baseUrl}/subfigures/?page=${num}`)
    const data = await res.json()
    return data
}