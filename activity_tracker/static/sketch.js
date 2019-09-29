const socket = io('http://localhost:5000');

function setup() {
  delay = new p5.Delay();
  frameRate(50);
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
    var body_state = message.PoseEstimation
    var mouse_speed = message.MouseTracker
    var apm = message.ActionsPerMinute

    textSize(16);

    if (body_state.neck == 1){
          fill(0, 172, 103);
          neck_msg = "Безопасное"}
    if (body_state.neck == 0){
          fill(0, 102, 153);
          neck_msg = "Невозможно определить"}
    if (body_state.neck == -1){
          fill(190, 50, 100);
          neck_msg = "Искривлённое (возможен остеохондроз)"}
    text("Положение шеи: " + neck_msg, 10, 30);

    if (body_state.spine == 1){
          fill(0, 172, 103);
          spine_msg = "Прямая"}
    if (body_state.spine == 0){
          fill(0, 102, 153);
          spine_msg = "Невозможно определить"}
    if (body_state.spine == -1){
          fill(190, 50, 100);
          spine_msg = "Сутулая"}
    text("Осанка: " + spine_msg, 10, 70);

    fill(0,0,0);
    text("Наклон плеч (в градусах): " + body_state.shoulder_skew  , 10, 110);

    fill(0,0,0);
    text("Число морганий: " + body_state.blinks  , 10, 130);

    text("Скорость мыши, ось X: " + mouse_speed.speed_x, 10, 190);
    text("Скорость мыши, ось Y: " + mouse_speed.speed_y, 10, 230);

    text("Действий в минуту: " + apm.actions, 10, 270);



});
}

// setInterval(function(){ redraw()}, 300);