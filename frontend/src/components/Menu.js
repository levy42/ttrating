import React, { Component } from 'react';
import { Menu, Dropdown } from 'semantic-ui-react'
import { Link } from 'react-router-dom'

class AppMenu extends Component {
    state = {activeItem: 'home'};

    handleItemClick = (e, { name }) => this.setState({activeItem: name});

    render() {
        const { activeItem } = this.state;
        return (
            <Menu fixed="top" borderless size="huge">
                <Menu.Item header>
                    TTennis.life
                </Menu.Item>
                <Menu.Item as={Link} icon="bar chart" name="Statistics"
                           to="/statistics"/>
                <Menu.Item as={Link} name="Tournaments" icon="trophy"
                           to="/tournaments"/>
                <Menu.Item as={Link} name="Rating" icon="table"
                           to="/rating"/>
                <Menu.Item as={Link} name="World rating" icon="world"
                           to="/world-rating"/>
                <Menu.Item as={Link} name="Game search" icon="search"
                           to="/game-search"/>
                <Menu.Item name="About" icon="info circle"/>
            </Menu>
        )
    }
}

export default AppMenu