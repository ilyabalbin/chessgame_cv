import time

import cv2
import chess
import numpy as np

import chess.svg
from PIL import Image
from io import BytesIO
import cairosvg

from base_camera import BaseCamera


# Translation mode
class CameraMode(object):
    FRAME_REAL = 0
    FRAME_BUBBLE = 1
    FRAME_GAME = 2


class Camera(BaseCamera):
    video_source = ''
    width = 400
    board_corner = None
    M = None
    board = None
    camera_mode = CameraMode.FRAME_REAL

    def __init__(self, source='', board = None):
        Camera.set_video_source(source)
        Camera.set_board(board)
        super(Camera, self).__init__()

    @staticmethod
    def set_board(board):
        if board is None:
            board = chess.Board()
        Camera.board = board

    @staticmethod
    def frame_real():
        camera = cv2.VideoCapture(Camera.video_source)
        cv2.waitKey(0)

        if not camera.isOpened():
            raise RuntimeError('Could not start camera.')

        while True:
            # read current frame
            _, frame = camera.read()

            if Camera.M is not None:
                frame = cv2.warpPerspective(frame, Camera.M, (Camera.width, Camera.width))

            yield frame
            # yield cv2.imencode('.jpg', frame)[1].tobytes()
            camera.grab()

    @staticmethod
    def set_mode(camera_mode):
        Camera.camera_mode = camera_mode
        if BaseCamera.thread is not None:
            BaseCamera.break_thread = True
            BaseCamera.thread = None

    @staticmethod
    def set_video_source(source):
        if source.isdigit():
            Camera.video_source = int(source)
        else:
            Camera.video_source = source

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
        print('camera mode:',  Camera.camera_mode)
        if Camera.camera_mode == CameraMode.FRAME_REAL:
            for frame in Camera.frame_real():
                yield cv2.imencode('.jpg', frame)[1].tobytes()
            # return Camera.frame_real()
        # elif Camera.camera_mode == CameraMode.FRAME_BUBBLE:
        #
        #     cap = cv2.VideoCapture(Camera.video_source)
        #     _, first_img = cap.read()
        #
        #     first_img = cv2.cvtColor(first_img, cv2.COLOR_BGR2GRAY)
        #     for frame in Camera.frame_diff(first_img):
        #         yield cv2.imencode('.jpg', frame)[1].tobytes()

        elif Camera.camera_mode == CameraMode.FRAME_GAME:
            for frame in Camera._game():
            #     yield frame
            # return Camera._game()
                yield cv2.imencode('.jpg', frame)[1].tobytes()
        raise ValueError('Bad camera_mode')

    @staticmethod
    def find_corner():
        camera = cv2.VideoCapture(Camera.video_source)

        ret = False
        res = None
        for _ in range(100):
            ret, first_frame = camera.read()
            ret, res = cv2.findChessboardCorners(first_frame, (7, 7))
            if ret:
                break
        if not ret:
            raise ValueError('Chessboard dont on board or dont empty ')

        res = res[:, 0, :]

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

    @staticmethod
    def _hand_on(frame_cur, frame_last, thr=0.1):

        diff = Camera._get_frame_diff(frame_cur, frame_last)
        size = diff.shape[0]

        return (diff != 0).sum() / (size * size) > thr

    @staticmethod
    def _get_frame_diff(frame1, frame2):
        diff = cv2.absdiff(frame1, frame2)
        diff = cv2.threshold(diff, 10, 150, cv2.THRESH_BINARY)[1]

        kernel = np.ones((5, 5,))
        diff = cv2.erode(diff, kernel)
        diff = cv2.dilate(diff, kernel)

        return diff

    @staticmethod
    def _get_move(frame_cur, frame_last, thr=0.1):
        diff = Camera._get_frame_diff(frame_cur, frame_last)

        step = diff.shape[0] // 8

        change_square = []
        for i in range(8):
            for j in range(8):
                sub_diff = diff[step * i:step * (i + 1), step * j:step * (j + 1)]

                if (sub_diff != 0).sum() / (step * step) > thr:
                    change_square.append([i, j])

        moves = []
        for j, i in change_square:
            for l, k in change_square:
                moves.append(chess.Move(i + j * 8, k + l * 8))

        res_move = None
        for move in moves:
            if move in Camera.board.legal_moves:
                res_move = move
                break

        return res_move

    @staticmethod
    def check_video_source():
        print(f"Check {Camera.video_source}")
        camera = cv2.VideoCapture(Camera.video_source)

        _, t = camera.read()
        cv2.waitKey(0)
        res = camera.isOpened()
        # camera.release()

        return res

    @staticmethod
    def _game():
        print('In game')
        if Camera.board is None:
            raise ValueError('Miss Board')

        frame_last = next(Camera.frame_real())
        frame_last = cv2.cvtColor(frame_last, cv2.COLOR_BGR2GRAY)

        hand_on_last = False
        for frame in Camera.frame_real():
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            hand_on_cur = Camera._hand_on(frame, frame_last)
            hand_on_change = hand_on_cur ^ hand_on_last
            hand_on_last = hand_on_cur

            print("hand on" if hand_on_cur else "hand off")

            if hand_on_change and not hand_on_cur:
                print('yo')
                time.sleep(2)

                frame = next(Camera.frame_real())
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

                cur_move = Camera._get_move(frame, frame_last)
                print(cur_move)
                Camera.board.push(cur_move)

            svg_board = chess.svg.board(Camera.board)
            svg_board = cairosvg.svg2png(svg_board)

            temp_buff = BytesIO()
            temp_buff.write(svg_board)
            temp_buff.seek(0)

            im = Image.open(temp_buff)

            background = Image.new('RGBA', im.size,  (255, 255, 255))
            background.paste(im, im)

            im_jpg = np.array(background.convert('RGB'), dtype=np.uint8)

            yield im_jpg
