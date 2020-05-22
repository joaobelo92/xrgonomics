import numpy as np
import math
import linalg_helpers
import exceptions

base_pos = np.array([[0, 0, 0]])


def compute_elbow_vector(end_effector, arm_proper_length, forearm_hand_length):
    """
    End effector is a vector starting at the shoulder. From a 2D perspective, and knowing all the sizes of the sides
    of the triangle, it is possible to use the law of cosines to retrieve the angle between the shoulder and the elbow,
    considering the arm a 2-segment body
    """
    # get length of each side of the triangle
    a = arm_proper_length
    b = forearm_hand_length
    c = linalg_helpers.magnitude(end_effector)

    if a > b + c:
        raise exceptions.MathError('End effector magnitude is larger than arm\'s length')

    # angle_ab = law_of_cosines_angle(a, b, c)
    try:
        angle_ac = linalg_helpers.law_of_cosines_angle(a, c, b)
    except exceptions.MathError:
        # If exception is raised, that means the pose is not possible (using a 2-body segment)
        # returning None has to be handled
        return None, None

    # we need to split the triangle in two right triangles, a' is the distance from
    # a where that happens (closer to end effector)
    a_prime = math.cos(angle_ac) * c
    d = math.sin(angle_ac) * c

    end_effector_normalized = linalg_helpers.normalize(end_effector)
    a_prime_prime = end_effector_normalized * (a - a_prime)
    d_unit_vector = linalg_helpers.normalize(np.cross(end_effector, np.array([0, 1, 0]), axis=0))
    d_vector = d_unit_vector * d

    return a_prime_prime + d_vector, a_prime_prime


# print(compute_elbow_vector([67.5, 41.5, -17.5], 33, 48))


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
        if hand is 'r' and current_pos[2] > elbow_prime[2]:
            num_rotations += 1
        elif hand is 'l' and current_pos[2] < elbow_prime[2]:
            num_rotations += 1

    rotations = np.empty([num_rotations, 3])
    curr_idx = 0
    for angle in range(0, 360, step):
        current_pos = linalg_helpers.euler_rodrigues_rotation(end_effector, angle, elbow)
        # z axis matters in this case. We do not want rotations where the elbow.z > elbow_prime.z
        if hand is 'r' and current_pos[2] > elbow_prime[2]:
            rotations[curr_idx] = current_pos
            curr_idx += 1
        elif hand is 'l' and current_pos[2] < elbow_prime[2]:
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

    humerus1_base_coord = np.identity(4)

    shoulder_elv_axis = humerus_base_coord @ shoulder_elv_axis

    # elv_angle is negative, due to OpenSim coordinate system
    transform = linalg_helpers.euler_rodrigues_rotation(shoulder_elv_axis[0:3], shoulder_elv)
    humerus1_base_coord[0:3, 0] = transform @ humerus1_base_coord[0:3, 0]
    humerus1_base_coord[0:3, 1] = transform @ humerus1_base_coord[0:3, 1]
    humerus1_base_coord[0:3, 2] = transform @ humerus1_base_coord[0:3, 2]

    return humerus1_base_coord


def compute_anchor_arm_poses(end_effector, arm_proper_length, forearm_hand_length, rotation_step=10):
    arm_poses = []
    elbow, elbow_prime = compute_elbow_vector(end_effector, arm_proper_length, forearm_hand_length)

    # If elbow is None, pose is not possible.
    if elbow is None:
        return arm_poses

    rotations = compute_valid_elbow_positions(end_effector, elbow, elbow_prime, rotation_step)
    # print(len(rotations))

    for rotation in rotations:
        forearm_vector = end_effector - rotation

        # To get the angle on a axis, we retrieve the angle of a point disregarding the non-relevant axis
        elv_angle = math.degrees(
            linalg_helpers.angle_between_vectors(np.array([rotation[0], 0, rotation[2]]), np.array([0, 0, 1])))
        elv_angle = elv_angle if rotation[0] > 0 else -elv_angle
        shoulder_elv = math.degrees(
            linalg_helpers.angle_between_vectors(np.array([rotation[0], rotation[1], 0]), np.array([0, -1, 0])))

        rot_matrix_humerus = compute_base_shoulder_rot(elv_angle, shoulder_elv)

        zero_rot_forarm_pos = rot_matrix_humerus @ np.array([forearm_hand_length, 0, 0, 1])
        shoulder_rot = math.degrees(
            linalg_helpers.angle_between_vectors(rot_matrix_humerus[0:3, 0], np.array(end_effector - rotation)))
        shoulder_rot = shoulder_rot if zero_rot_forarm_pos[2] > forearm_vector[2] else -shoulder_rot

        elbow_flexion = math.degrees(linalg_helpers.angle_between_vectors(end_effector - rotation, rotation))

        arm_poses.append({'elbow_x': rotation[0], 'elbow_y': rotation[1], 'elbow_z': rotation[2],
                          'elv_angle': elv_angle, 'shoulder_elv': shoulder_elv,
                          'shoulder_rot': shoulder_rot, 'elbow_flexion': elbow_flexion})

    return arm_poses


# print(compute_anchor_arm_poses([30, 0, 40], 33, 48))
