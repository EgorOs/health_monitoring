import React, { Component } from 'react';
import socketIOClient from "socket.io-client";

export default class Info extends Component {
  constructor() {
    super();
    this.state = {
      message: 'Loading...',
      endpoint: "http://localhost:8080"
    }
  }

  componentDidMount() {
    fetch('/api/secret')
      .then(res => res.text())
      .then(res => this.setState({message: res}));
    const { endpoint } = this.state;
    const socket = socketIOClient(endpoint);
    socket.on("sendWarningToClient", data => this.setState({ message: data }));
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