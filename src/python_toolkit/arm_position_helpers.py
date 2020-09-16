import numpy as np
import math

import linalg_helpers
import exceptions
# import biomechanics
# import opensim as osim

base_pos = np.array([[0, 0, 0]])


def compute_elbow_plane(end_effector, arm_proper_length, forearm_hand_length, shoulder=np.array([0, 0, 0])):
    """
    End effector is a vector starting at the shoulder. From a 2D perspective, and knowing all the sizes of the sides
    of the triangle, it is possible to use the law of cosines to retrieve the angle between the shoulder and the elbow,
    considering the arm a 2-segment body
    """
    # get length of each side of the triangle
    a = arm_proper_length
    b = forearm_hand_length
    c = linalg_helpers.magnitude(end_effector)

    if b > a + c:
        return None, None, None, None
        # raise exceptions.MathError('End effector magnitude is larger than arm\'s length')

    # end effector unit vector (normal vector of the swivel plane)
    n = linalg_helpers.normalize(end_effector)

    y = np.array([0, 1, 0])
    u = linalg_helpers.normalize(-y + np.dot(y, n) * n)
    v = np.cross(n, u)

    try:
        cos_beta = linalg_helpers.law_of_cosines_angle(a, b, c, res='beta', acos=False)
        sin_beta = math.sin(linalg_helpers.law_of_cosines_angle(a, b, c, res='beta'))
    except exceptions.MathError:
        # If exception is raised, that means the pose is not possible (using a 2-body segment)
        # returning None has to be handled
        return None, None, None, None

    center = cos_beta * arm_proper_length * n
    radius = sin_beta * arm_proper_length

    return u, v, center, radius


def compute_interaction_space(spacing, limits, arm_total_length):
    """
    Computes all the positions that are reachable by the arm, apart from each other according to the spacing parameter inside the
    limits in 3D space provided as a list of tuples ([(-x, x), (-y, y), (-z, z)]). For now, consider the coordinate system origin to be
    the right shoulder joint and the x axis is parallel to the line between both shoulders, going positive to the right of the shoulder.

    OpenSim uses the standard engineering coordinate system of X forward (Red), Y up (Green), Z right (Blue)
    OpenSim also uses meters, but the example .trc files are in mm (perhaps they just refer to the unit?)
    Right is +z in OpenSim coordinate system
    """
    current_coords = [math.floor(limits[0][0]), math.floor(limits[1][0]), math.floor(limits[2][0])]
    interaction_space = []
    spacing_mag = linalg_helpers.magnitude([spacing / 2, spacing / 2, spacing / 2])
    while current_coords[2] < limits[2][1]:
        while current_coords[1] < limits[1][1]:
            while current_coords[0] < limits[0][1]:
                # validate if is in reach of the user
                # validate other conditions
                if (current_coords[0] > 0 or current_coords[2] > 0) and (
                        linalg_helpers.magnitude(current_coords) + spacing_mag <= arm_total_length):
                    interaction_space.append([current_coords[0], current_coords[1], current_coords[2]])
                current_coords[0] += spacing

            current_coords[0] = limits[0][0]
            current_coords[1] += spacing

        current_coords[1] = limits[1][0]
        current_coords[2] += spacing
    return interaction_space


def compute_valid_elbow_positions(end_effector, elbow, elbow_prime, step=5, hand='r'):
    """Assumes shoulder is at pos (0, 0, 0)"""
    num_rotations = 0
    for angle in range(0, 360, step):
        current_pos = linalg_helpers.euler_rodrigues_rotation(end_effector, angle, elbow)
        # z axis matters in this case. We do not want rotations where the elbow.z > elbow_prime.z
        if hand == 'r' and current_pos[2] > elbow_prime[2]:
            num_rotations += 1
        elif hand == 'l' and current_pos[2] < elbow_prime[2]:
            num_rotations += 1

    rotations = np.empty([num_rotations, 3])
    curr_idx = 0
    for angle in range(0, 360, step):
        current_pos = linalg_helpers.euler_rodrigues_rotation(end_effector, angle, elbow)
        # z axis matters in this case. We do not want rotations where the elbow.z > elbow_prime.z
        if hand == 'r' and current_pos[2] > elbow_prime[2]:
            rotations[curr_idx] = current_pos
            curr_idx += 1
        elif hand == 'l' and current_pos[2] < elbow_prime[2]:
            rotations[curr_idx] = current_pos
            curr_idx += 1
    return rotations


