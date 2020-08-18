import arm_position_helpers as armpos
import linalg_helpers as linalg
import pose_database
import numpy as np
import opensim as osim
import biomechanics
import os
import file_io
import xml.etree.ElementTree
import math
from scipy.spatial import ConvexHull


def initialize_pose_db(db_name, arm_proper_length=33, forearm_hand_length=46, spacing=10):
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

    # print('elbow: {}'.format(np.array([0.0360217, -0.305384, 0.17] - np.array([-0.0109379, 0.0239952, 0.17469]))))
    # print('end effector: {}'.format(np.array([0.143778, -0.752421, 0.205026] - np.array([-0.0109379, 0.0239952, 0.17469]))))
    #
    # print('length proper: {}'.format(linalg.magnitude(np.array([0.0360217, -0.305384,0.17] - np.array([-0.0109379, 0.0239952, 0.17469])))))
    # print('length forearm: {}'.format(linalg.magnitude(np.array([0.143778, -0.752421, 0.205026] - np.array([0.0293081, -0.290748, 0.11592])))))

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


def get_all_voxels(db_name):
    conn = pose_database.create_connection(db_name)
    anchors = pose_database.get_all_voxels(conn)
    result = []
    for anchor in anchors:
        result.append({
            'id': anchor[0],
            'position': [anchor[1], anchor[2], anchor[3]],
        })
    return result


def get_voxels_constrained(db_name, x, y, z, x_constraint, y_constraint, z_constraint, metric):
    conn = pose_database.create_connection(db_name)
    print(metric)
    # metric = 'muscle_activation_reserve'
    if metric is 'muscle_activation':
        query = metric + ', MIN(arm_poses.muscle_activation_reserve)'
    else:
        query = 'MIN(' + metric + '), arm_poses.reserve'

    sql = '''SELECT voxels.id, voxels.x, voxels.y, voxels.z, COUNT(*), arm_poses.arm_pose_id, {}
             FROM voxels INNER JOIN arm_poses ON arm_poses.voxel_id = voxels.id '''.format(query)
    # sql = '''SELECT voxels.id, voxels.x, voxels.y, voxels.z, COUNT(*)
    #          FROM voxels LEFT OUTER JOIN arm_poses ON voxels.id = arm_poses.voxel_id '''
    params = []
    if x is not "" or y is not "" or z is not "":
        sql += 'WHERE '
    if x is not "":
        x = float(x)
        if x_constraint is '=':
            sql += 'min_x <= ? AND max_x > ? '
            params += [x, x]
        elif x_constraint is '<=':
            sql += 'max_x <= ? '
            params += [x]
        else:
            sql += 'min_x >= ? '
            params += [x]
    if y is not "":
        y = float(y)
        if x is not "":
            sql += 'AND '
        if y_constraint is '=':
            sql += 'min_y <= ? AND max_y > ? '
            params += [y, y]
        elif y_constraint is '<=':
            sql += 'max_y <= ? '
            params += [y]
        else:
            sql += 'min_y >= ? '
            params += [y]
    if z is not "":
        z = float(z)
        if x is not "" or y is not "":
            sql += 'AND '
        if z_constraint is '=':
            sql += 'min_z <= ? AND max_z > ? '
            params += [z, z]
        elif z_constraint is '<=':
            sql += 'max_z <= ? '
            params += [z]
        else:
            sql += 'min_z >= ? '
            params += [z]

    sql += '''AND {} IS NOT NULL {}
              GROUP BY voxels.id'''.format(metric, 'AND reserve IS NOT NULL' if metric is 'muscle_activation' else '')

    # print(sql)
    cursor = pose_database.custom_query(conn, sql, params)
    voxels = cursor.fetchall()

    result = []
    if len(voxels) > 0:
        voxels = np.array(voxels)
        # Add a column for normalized comfort values
        voxels_new = np.zeros((voxels.shape[0], voxels.shape[1] + 1))
        voxels_new[:, :-1] = voxels

        min_activation = np.amin(voxels_new[:, 6])
        min_reserve = np.amin(voxels_new[:, 7])
        max_activation = np.amax(voxels_new[:, 6])
        max_reserve = np.amax(voxels_new[:, 7])
        print(min_activation, min_reserve, max_activation, max_reserve, metric)

        if metric == 'muscle_activation':
            min_activation = 0.0012142493999999998
            max_activation = 0.1659012612
            voxels_new[:, 6] -= min_activation
            voxels_new[:, 6] /= max_activation - min_activation
            # only for visualization purposes multiply muscle activation
            voxels_new[:, 8] = voxels_new[:, 6] * 2.5 + voxels_new[:, 7]
            voxels_sorted = voxels_new[voxels_new[:, 8].argsort()]
        elif metric == 'weighted_metrics':
            voxels_new[:, 8] = voxels_new[:, 6]
            voxels_sorted = voxels_new[voxels_new[:, 8].argsort()]
        else:
            # to facilitate visualization
            if metric == 'consumed_endurance':
                metric_min = 0.018610636123524517
                metric_max = 9.599405943409115
            else:
                metric_min = 3.0
                metric_max = 9
            voxels_new[:, 6] -= metric_min
            voxels_new[:, 6] /= metric_max - metric_min
            voxels_new[:, 8] = voxels_new[:, 6]
            voxels_sorted = voxels_new[voxels_new[:, 8].argsort()]
            # print(voxels_sorted[:, 8][0], voxels_sorted[:, 8][-1])
            # normalize comfort value
            # print(voxels_sorted[:, 8][-10:])
            # print(voxels_sorted[:, 8][0], voxels_sorted[:, 8][-1])
            voxels_sorted[:, 8] -= voxels_sorted[:, 8][0]
            voxels_sorted[:, 8] /= voxels_sorted[:, 8][-1] - voxels_sorted[:, 8][0]
            # print(voxels_sorted[:, 8])

        for voxel in voxels_sorted.tolist():
            result.append({
                'id': int(voxel[0]),
                'position': [voxel[1], voxel[2], voxel[3]],
                'num_poses': int(voxel[4]),
                'pose_id': int(voxel[5]),
                'comfort': voxel[8]
            })
    return result


