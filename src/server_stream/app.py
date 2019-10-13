#!/usr/bin/env python
from flask import Flask, render_template, Response, request, redirect, url_for
from camera_chess import Camera, CameraMode

app = Flask(__name__)


def gen(camera):
    while True:
        frame = camera.get_frame()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')


@app.route('/video_feed')
def video_feed():
    return Response(gen(Camera("http://100.66.103.27:8080/video")),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/', methods=['POST', 'GET'])
def index():
    if request.method == "POST":
        video_source = request.form.get("video_source")
        Camera.set_video_source(video_source)

        if Camera.check_video_source():
            return redirect(url_for('ches_chessboard'), code=302)

    return render_template('index.html')


@app.route('/conf/chessboard', methods=['GET', 'POST'])
def ches_chessboard():
    Camera.board_corner = None
    Camera.M = None
    if request.method == "POST":
        Camera.find_corner()
        return redirect(url_for('set_position'), code=302)
    Camera.set_mode(CameraMode.FRAME_REAL)
    return render_template('conf_chess.html')


@app.route('/conf/chess', methods=['POST', 'GET'])
def set_position():
    if request.method == "POST":
        return redirect(url_for('chess_game'), code=302)
    return render_template('set_position.html')


@app.route('/game/chessboard')
def chess_game():
    if Camera.camera_mode != CameraMode.FRAME_GAME:
        Camera.set_mode(CameraMode.FRAME_GAME)
    return render_template('chess_game.html')


if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)