def compute_base_shoulder_rot(elv_angle, shoulder_elv):
    # Values retrieved from the model
    elv_angle_axis = np.array([0.0048, 0.99908918, 0.04240001])
    # Potential source of issues, x-z coordinates are swapped
    shoulder_elv_axis = np.array([-0.99826136, 0.0023, 0.05889802, 1])

    humerus_base_coord = np.identity(4)

    # elv_angle is negative, due to OpenSim coordinate system
    transform = linalg_helpers.euler_rodrigues_rotation(elv_angle_axis, elv_angle)
    humerus_base_coord[0:3, 0] = transform @ humerus_base_coord[0:3, 0]
    humerus_base_coord[0:3, 1] = transform @ humerus_base_coord[0:3, 1]
    humerus_base_coord[0:3, 2] = transform @ humerus_base_coord[0:3, 2]

    # print(humerus_base_coord)
    humerus1_base_coord = np.identity(4)

    # humerus_base_coord is updated parent coord system (with elv_angle)
    # need to know where the rotation axis is on parent coord system
    shoulder_angle_axis = humerus_base_coord @ shoulder_elv_axis

    transform = linalg_helpers.euler_rodrigues_rotation(shoulder_angle_axis[0:3], shoulder_elv)
    humerus1_base_coord[0:3, 0] = transform @ humerus1_base_coord[0:3, 0]
    humerus1_base_coord[0:3, 1] = transform @ humerus1_base_coord[0:3, 1]
    humerus1_base_coord[0:3, 2] = transform @ humerus1_base_coord[0:3, 2]
    # print('h', humerus1_base_coord)

    return humerus1_base_coord


def compute_anchor_arm_poses(end_effector, arm_proper_length, forearm_hand_length,
                             rotation_step=-math.pi / 8, limit=-math.pi * 3 / 4, model=None):
    arm_poses = []
    u, v, c, r = compute_elbow_plane(end_effector, arm_proper_length, forearm_hand_length)

    # If result is None, pose is not possible with current constraints
    if u is None:
        return arm_poses

    # rotate from 0 to 135 degrees
    elbow_positions = []
    theta = 0

    while theta > limit:
        elbow_positions.append(r * (math.cos(theta) * u + math.sin(theta) * v) + c)
        theta += rotation_step

    error_elbow_acc = 0
    error_end_effector_acc = 0

    for elbow_pos in elbow_positions:
        elv_angle = math.atan2(elbow_pos[0], elbow_pos[2])
        if math.degrees(elv_angle) > 130:
            continue

        # both values are normalized
        if not math.isclose(math.cos(elv_angle), 0, abs_tol=1e-5):
            s2 = elbow_pos[2] / (math.cos(elv_angle) * arm_proper_length)
        else:
            s2 = elbow_pos[0] / (math.sin(elv_angle) * arm_proper_length)

        shoulder_elv = math.atan2(s2, -elbow_pos[1] / arm_proper_length)
        elbow_flexion = linalg_helpers.law_of_cosines_angle(arm_proper_length, forearm_hand_length,
                                                            linalg_helpers.magnitude(end_effector), radians=False)
        elbow_flexion_osim = 180 - elbow_flexion

        humerus_transform = np.linalg.inv(compute_base_shoulder_rot(elv_angle, shoulder_elv))
        forearm_vector = end_effector - elbow_pos
        point = humerus_transform @ np.array([forearm_vector[0], forearm_vector[1], forearm_vector[2], 1])
        shoulder_rot = -math.degrees(math.atan2(point[2], point[0]))

        arm_poses.append({'elbow_x': elbow_pos[0], 'elbow_y': elbow_pos[1], 'elbow_z': elbow_pos[2],
                          'elv_angle': math.degrees(elv_angle), 'shoulder_elv': math.degrees(shoulder_elv),
                          'shoulder_rot': shoulder_rot, 'elbow_flexion': elbow_flexion_osim})

        # Only for validation, opensim required (FW: compute std deviation)
        # _, markers = biomechanics.retrieve_dependent_coordinates(model, math.degrees(elv_angle),
        #                                                          math.degrees(shoulder_elv), shoulder_rot,
        #                                                          elbow_flexion_osim)

        # shoulder_base_pos = np.array([-0.0109379, 0.0239952, 0.17469])

        # validation of elbow position
        # current_elbow_pos = shoulder_base_pos + elbow_pos / 100
        # error_elbow = linalg_helpers.magnitude(np.array(markers['R.Elbow.Center']) - (np.array(current_elbow_pos)))
        # error_elbow_acc += error_elbow
        #
        # # validation of end_effector position
        # current_end_effector_pos = shoulder_base_pos + end_effector / 100
        # error_end_effector = linalg_helpers.magnitude(np.array(markers['End.Effector']) -
        #                                               (np.array(current_end_effector_pos)))
        # error_end_effector_acc += error_end_effector
        # print(shoulder_base_pos, current_end_effector_pos, np.array(markers['End.Effector']))
        # print(elbow_pos, np.array(markers['End.Effector']) - shoulder_base_pos, error_elbow,
        #       error_end_effector, math.degrees(elv_angle), math.degrees(shoulder_elv), shoulder_rot,
        #       elbow_flexion_osim)
        # print(end_effector, error_elbow_acc/len(elbow_positions), error_end_effector_acc/len(elbow_positions))
    return arm_poses
