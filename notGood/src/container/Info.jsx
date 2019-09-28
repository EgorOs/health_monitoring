import React, { Component } from 'react';

export default class Info extends Component {
  constructor() {
    super();
    this.state = {
      message: 'Loading...'
    }
  }

  componentDidMount() {
    fetch('/api/secret')
      .then(res => res.text())
      .then(res => this.setState({message: res}));
  }

  render() {
    return (
      <div>
        <h1>Warnings</h1>
        <p>{this.state.message}</p>
      </div>
    );
  }
}