def compute_muscle_activation_reserve_function(db_name):
    conn = pose_database.create_connection(db_name)
    cursor = conn.cursor()
    # cursor = conn.cursor()
    # sql = '''ALTER TABLE arm_poses
    #          ADD muscle_activation_reserve REAL'''
    # cursor.execute(sql)
    # conn.commit()

    # we want to give priority to poses with the lowest reserve values. Hence, we use the max reserve value of all
    # voxels, where their reserve value is the minimum between all the poses.
    # voxels that have reserve values among a threshold receive the worst comfort rating (1).
    poses = pose_database.get_all_poses_muscle_activation(conn)

    reserve_threshold = 250
    for pose in poses:
        muscle_activation_reserve = pose[1] + pose[2] / reserve_threshold
        sql = '''UPDATE arm_poses
                 SET muscle_activation_reserve = ?
                 WHERE arm_pose_id = ?'''
        cursor.execute(sql, (muscle_activation_reserve, pose[0]))

    conn.commit()


def compute_weigthed_metrics(db_name):
    conn = pose_database.create_connection(db_name)
    cursor = conn.cursor()
    # sql = '''ALTER TABLE arm_poses
    #          ADD weighted_metrics REAL'''
    # cursor.execute(sql)

    # we want to give priority to poses with the lowest reserve values. Hence, we use the max reserve value of all
    # voxels, where their reserve value is the minimum between all the poses.
    # voxels that have reserve values among a threshold receive the worst comfort rating (1).
    poses = pose_database.get_all_poses_all_metrics(conn)

    for arm_id, consumed_endurance, rula, muscle_activation in poses:

        consumed_endurance -= 0.018610636123524517
        consumed_endurance /= 9.599405943409115
        consumed_endurance_w = 1/3 * consumed_endurance
        rula -= 3
        rula /= 9
        rula_w = 1/3 * rula
        if muscle_activation is None:
            muscle_activation = 1
        muscle_activation_w = 1/3 * min(1, muscle_activation)
        sql = '''UPDATE arm_poses
                 SET weighted_metrics = ?
                 WHERE arm_pose_id = ?'''
        cursor.execute(sql, (consumed_endurance_w + rula_w + muscle_activation_w, arm_id))

    conn.commit()

