import React, { Component } from 'react';
import { Link, Route, Switch } from 'react-router-dom';
import withAuth from './withAuth';
import Home from './container/Home';
import Info from './container/Info';
import Login from './container/Login';
import Register from './container/Register';

class App extends Component {
  render() {
    return (
      <div>
        <ul>
          <li><Link to="/">Home</Link></li>
          <li><Link to="/info">Info</Link></li>
          <li><Link to="/login">Login</Link></li>
          <li><Link to="/signup"> Sign Up</Link></li>
          <li><Link to="/logout"> Log out</Link></li>
        </ul>

        <Switch>
          <Route path="/" exact component={Home} />
          <Route path="/secret" component={withAuth(Info)} />
          <Route path="/login" component={Login} />
          <Route path="/signup" component={Register} />
        </Switch>
      </div>
    );
  }
}

export default App;
