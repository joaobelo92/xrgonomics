import arm_position_helpers as armpos
import linalg_helpers as linalg
import pose_database
import numpy as np


def initialize_pose_db(db_name, arm_proper_length=33, forearm_hand_length=48, spacing=5):
    conn = pose_database.create_connection(db_name)
    pose_database.create_tables(conn)

    # thorax [0, 0, 0]
    # clavicle [0.00502553, 0.00792304, 0.025465]
    # clavphant [-0.0125719, 0.0251998, 0.161]
    # scapula [-0.0125719, 0.0251998, 0.161]
    # scapphant [-0.0160728, -0.00994205, 0.17]
    # humphant [-0.0160728, -0.00994205, 0.17]
    # humphant1 [-0.0160728, -0.00994205, 0.17]
    # humerus [-0.0160728, -0.00994205, 0.17]
    # ulna [0.040362, -0.294871, 0.1577]
    # radius [0.0427534, -0.30613, 0.177699]
    # proximal_row [0.102503, -0.541328, 0.202699]
    # hand [0.109048, -0.55546, 0.205026]

    # --- R.Shoulder [-0.0109379, 0.0239952, 0.17469]
    # R.Elbow.Lateral [0.0376569, -0.285346, 0.19884]
    # R.Elbow.Medial [0.0293081, -0.290748, 0.11592]
    # --- R.Elbow.Center [0.0360217,-0.305384,0.17]
    # --- End.Effector [0.143778, -0.752421, 0.205026]

    # Acromion-Radiale length 31.14 12.26 50TH 34.05 13.41
    # Forearm - hand lenght 44.21 17.41 50TH 48.28 19.01

    print('elbow: {}'.format(np.array([0.0360217, -0.305384, 0.17] - np.array([-0.0109379, 0.0239952, 0.17469]))))
    print('end effector: {}'.format(np.array([0.143778, -0.752421, 0.205026] - np.array([-0.0109379, 0.0239952, 0.17469]))))

    print('length proper: {}'.format(linalg.magnitude(np.array([0.0360217, -0.305384,0.17] - np.array([-0.0109379, 0.0239952, 0.17469])))))
    print('length forearm: {}'.format(linalg.magnitude(np.array([0.143778, -0.752421, 0.205026] - np.array([0.0293081, -0.290748, 0.11592])))))

    arm_total_length = arm_proper_length + forearm_hand_length
    voxels = armpos.compute_interaction_space(spacing, [(-15, arm_total_length), (-arm_total_length, arm_total_length),
                                                        (-arm_proper_length/2 - forearm_hand_length, arm_total_length)],
                                                        arm_total_length)
    for voxel in voxels:
        pose_database.insert_anchor(conn, (voxel[0], voxel[0] + spacing,
                                           voxel[1], voxel[1] + spacing,
                                           voxel[2], voxel[2] + spacing,
                                           voxel[0] + spacing / 2, voxel[1] + spacing / 2,
                                           voxel[2] + spacing / 2))

    conn.commit()


def compute_all_arm_pos(db_name, arm_proper_length=33, forearm_hand_length=48):
    conn = pose_database.create_connection(db_name)
    anchors = pose_database.get_voxels_cursor(conn)
    for anchor in anchors:
        # get point in the anchor center
        end_effector = (anchor[7], anchor[8], anchor[9])
        poses = armpos.compute_anchor_arm_poses(end_effector, arm_proper_length, forearm_hand_length)
        if poses is not None:
            for pose in poses:
                pose_database.insert_arm_pose(conn, (anchor[0], pose['elbow_x'], pose['elbow_y'], pose['elbow_z'],
                                                     pose['elv_angle'], pose['shoulder_elv'], pose['shoulder_rot'],
                                                     pose['elbow_flexion']))
    conn.commit()


def get_all_voxels(db_name):
    conn = pose_database.create_connection(db_name)
    anchors = pose_database.get_voxels_cursor(conn)
    result = []
    for anchor in anchors:
        result.append({
            'id': anchor[0],
            'position': [anchor[7], anchor[8], anchor[9]],
        })
    return result


def get_voxels_constrained(db_name, x, y, z):
    conn = pose_database.create_connection(db_name)
    sql = '''SELECT * FROM voxels '''
    params = []
    if x is not "" or y is not "" or z is not "":
        sql += 'WHERE '
    if x is not "":
        x = float(x)
        sql += 'min_x <= ? AND max_x > ? '
        params += [x, x]
    if y is not "":
        y = float(y)
        if x is not "":
            sql += 'AND '
        sql += 'min_y <= ? AND max_y > ? '
        params += [y, y]
    if z is not "":
        z = float(z)
        if x is not "" or y is not "":
            sql += 'AND '
        sql += 'min_z <= ? AND max_z > ?'
        params += [z, z]

    anchors = pose_database.custom_query(conn, sql, params)

    result = []
    for anchor in anchors:
        result.append({
            'id': anchor[0],
            'position': [anchor[7], anchor[8], anchor[9]],
        })
    return result


def get_voxel_poses(db_name, x, y, z):
    conn = pose_database.create_connection(db_name)
    # print(x, y, z)
    voxel_id = pose_database.get_voxel_point(conn, x, y, z)[0]
    poses = pose_database.get_poses_in_voxel(conn, voxel_id)
    result = []
    for pose in poses:
        result.append({
            'id': pose[0],
            'elbow': [pose[2], pose[3], pose[4]]
        })
    return result


def compute_arm_pos(end_effector, arm_proper_length, forearm_hand_length, rotation_step=20):
    return armpos.compute_anchor_arm_poses(end_effector, arm_proper_length, forearm_hand_length, rotation_step)


def get_interaction_space_limits(db_name):
    conn = pose_database.create_connection(db_name)
    limits = pose_database.get_voxels_limits(conn)
    limits_dict = {
        'min_x': limits[0],
        'max_x': limits[1],
        'min_y': limits[2],
        'max_y': limits[3],
        'min_z': limits[4],
        'max_z': limits[5],
    }
    return limits_dict


def compute_all_arm_pos(db_name, arm_proper_length=33, forearm_hand_length=48):
    conn = pose_database.create_connection(db_name)
    for voxel in get_all_voxels(db_name):
        poses = compute_arm_pos(voxel['position'], arm_proper_length, forearm_hand_length)
        for pose in poses:
            # print((voxel['id'], *pose.values()))
            pose_database.insert_arm_pose(conn, (voxel['id'], *pose.values()))
    conn.commit()

# pose_database.drop_tables(pose_database.create_connection('poses.db'))
# initialize_pose_db('poses.db')
# compute_all_arm_pos('poses.db')

# get_voxel_poses('poses.db', 20, 22, 5)





