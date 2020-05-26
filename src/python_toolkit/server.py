import zmq
import base64
import numpy as np
import time
import cv2
import arm_position
import json

context = zmq.Context()
socket = context.socket(zmq.REP)
socket.bind('tcp://*:5555')

while True:
    since = time.time()
    request = socket.recv_multipart()

    # first part of the request encodes operation
    if request[0].decode('utf-8') == 'F':
        frame_byte = base64.b64decode(request[1])

        img_arr = np.frombuffer(frame_byte, np.uint8)
        # reshape with correct dimensions
        img = img_arr.reshape((480, 640, 4), order='C')
        # remove alpha channel
        img_rgb = img[:, :, :3]
        img_bgr = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)
        img_bgr = cv2.flip(img_bgr, 0)
        cv2.imshow("image", img_bgr)
        cv2.waitKey(1)

        print('Received request, time: {}'.format(time.time() - since))

        socket.send(b'Image data')
    # elif request[0].decode('utf-8') == 'A':
    #     anchors = arm_position.get_all_voxels('poses.db')
    #     anchors_json = {'anchors': anchors}
    #     socket.send(json.dumps(anchors_json).encode('utf-8'))
    elif request[0].decode('utf-8') == 'C':
        req = json.loads(request[1])
        anchors = arm_position.get_voxels_constrained('poses.db', *req.values())
        socket.send(json.dumps(anchors).encode('utf-8'))
    elif request[0].decode('utf-8') == 'P':
        req = json.loads(request[1])
        poses = arm_position.get_voxel_poses('poses.db', *req.values())
        socket.send(json.dumps(poses).encode('utf-8'))
    elif request[0].decode('utf-8') == 'L':
        limits = arm_position.get_interaction_space_limits('poses.db')
        socket.send(json.dumps(limits).encode('utf-8'))
    else:
        socket.send(b'Error')