# compute_weigthed_metrics('poses.db')


def get_voxel_poses(db_name, x, y, z):
    conn = pose_database.create_connection(db_name)
    voxel_id = pose_database.get_voxel_point(conn, x, y, z)[0]
    poses = pose_database.get_poses_in_voxel(conn, voxel_id)
    result = []
    for pose in poses:
        result.append({
            'id': pose[0],
            'elbow': [pose[2], pose[3], pose[4]]
        })
    return result


def compute_arm_pos(end_effector, arm_proper_length, forearm_hand_length):
    return armpos.compute_anchor_arm_poses(end_effector, arm_proper_length, forearm_hand_length)


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


# def compute_all_arm_pos(db_name, arm_proper_length=33, forearm_hand_length=48):
#     conn = pose_database.create_connection(db_name)
#     for voxel in get_all_voxels(db_name):
#         poses = compute_arm_pos(voxel['position'], arm_proper_length, forearm_hand_length)
#         for pose in poses:
#             # print((voxel['id'], *pose.values()))
#             pose_database.insert_arm_pose(conn, (voxel['id'], *pose.values()))
#     conn.commit()


def compute_all_arm_pos(db_name, arm_proper_length=33, forearm_hand_length=48):
    conn = pose_database.create_connection(db_name)
    # voxel = get_voxels_constrained(db_name, 32.5, 1.5, 42.5)[0]
    # poses = armpos.compute_anchor_arm_poses(voxel['position'], arm_proper_length, forearm_hand_length)
    # if poses is not None:
    #     for pose in poses:
    #         # print(voxel['position'], pose['elbow_x'], pose['elbow_y'], pose['elbow_z'])
    #         pose_database.insert_arm_pose(conn, (voxel['id'], pose['elbow_x'], pose['elbow_y'], pose['elbow_z'],
    #                                              pose['elv_angle'], pose['shoulder_elv'], pose['shoulder_rot'],
    #                                              pose['elbow_flexion']))
    error_acc = 0
    model = osim.Model('../../assets/MoBL_ARMS_module6_7_CMC_updated_unlocked.osim')
    model.initSystem()
    for voxel in get_all_voxels(db_name):
        # get point in the anchor center
        poses, error = armpos.compute_anchor_arm_poses(np.array(voxel['position']), arm_proper_length, forearm_hand_length, model)
        error_acc += error
        if poses is not None:
            for pose in poses:
                # print(voxel['position'], pose['elbow_x'], pose['elbow_y'], pose['elbow_z'])
                pose_database.insert_arm_pose(conn, (voxel['id'], pose['elbow_x'], pose['elbow_y'], pose['elbow_z'],
                                                     pose['elv_angle'], pose['shoulder_elv'], pose['shoulder_rot'],
                                                     pose['elbow_flexion']))

    conn.commit()
    # print(error_acc / pose_database.count_poses())


