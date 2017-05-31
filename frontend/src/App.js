import React, { Component } from 'react';
import AppMenu from './components/Menu'
import Footer from './components/Footer'

class App extends Component {
    render() {
        return (
            <div>
                <AppMenu/>
                {this.props.children}
                <Footer/>
            </div>
        );
    }
}

export default App;
