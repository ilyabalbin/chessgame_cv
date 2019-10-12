import cv2
import chess
import numpy as np

from base_camera import BaseCamera


class Camera(BaseCamera):
    video_source = 0
    width = 400
    board_corner = None
    M = None

    def __init__(self, source=0):
        Camera.set_video_source(source)
        super(Camera, self).__init__()

    @staticmethod
    def set_video_source(source):
        Camera.video_source = source

    @staticmethod
    def frame_real():
        camera = cv2.VideoCapture(Camera.video_source)

        if not camera.isOpened():
            raise RuntimeError('Could not start camera.')

        while True:
            # read current frame
            _, frame = camera.read()

            if Camera.M is not None:
                frame = cv2.warpPerspective(frame, Camera.M, (Camera.width, Camera.width))

            yield frame
            camera.grab()

    @staticmethod
    def frame_diff(frame_other):
        kernel = np.ones((5, 5,))

        for frame in Camera.frame_real():
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            diff = cv2.absdiff(frame, frame_other)
            diff = cv2.threshold(diff, 10, 150, cv2.THRESH_BINARY)[1]

            diff = cv2.erode(diff, kernel)
            diff = cv2.dilate(diff, kernel)
            yield diff

    @staticmethod
    def frames():
        cap = cv2.VideoCapture(Camera.video_source)
        _, first_img = cap.read()
        first_img = cv2.cvtColor(first_img, cv2.COLOR_BGR2GRAY)

        for frame in Camera.frame_diff(first_img):
            yield cv2.imencode('.jpg', frame)[1].tobytes()


    @staticmethod
    def find_corner():
        camera = cv2.VideoCapture(Camera.video_source)

        ret = False
        res = None
        for _ in range(100):
            ret, first_frame = camera.read()
            ret, res = cv2.findChessboardCorners(first_frame, (7, 7))

        if not ret:
            raise ValueError('Chessboard dont on board or dont empty ')

        min_x, max_x = res[:, 0].min(), res[:, 0].max()
        min_y, max_y = res[:, 1].min(), res[:, 1].max()

        dx = (max_x - min_x) / 6
        dy = (max_y - min_y) / 6

        board_corner = np.array([
            [min_x - dx, max_y + dy],
            [min_x - dx, min_y - dy],
            [max_x + dx, max_y + dy],
            [max_x + dx, min_y - dy],
        ])

        Camera.board_corner = np.vstack((res, board_corner))

        pst1 = np.float32(board_corner)
        pst2 = np.float32([[0, 0], [Camera.width, 0], [0, Camera.width], [Camera.width, Camera.width]])

        Camera.M = cv2.getPerspectiveTransform(pst1, pst2)