def compute_muscle_activations(db_name):
    conn = pose_database.create_connection(db_name)
    # print(pose_database.count_poses(conn))
    poses = pose_database.get_all_poses(conn)

    for pose in poses:
        # pose = poses[2000]
        # print(pose_database.get_voxel_by_id(conn, pose[1]))
        if pose[-4] is not None:
            continue
        # get OpenSim coordinates
        model = osim.Model('../../experiments/MoBL_ARMS_module6_7_CMC_updated_unlocked.osim')
        coords, _ = biomechanics.retrieve_dependent_coordinates(model, pose[5], pose[6], pose[7], pose[8])

        # create mot file and organize experiment data in folders
        new_path = '../../experiments/poses/{}/'.format(pose[0])
        if not os.path.exists(new_path):
            os.makedirs(new_path)
        file_io.generate_arm_static_mot(new_path + 'pose_{}.mot'.format(pose[0]), list(coords.keys()),
                                        list(coords.values()), num_rows=50)

        baseline_st_xml = xml.etree.ElementTree.parse('../../assets/so_baseline.xml')
        coord_file_elem = baseline_st_xml.getroot().find('AnalyzeTool/coordinates_file')
        coord_file_elem.text = 'pose_{}.mot'.format(pose[0])
        baseline_st_xml.write(new_path + 'pose_{}_so.xml'.format(pose[0]))

        # run static optimization
        biomechanics.run_static_optimization(new_path + 'pose_{}_so.xml'.format(pose[0]))

        # parse results
        avg_activations, reserve = file_io.read_so_results(new_path + '_StaticOptimization_activation.sto')

        # insert discomfort metric in db
        pose_database.set_pose_activation_reserve(conn, pose[0], avg_activations, reserve)
        conn.commit()


def compute_consumed_endurance(db_name):
    conn = pose_database.create_connection(db_name)
    poses = pose_database.get_all_poses_voxels(conn)
    # print(poses[0])

    # Frievalds arm data for 50th percentile male:
    # upper arm: length - 33cm; mass - 2.1; distance cg - 13.2
    # forearm: length - 26.9cm; mass - 1.2; distance cg - 11.7
    # hand: length - 19.1cm; mass - 0.4; distance cg - 7.0
    for pose in poses:
        # print(pose)
        # retrieve pose data and convert to meters
        end_effector = np.array(pose[1:4]) / 100
        elbow = np.array(pose[4:7]) / 100

        # ehv stands for elbow hand vector
        ehv_unit = linalg.normalize(end_effector - elbow)
        elbow_unit = linalg.normalize(elbow)
        # Due to the fact that we lock the hand coordinate (always at 0 degrees), the CoM of the elbow - hand vector
        # will always be at 17.25cm from the elbow.
        # 11.7 + 0.25 * 22.2 = 17.25
        # check appendix B of Consumed Endurance paper for more info
        d = elbow + ehv_unit * 0.1725
        a = elbow_unit * 0.132
        ad = d - a
        com = a + 0.43 * ad

        torque_shoulder = np.cross(com, 3.7 * np.array([0, 9.8, 0]))
        torque_shoulder_mag =  linalg.magnitude(torque_shoulder)
        # print(torque_shoulder, linalg.magnitude(torque_shoulder))

        strength = torque_shoulder_mag / 101.6 * 100
        pose_database.set_pose_consumed_endurance(conn, pose[0], strength)
        conn.commit()


def compute_rula(db_name, arm_proper_length=33):
    conn = pose_database.create_connection(db_name)
    poses = pose_database.get_all_poses_voxels(conn)

    # pose = poses[0]
    for pose in poses:
        # arm pose is already computed for osim
        end_effector = pose[1:4]
        # elbow_pos = pose[4:7]
        elv_angle = pose[7]
        shoulder_elv = pose[8]
        elbow_flexion = pose[9]

        rula_score = 0

        # upper arm flexion / extension
        if shoulder_elv < 20:
            rula_score += 1
        elif shoulder_elv < 45:
            rula_score += 2
        elif shoulder_elv < 90:
            rula_score += 3
        else:
            rula_score += 4

        # add 1 if upper arm is abducted
        # we consider arm abducted if elv_angle is < 45 and > -45, and shoulder_elv > 30
        if -60 > elv_angle < 60 and shoulder_elv > 30:
            rula_score += 1

        # lower arm flexion
        if 60 < elbow_flexion < 100:
            rula_score += 1
        else:
            rula_score += 2

        # if lower arm is working across midline or out to the side add 1
        # according to MoBL model, shoulder is 17cm from thorax on z axis (osim coord system), we use that value:
        if end_effector[2] + 17 < 0 or end_effector[2] > 0:
            rula_score += 1

        # wrist is always 1, due to fixed neutral position
        rula_score += 1

        pose_database.set_pose_rula(conn, pose[0], rula_score)
        conn.commit()


