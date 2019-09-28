const express = require('express');
const bodyParser = require('body-parser');
const cookieParser = require('cookie-parser');
const path = require('path');
const jwt = require('jsonwebtoken');
const mongoose = require('mongoose');
const User = require('./models/User');
const withAuth = require('./middleware');

// const session=require('express-session');

const app = express();
const http = require('http').Server(app);
const io = require('socket.io')(http);

const secret = 'proryv';

app.use(bodyParser.urlencoded({ extended: false }));
app.use(bodyParser.json());
app.use(cookieParser());
// app.use(session({secret:'proryv',cookie:{maxAge:6000}}));

const mongo_uri = 'mongodb+srv://mongodbuser:wordpass@cluster0-7z9zs.mongodb.net/test?retryWrites=true&w=majority';
mongoose.connect(mongo_uri, { useNewUrlParser: true }, function(err) {
  if (err) {
    throw err;
  } else {
    console.log(`Successfully connected to ${mongo_uri}`);
  }
});

app.use(express.static(path.join(__dirname, 'public')));

io.on('connection', socket => {
  // console.log('Client connection received');
  socket.emit('sendWarningToClient', {payload: 'causes'});
  
  socket.on('recievedSomething', (data) => {
      console.log(data);
  })
});

app.get('/', function (req, res) {
  res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

app.get('/api/home', function(req, res) {
  res.send('Welcome!');
});

app.get('/api/secret', withAuth, function(req, res) {
  res.send('warning');
  // io.on('noUser', socket => {
  //   res.send('user dissapear');
  //   socket.emit('sendNoUserMessage', {user: 'disabled'});
    
  //   socket.on('userComeBack', (data) => {
  //       console.log(data);
  //   });
  // });

  // io.on('niceHealth', socket => {
  //   res.send('Great!');
  //   socket.emit('sendHealthyMessage', {user: 'healthy'});
    
  //   socket.on('warning', (data) => {
  //       console.log(data);
  //   });
  // });

});

app.post('/api/register', function(req, res) {
  const { email, password } = req.body;
  const user = new User({ email, password });
  user.save(function(err) {
    if (err) {
      console.log(err);
      res.status(500).send("Error registering new user please try again.");
    } else {
      res.status(200).send("Welcome to the club!");
    }
  });
});

app.post('/api/authenticate', function(req, res) {
  const { email, password } = req.body;
  User.findOne({ email }, function(err, user) {
    if (err) {
      console.error(err);
      res.status(500)
        .json({
        error: 'Internal error please try again'
      });
    } else if (!user) {
      res.status(401)
        .json({
        error: 'Incorrect email or password'
      });
    } else {
      user.isCorrectPassword(password, function(err, same) {
        if (err) {
          res.status(500)
            .json({
            error: 'Internal error please try again'
          });
        } else if (!same) {
          res.status(401)
            .json({
            error: 'Incorrect email or password'
          });
        } else {
          // Issue token
          const payload = { email };
          const token = jwt.sign(payload, secret, {
            expiresIn: '1h'
          });
          // req.session.loggedIn=true;
          res.cookie('token', token, { httpOnly: true }).sendStatus(200);
        }
      });
    }
  });
});

// app.get('/api/logout', function(req, res){
//   req.session.loggedIn=false;
//   res.redirect('/');
// });

app.get('/checkToken', withAuth, function(req, res) {
  res.sendStatus(200);
});

app.listen(process.env.PORT || 8080);
