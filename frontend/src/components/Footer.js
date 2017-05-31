import React, { Component } from 'react';

class Footer extends Component {
    render() {
        return (
            <div className="ui divider"></div>,
                <div className="ui footer">
                    <div className="ui three column grid">
                        <div className="column centered">
                            @ 2017 <a>TTennis.life</a>
                            <div>Rating data a taken from
                                <a href="http://reiting.com.ua/"
                                   target="_blank">reiting.com.ua</a>
                            </div>
                        </div>
                        <div className="column centered">
                            <a className="item">
                                Urkainian</a> ·
                            <a className="active item">
                                Russina</a> ·
                        </div>
                        <div className="column centered">
                            <strong>Contacts:</strong>
                            <p><i className="mail icon"></i>email</p>
                        </div>
                    </div>
                </div>
        )
    }
}

export default Footer
