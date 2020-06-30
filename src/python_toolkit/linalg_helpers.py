import numpy as np
import math
import exceptions


class HomogeneousCoordinates:
    def __init__(self, position, rotation=(0, 0, 0)):
        rotation = rotation_matrix(*rotation)
        homogeneous = np.zeros((4, 4))
        homogeneous[:-1, :-1] = rotation
        homogeneous[:-1, 3] = position.T
        homogeneous[3, :] = [0, 0, 0, 1]
        self.matrix = homogeneous

    def set_rotation(self, x, y, z):
        self.matrix[:-1, :-1] = rotation_matrix(x, y, z)

    def get_pos(self):
        return self.matrix[:-1, 3]


def rotation_matrix(x, y, z):
    if x is None:
        rotation_x = np.identity(3)
    else:
        # x = np.deg2rad(x)
        rotation_x = np.array([[1, 0, 0],
                               [0, np.cos(x), -np.sin(x)],
                               [0, np.sin(x), np.cos(x)]])

    if y is None:
        rotation_y = np.identity(3)
    else:
        # y = np.deg2rad(y)
        rotation_y = np.array([[np.cos(y), 0, np.sin(y)],
                               [0, 1, 0],
                               [-np.sin(y), 0, np.cos(y)]])

    if z is None:
        rotation_z = np.identity(3)
    else:
        # z = np.deg2rad(z)
        rotation_z = np.array([[np.cos(z), -np.sin(z), 0],
                               [np.sin(z), np.cos(z), 0],
                               [0, 0, 1]])

    rotation = rotation_x @ rotation_y @ rotation_z
    #         rotation_matrix = rotation_y @ rotation_x @ rotation_z
    homogeneous = np.zeros((4, 4))
    homogeneous[:-1, :-1] = rotation
    homogeneous[:-1, 3] = [0, 0, 0]
    homogeneous[3, :] = [0, 0, 0, 1]
    return homogeneous

def magnitude(v):
    return np.linalg.norm(v)


def normalize(v):
    m = magnitude(v)
    if m == 0:
        return v
    return v / m


def angle_between_vectors(a, b):
    theta = np.dot(a, b) / (magnitude(a) * magnitude(b))
    return math.acos(theta)


def law_of_cosines_angle(a, b, c, res='gamma', radians=True, acos=True):
    """
    a, b and c are the length/ratios of the sides, where c is the side opposite to the angle
    we want to retrieve
    """
    if abs(a) > abs(b) + abs(c) or abs(b) > abs(a) + abs(c) or abs(c) > abs(a) + abs(b):
        raise exceptions.MathError('Impossible triangle: The sum of two sides must be larger than the third')

    # gamma = elbow flexion
    # alpha = end-effector - elbow angle (not useful)
    # beta = shoulder elevation + rotation
    angles = {
        'gamma': (a ** 2 + b ** 2 - c ** 2) / (2 * a * b),
        'alpha': (b ** 2 + c ** 2 - a ** 2) / (2 * b * c),
        'beta': (a ** 2 + c ** 2 - b ** 2) / (2 * a * c)
    }

    if not acos:
        return angles[res]

    angles[res] = math.acos(angles[res])

    # Only one value is physically realizable because of joint limits
    if angles[res] > math.pi:
        angles[res] -= math.pi

    return angles[res] if radians is True else math.degrees(angles[res])


def euler_rodrigues_rotation(axis, theta, vector=None):
    axis = np.array(axis)
    if vector is not None:
        vector = np.array(vector)
    # theta = math.radians(angle)

    # axis must be a unit vector
    axis = axis / math.sqrt(np.dot(axis, axis))
    a = math.cos(theta / 2.0)
    b, c, d = -axis * math.sin(theta / 2.0)
    aa, bb, cc, dd = a * a, b * b, c * c, d * d
    bc, ad, ac, ab, bd, cd = b * c, a * d, a * c, a * b, b * d, c * d

    rotation_matrix = np.array([[aa + bb - cc - dd, 2 * (bc + ad), 2 * (bd - ac)],
                                [2 * (bc - ad), aa + cc - bb - dd, 2 * (cd + ab)],
                                [2 * (bd + ac), 2 * (cd - ab), aa + dd - bb - cc]])

    if vector is None:
        return rotation_matrix
    else:
        return rotation_matrix @ vector


def look_at_rotation_matrix(eye, center, up):
    # up=np.array([0, 1, 0])
    dir_unit_vector = normalize(center - eye)
    up_unit_vector = normalize(up)

    right_vector = np.cross(up_unit_vector, dir_unit_vector)
    up_vector = np.cross(dir_unit_vector, normalize(right_vector))

    rotation_matrix = np.empty([4, 4])
    rotation_matrix[:3, 0] = right_vector
    rotation_matrix[3, 0] = 0
    rotation_matrix[:3, 1] = up_vector
    rotation_matrix[3, 0] = 0
    rotation_matrix[:3, 2] = dir_unit_vector
    rotation_matrix[2, 0] = 0
    rotation_matrix[:, 3] = np.array([0, 0, 0, 1])

    return rotation_matrix;


def get_rotation_two_vectors(a, b):
    # returns the rotation matrix that rotates from a to b
    # https://math.stackexchange.com/a/476311
    a_unit = normalize(a)
    b_unit = normalize(b)
    v = np.cross(a_unit, b_unit, axis=0)
    c = np.dot(a_unit, b_unit)

    v_x = np.array([
        [0, -v[2], v[1]],
        [v[2], 0, -v[0]],
        [-v[1], v[0], 0]
    ])

    rotation_matrix = np.identity(3) + v_x + (v_x @ v_x) * (1 / (1 + c))
    hom_rotation_matrix = np.empty([4, 4])
    hom_rotation_matrix[:3, :3] = rotation_matrix
    hom_rotation_matrix[3, :] = [0, 0, 0, 1]
    hom_rotation_matrix[:3, 3] = [0, 0, 0]

    return hom_rotation_matrix


def rotation_matrix_to_euler(r):
    # https://stackoverflow.com/questions/15022630/how-to-calculate-the-angle-from-rotation-matrix
    # print(r[2, 1:3], r)
    rot_x = math.atan2(r[2, 1], r[2, 2])
    rot_y = math.atan2(-r[2, 0], np.linalg.norm(r[2, 1:3]))
    rot_z = math.atan2(r[1, 0], r[0, 0])

    return np.array([rot_x, rot_y, rot_z])
