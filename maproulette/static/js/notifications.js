notifications = {
  queue: [],
  running: false,
  
  emit: function(text, time) {
    if (time == null) {
      time = 3;}
    this.queue.push({
      text: text,
      time: time});
    if (!this.running) {
      this.running = true;
      return display();}},
  
  display: function() {
    var msgObj, text, time;
    msgObj = this.queue.shift();
    text = msgObj.text;
    time = msgObj.time * 1000;
    $("msgBox").html(text).fadeIn();
    $("msgBox").css("display", "block");
    return setTimeout((function() {
      return this.close();
    }), time);},
  
  clear: function() {
    this.queue = [];
    return this.close();},
  
  close: function() {
    $("msgBox").fadeOut();
    if (this.queue.length === 0) {
      return this.running = false;
    } else {
      return this.display();
    }}
};
