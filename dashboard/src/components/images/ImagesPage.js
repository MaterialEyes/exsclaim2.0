import React from 'react';
import { useState, useEffect } from 'react';
import { fetchArticles } from '../../services/ApiClient';
import { ImageList, ImageListItem } from '@mui/material';
import myData from '../../example-files/exsclaim.json';

const exampleItemData = [
    {
      img: 'https://images.unsplash.com/photo-1551963831-b3b1ca40c98e',
      title: 'Breakfast',
      author: '@bkristastucchio',
    },
    {
      img: 'https://images.unsplash.com/photo-1551782450-a2132b4ba21d',
      title: 'Burger',
      author: '@rollelflex_graphy726',
    },
    {
      img: 'https://images.unsplash.com/photo-1522770179533-24471fcdba45',
      title: 'Camera',
      author: '@helloimnik',
    },
    {
      img: 'https://images.unsplash.com/photo-1444418776041-9c7e33cc5a9c',
      title: 'Coffee',
      author: '@nolanissac',
    },
    {
      img: 'https://images.unsplash.com/photo-1533827432537-70133748f5c8',
      title: 'Hats',
      author: '@hjrc33',
    },
    {
      img: 'https://images.unsplash.com/photo-1558642452-9d2a7deb7f62',
      title: 'Honey',
      author: '@arwinneil',
    },
    {
      img: 'https://images.unsplash.com/photo-1516802273409-68526ee1bdd6',
      title: 'Basketball',
      author: '@tjdragotta',
    },
    {
      img: 'https://images.unsplash.com/photo-1518756131217-31eb79b20e8f',
      title: 'Fern',
      author: '@katie_wasserman',
    },
    {
      img: 'https://images.unsplash.com/photo-1597645587822-e99fa5d45d25',
      title: 'Mushrooms',
      author: '@silverdalex',
    },
    {
      img: 'https://images.unsplash.com/photo-1567306301408-9b74779a11af',
      title: 'Tomato basil',
      author: '@shelleypauls',
    },
    {
      img: 'https://images.unsplash.com/photo-1471357674240-e1a485acb3e1',
      title: 'Sea star',
      author: '@peterlaster',
    },
    {
      img: 'https://images.unsplash.com/photo-1589118949245-7d38baf380d6',
      title: 'Bike',
      author: '@southside_customs',
    },
  ];

//var data = JSON.parse(fs.readFileSync('../../example-files/exsclaim.json'));

console.log(myData["d0na00203h_fig1.jpg"]["figure_name"]);

const ImagesPage = () => {
    // get the articles
    const [articles, setArticles] = useState([])

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
    //
    // try combining the masonry image list with this:
    // https://colab.research.google.com/drive/1WB5EQxSn8lVwx7vDw0TT8ZpDn7jxYzh9#scrollTo=660oaoioWGek
    return (
      /*
       <div>
           {articles.length > 0 ? (
               <ImageList sx={{ width: 500, height: 450 }} cols={3} rowHeight={164}>
                    {data.map((item) => (
                    <ImageListItem key={item.img}>
                        <img
                        src={`${item.img}?w=164&h=164&fit=crop&auto=format`}
                        srcSet={`${item.img}?w=164&h=164&fit=crop&auto=format&dpr=2 2x`}
                        alt={item.title}
                        loading="lazy"
                        />
                    </ImageListItem>
                    ))}
                </ImageList>
           ) : (
               'No articles available'
           )}
       </div>
       */
       
       <img
        src={`${myData["d0na00203h_fig1.jpg"]["image_url"]}?w=164&h=164&fit=crop&auto=format`}
        srcSet={`${myData["d0na00203h_fig1.jpg"]["image_url"]}?w=164&h=164&fit=crop&auto=format&dpr=2 2x`}
        alt={myData["d0na00203h_fig1.jpg"]["figure_name"]}
        loading="lazy"
        />

    )
}

export default ImagesPage;