def optimal_position_in_polygon(db_name, polygon):
    conn = pose_database.create_connection(db_name)

    metric = 'consumed_endurance'
    sql = '''SELECT voxels.id, voxels.x, voxels.y, voxels.z, arm_poses.arm_pose_id, MIN({}), arm_poses.reserve
             FROM voxels LEFT OUTER JOIN arm_poses ON arm_poses.voxel_id = voxels.id
             GROUP BY voxels.id'''.format(metric)

    # params = []
    # if x is not "" or y is not "" or z is not "":
    #     sql += 'WHERE '
    # if x is not "":
    #     x = float(x)
    #     sql += 'min_x <= ? AND max_x > ? '
    #     params += [x, x]
    # if y is not "":
    #     y = float(y)
    #     if x is not "":
    #         sql += 'AND '
    #     sql += 'min_y <= ? AND max_y > ? '
    #     params += [y, y]
    # if z is not "":
    #     z = float(z)
    #     if x is not "" or y is not "":
    #         sql += 'AND '
    #     sql += 'min_z <= ? AND max_z > ? '
    #     params += [z, z]
    #
    # sql += ""

    cursor = pose_database.custom_query(conn, sql, [])
    voxels = cursor.fetchall()

    polygon = np.array(polygon)
    hull = ConvexHull(polygon.reshape([8, 3]))
    in_spec = []
    for voxel in voxels:
        if voxel[5] is None:
            continue
        pos = (voxel[1], voxel[2], voxel[3])
        if point_in_polygon(hull, pos):
            in_spec.append([voxel[1], voxel[2], voxel[3], voxel[5]])

    if len(in_spec) > 0:
        in_spec = np.array(in_spec)
        in_spec = in_spec[in_spec[:, 3].argsort()]
        # print(in_spec[in_spec[:, 3].argsort()])
        return in_spec.tolist()
    return in_spec


def point_in_polygon(polygon, point):
    '''
    Checks if `pnt` is inside the convex hull.
    `hull` -- a QHull ConvexHull object
    `pnt` -- point array of shape (3,)
    '''
    new_hull = ConvexHull(np.concatenate((polygon.points, [point])))
    if np.array_equal(new_hull.vertices, polygon.vertices):
        return True
    return False

# optimal_position_in_polygon('poses.db', [0.34324583411216736, 0.17320507764816284, 0.25422555208206177, 0.34324583411216736, -0.17320507764816284, 0.25422555208206177, -0.2588087320327759, -0.17320507764816284, 0.33980342745780945, -0.2588087320327759, 0.17320507764816284, 0.33980342745780945, 1144.15283203125, 577.3502807617188, 847.4183959960938, 1144.15283203125, -577.3502807617188, 847.4183959960938, -862.6958618164062, -577.3502807617188, 1132.677978515625, -862.6958618164062, 577.3502807617188, 1132.677978515625])

# pose_database.drop_tables(pose_database.create_connection('poses.db'))
# initialize_pose_db('poses.db')
# compute_all_arm_pos('poses.db')
# compute_muscle_activations('poses.db')
# compute_consumed_endurance('poses.db')
# compute_rula('poses.db')

# r = get_voxel_poses('poses.db', 32.5, 1.5, 42.5)
# for p in r:
#     print(p)
# print(len(r), r)





