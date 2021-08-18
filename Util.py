#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
@author: BENULL
@time: 2021/8/18 13:46
"""
import cv2
import numpy as np

_OPENPOSE_POINT_COLORS = [
    (255, 255, 0), (255, 191, 0),
    (102, 255, 0), (255, 77, 0), (0, 255, 0),
    (255, 255, 77), (204, 255, 77), (255, 204, 77),
    (77, 255, 191), (255, 191, 77), (77, 255, 91),
    (255, 77, 204), (204, 255, 77), (255, 77, 191),
    (191, 255, 77), (255, 77, 127),
    (127, 255, 77), (255, 255, 0)]

_OPENPOSE_EDGES = [
    (0, 1),
    (1, 2), (2, 3), (3, 4),
    (1, 5), (5, 6), (6, 7),
    (1, 8), (8, 9), (9, 10),
    (1, 11), (11, 12), (12, 13),
    (0, 14), (14, 16),
    (0, 15), (15, 17)
]

_OPENPOSE_EDGE_COLORS = [
    (0, 0, 255),
    (0, 84, 255), (0, 168, 0), (0, 255, 168),
    (84, 0, 168), (84, 84, 255), (84, 168, 0),
    (84, 255, 84), (168, 0, 255), (168, 84, 255),
    (168, 168, 0), (168, 255, 84), (255, 0, 0),
    (255, 84, 255), (255, 168, 0),
    (255, 255, 84), (255, 0, 168)]

RENDER_CONFIG_OPENPOSE = {
    'edges': _OPENPOSE_EDGES,
    'edgeColors': _OPENPOSE_EDGE_COLORS,
    'edgeWidth': 2,
    'pointColors': _OPENPOSE_POINT_COLORS,
    'pointRadius': 3
}


def preparePose(pose, imageSize, invNorm):
    if invNorm == 'auto':
        invNorm = np.bitwise_and(pose >= 0, pose <= 1).all()

    if invNorm:
        w, h = imageSize
        trans = np.array([[w, 0], [0, h]])
        pose = (trans @ pose.T).T

    return pose.astype(np.int32)


def prepareBbox(box, imageSize, invNorm):
    if invNorm == 'auto':
        invNorm = np.bitwise_and(box >= 0, box <= 1).all()
    if invNorm:
        w, h = imageSize
        trans = np.array([[w, 0], [0, h]])
        box = (trans @ box.T).T
    return box.astype(np.int32)


def renderPose(image, poses, inplace: bool = True, inverseNormalization='auto'):
    """绘制骨架

    参数
        image: 原图

        poses: 一组或多组关节点坐标

        config: 配置项

        inplace: 是否绘制在原图上

        inverseNormalization` 是否[True|False]进行逆归一化, 当值为auto时将根据坐标值自动确定

    返回
        输出图像, inplace为True时返回image, 为False时返回新的图像
    """
    poses = np.array(poses)
    if not inplace:
        image = image.copy()

    if len(poses.shape) == 2:
        poses = poses[None, :, :2]

    if inverseNormalization not in ['auto', True, False]:
        raise ValueError(f'Unknown "inverseNormalization" value {inverseNormalization}')

    _isPointValid = lambda point: point[0] != 0 and point[1] != 0
    _FILL_CIRCLE = -1
    for pose in poses:
        pose = preparePose(pose, (image.shape[1], image.shape[0]), inverseNormalization)
        validPointIndices = set(filter(lambda i: _isPointValid(pose[i]), range(pose.shape[0])))
        for i, (start, end) in enumerate(RENDER_CONFIG_OPENPOSE['edges']):
            if start in validPointIndices and end in validPointIndices:
                cv2.line(image, tuple(pose[start]), tuple(pose[end]), RENDER_CONFIG_OPENPOSE['edgeColors'][i],
                         RENDER_CONFIG_OPENPOSE['edgeWidth'])

        for i in validPointIndices:
            cv2.circle(image, tuple(pose[i]), RENDER_CONFIG_OPENPOSE['pointRadius'],
                       tuple(RENDER_CONFIG_OPENPOSE['pointColors'][i]), _FILL_CIRCLE)

    return image


def renderBbox(image, box, inplace: bool = True, inverseNormalization='auto'):
    box = np.array(box)
    if not inplace:
        image = image.copy()

    if inverseNormalization not in ['auto', True, False]:
        raise ValueError(f'Unknown "inverseNormalization" value {inverseNormalization}')
    box = box.reshape(2, 2)
    box = prepareBbox(box, (image.shape[1], image.shape[0]), inverseNormalization)
    cv2.rectangle(image, tuple(box[0]), tuple(box[0]+box[1]), (255, 0, 0), thickness=1)
    return image


if __name__ == '__main__':
    box = np.array([
        0.269108878241645,
        0.4650149345397949,
        0.35790460374620225,
        0.5267127990722656
    ])
    pose = np.array([
        [
            0.39354264736175537,
            0.48819002509117126,
            0.923402726650238
        ],
        [
            0.43515947461128235,
            0.5560774803161621,
            0.7588653564453125
        ],
        [
            0.3103090524673462,
            0.5537365674972534,
            0.7842735648155212
        ],
        [
            0.2686921954154968,
            0.66610187292099,
            0.7693331837654114
        ],
        [
            0.2770155668258667,
            0.769103467464447,
            0.8043838143348694
        ],
        [
            0.5600099563598633,
            0.5584183931350708,
            0.7334572076797485
        ],
        [
            0.6265968084335327,
            0.6895113587379456,
            0.7678289413452148
        ],
        [
            0.609950065612793,
            0.8065586090087891,
            0.8505650162696838
        ],
        [
            0.36024925112724304,
            0.8018767237663269,
            0.6939839720726013
        ],
        [
            0.39354264736175537,
            0.9142420887947083,
            0.7941097021102905
        ],
        [
            0.43515947461128235,
            0.9844704866409302,
            0.47330009937286377
        ],
        [
            0.5100697875022888,
            0.8112404942512512,
            0.7796888947486877
        ],
        [
            0.4934230446815491,
            0.9329696893692017,
            0.709816575050354
        ],
        [
            0,
            0,
            0
        ],
        [
            0.36024925112724304,
            0.46946245431900024,
            0.9063138365745544
        ],
        [
            0.42683613300323486,
            0.46946245431900024,
            0.9237740635871887
        ],
        [
            0.32695576548576355,
            0.47882628440856934,
            0.5785307884216309
        ],
        [
            0.4850997030735016,
            0.4647805690765381,
            0.9087408185005188
        ]
    ])

    img = cv2.imread('/Users/benull/Downloads/3754.jpg')
    renderPoseImage = renderPose(img, pose, inplace=False)
    renderBboxImage = renderBbox(renderPoseImage, box, inplace=False)
    cv2.imshow('poseAndBox', renderBboxImage)
    cv2.waitKey()
