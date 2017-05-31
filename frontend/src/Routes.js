import React from 'react'
import App from './App'
import Rating from './components/Rating'
import Tournaments from './components/Tournaments'
import Statictics from './components/Statistics'
import WorldRating from './components/WorldRating'
import GameSearch from './components/GameSearch'

import { BrowserRouter, Route } from 'react-router-dom'

const Routes = () => (
    <BrowserRouter>
        <App>
            <Route path="/rating" component={Rating}/>
            <Route path="/tournaments" component={Tournaments}/>
            <Route path="/statistics" component={Statictics}/>
            <Route path="/world-rating" component={WorldRating}/>
            <Route path="/game-search" component={GameSearch}/>
        </App>
    </BrowserRouter>
);

export default Routes;
