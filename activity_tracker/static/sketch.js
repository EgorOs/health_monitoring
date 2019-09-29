const socket = io('http://localhost:5000');

function setup() {
  delay = new p5.Delay();
  frameRate(5);
  createCanvas(windowWidth, windowHeight);
  socket.on('connect', function() {
    socket.emit('my event', {data: 'I\'m connected!'});
});
}

function draw() {
  // put drawing code here
  socket.emit('request_data', {data: 1});
  socket.on('data_response', function(message) {
    clear();
    if (message.neck == 1){
          neck_msg = "Безопасное"}
    if (message.neck == 0){
          neck_msg = "Невозможно определить"}
    if (message.neck == -1){
          neck_msg = "Искривлённое (возможен остеохондроз)"}
    textSize(16);
    text("Положение шеи: " + neck_msg, 10, 30);

    if (message.spine == 1){
          spine_msg = "Прямая"}
    if (message.spine == 0){
          spine_msg = "Невозможно определить"}
    if (message.spine == -1){
          spine_msg = "Сутулая"}
    text("Осанка: " + spine_msg, 10, 70);

    text("Наклон плеч (в градусах): " + message.shoulder_skew  , 10, 110);



});
}

// setInterval(function(){ redraw()}, 300);