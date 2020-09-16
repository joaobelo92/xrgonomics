import arm_position_helpers as armpos
import linalg_helpers as linalg
import pose_database
import numpy as np
# import opensim as osim
# import biomechanics
from scipy.spatial import ConvexHull
import time


class XRgonomics:
    def __init__(self, database='poses.db', arm_proper_length=33, forearm_hand_length=46, spacing=10):
        since = time.time()
        self.arm_proper_length = arm_proper_length
        self.forearm_hand_length = forearm_hand_length
        self.conn = pose_database.create_connection(database)
        if database != 'poses.db':
            pose_database.create_tables(self.conn)
            self.initialize_pose_db(arm_proper_length, forearm_hand_length, spacing)
            self.compute_all_arm_pos()
            self.compute_consumed_endurance()
            self.compute_rula()
        self.last_interaction_space = []
        self.is_version = 0
        self.is_updated = 0
        print("Toolkit initialized in {:.2f} seconds!".format(time.time() - since))

    def initialize_pose_db(self, arm_proper_length, forearm_hand_length, spacing):
        pose_database.create_tables(self.conn)

        arm_total_length = arm_proper_length + forearm_hand_length
        voxels = armpos.compute_interaction_space(spacing,
                                                  [(-15, arm_total_length), (-arm_total_length, arm_total_length),
                                                   (-arm_proper_length / 2 - forearm_hand_length, arm_total_length)],
                                                  arm_total_length)
        for voxel in voxels:
            pose_database.insert_voxel(self.conn, (voxel[0], voxel[0] + spacing,
                                       voxel[1], voxel[1] + spacing,
                                       voxel[2], voxel[2] + spacing,
                                       voxel[0] + spacing / 2, voxel[1] + spacing / 2,
                                       voxel[2] + spacing / 2))
        self.conn.commit()

    def get_all_voxels(self):
        anchors = pose_database.get_all_voxels(self.conn)
        result = []
        for anchor in anchors:
            result.append({
                'id': anchor[0],
                'position': [anchor[1], anchor[2], anchor[3]],
            })
        return result

    def get_voxels_constrained(self, metric, constraints):
        if metric == 'last_interaction_space':
            return self.get_last_interaction_space()
        if metric == 'muscle_activation':
            query = metric + ', MIN(arm_poses.muscle_activation_reserve)'
        else:
            query = 'MIN(' + metric + '), arm_poses.reserve'

        sql = '''SELECT voxels.id, voxels.x, voxels.y, voxels.z, COUNT(*), arm_poses.arm_pose_id, {}
                 FROM voxels INNER JOIN arm_poses ON arm_poses.voxel_id = voxels.id '''.format(query)

        params = []
        if len(constraints) > 0:
            const_sql, const_params = get_sql_constraint(*constraints[0].values())
            sql += 'WHERE ' + const_sql
            params += const_params

            for constraint in constraints[1:]:
                const_sql, const_params = get_sql_constraint(*constraint.values())
                sql += 'AND ' + const_sql
                params += const_params

        sql += '''AND {} IS NOT NULL {}
                  GROUP BY voxels.id'''.format(metric, 'AND reserve IS NOT NULL' if metric == 'muscle_activation' else '')

        cursor = pose_database.custom_query(self.conn, sql, params)
        voxels = cursor.fetchall()

        result = []
        voxels_sorted = normalize_comfort_metric(voxels, 6, metric)
        for voxel in voxels_sorted.tolist():
            result.append({
                'id': int(voxel[0]),
                'position': [voxel[1], voxel[2], voxel[3]],
                'num_poses': int(voxel[4]),
                'pose_id': int(voxel[5]),
                'comfort': voxel[8]
            })
        return result

    def compute_muscle_activation_reserve_function(self):
        cursor = self.conn.cursor()

        # we want to give priority to poses with the lowest reserve values. Hence, we use the max reserve value of all
        # voxels, where their reserve value is the minimum between all the poses.
        # voxels that have reserve values among a threshold receive the worst comfort rating (1).
        poses = pose_database.get_all_poses_muscle_activation(self.conn)

        reserve_threshold = 250
        for pose in poses:
            muscle_activation_reserve = pose[1] + pose[2] / reserve_threshold
            sql = '''UPDATE arm_poses
                     SET muscle_activation_reserve = ?
                     WHERE arm_pose_id = ?'''
            cursor.execute(sql, (muscle_activation_reserve, pose[0]))

        self.conn.commit()

    def compute_weigthed_metrics(self):
        cursor = self.conn.cursor()

        poses = pose_database.get_all_poses_all_metrics(self.conn)

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

        self.conn.commit()

    def get_voxel_poses(self, x, y, z, metric):
        voxel_id = pose_database.get_voxel_point(self.conn, x, y, z)[0]
        poses = pose_database.get_poses_in_voxel(self.conn, voxel_id, metric).fetchall()

        result = []
        poses_sorted = normalize_comfort_metric(poses, 4, metric)
        for pose in poses_sorted:
            result.append({
                'id': int(pose[0]),
                'elbow': [pose[1], pose[2], pose[3]],
                'comfort': pose[-1]
            })
        return result

    def get_last_interaction_space(self):
        result = []
        if self.is_updated < self.is_version:
            for voxel in self.last_interaction_space:
                result.append({
                    'id': 0,
                    'position': [voxel[0], voxel[1], voxel[2]],
                    'num_poses': 0,
                    'pose_id': 0,
                    'comfort': voxel[3]
                })
            self.is_updated += 1
        return result

    def get_interaction_space_limits(self):
        limits = pose_database.get_voxels_limits(self.conn)
        limits_dict = {
            'min_x': limits[0],
            'max_x': limits[1],
            'min_y': limits[2],
            'max_y': limits[3],
            'min_z': limits[4],
            'max_z': limits[5],
        }
        return limits_dict

    def compute_all_arm_pos(self):
        # model = osim.Model('../../assets/MoBL_ARMS_module6_7_CMC_updated_unlocked.osim')
        # model.initSystem()
        for voxel in self.get_all_voxels():
            # get point in the anchor center
            poses = armpos.compute_anchor_arm_poses(np.array(voxel['position']), self.arm_proper_length,
                                                    self.forearm_hand_length)
            if len(poses) > 0:
                for pose in poses:
                    pose_database.insert_arm_pose(self.conn, (voxel['id'], pose['elbow_x'], pose['elbow_y'],
                                                              pose['elbow_z'], pose['elv_angle'], pose['shoulder_elv'],
                                                              pose['shoulder_rot'], pose['elbow_flexion']))
        self.conn.commit()

    # Need opensim python bindings
    # def compute_muscle_activations(self):
    #     conn = pose_database.create_connection(self.database)
    #     # print(pose_database.count_poses(conn))
    #     poses = pose_database.get_all_poses(conn)
    #
    #     for pose in poses:
    #         # pose = poses[2000]
    #         # print(pose_database.get_voxel_by_id(conn, pose[1]))
    #         if pose[-4] is not None:
    #             continue
    #         # get OpenSim coordinates
    #         model = osim.Model('../../experiments/MoBL_ARMS_module6_7_CMC_updated_unlocked.osim')
    #         coords, _ = biomechanics.retrieve_dependent_coordinates(model, pose[5], pose[6], pose[7], pose[8])
    #
    #         # create mot file and organize experiment data in folders
    #         new_path = '../../experiments/poses/{}/'.format(pose[0])
    #         if not os.path.exists(new_path):
    #             os.makedirs(new_path)
    #         file_io.generate_arm_static_mot(new_path + 'pose_{}.mot'.format(pose[0]), list(coords.keys()),
    #                                         list(coords.values()), num_rows=50)
    #
    #         baseline_st_xml = xml.etree.ElementTree.parse('../../assets/so_baseline.xml')
    #         coord_file_elem = baseline_st_xml.getroot().find('AnalyzeTool/coordinates_file')
    #         coord_file_elem.text = 'pose_{}.mot'.format(pose[0])
    #         baseline_st_xml.write(new_path + 'pose_{}_so.xml'.format(pose[0]))
    #
    #         # run static optimization
    #         biomechanics.run_static_optimization(new_path + 'pose_{}_so.xml'.format(pose[0]))
    #
    #         # parse results
    #         avg_activations, reserve = file_io.read_so_results(new_path + '_StaticOptimization_activation.sto')
    #
    #         # insert discomfort metric in db
    #         pose_database.set_pose_activation_reserve(conn, pose[0], avg_activations, reserve)
    #         conn.commit()

    def compute_consumed_endurance(self):
        poses = pose_database.get_all_poses_voxels(self.conn)
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
            # will always be at 17.25cm from the elbow for 50th percent male
            # 11.7 + 0.25 * 22.2 = 17.25
            # 17.25 / 46 = 0.375
            # check appendix B of Consumed Endurance paper for more info
            d = elbow + ehv_unit * self.forearm_hand_length * 0.01 * 0.375
            a = elbow_unit * self.arm_proper_length * 0.01 * 0.4
            ad = d - a
            com = a + 0.43 * ad

            # mass should be adjusted if arm dimensions change
            # 3.7kg for 50th percentile male, currently a simple heuristic based on arm size.
            adjusted_mass = (self.forearm_hand_length + self.arm_proper_length) / 79 * 3.7
            torque_shoulder = np.cross(com, adjusted_mass * np.array([0, 9.8, 0]))
            torque_shoulder_mag = linalg.magnitude(torque_shoulder)

            strength = torque_shoulder_mag / 101.6 * 100
            pose_database.set_pose_consumed_endurance(self.conn, pose[0], strength)
            self.conn.commit()

    def compute_rula(self):
        poses = pose_database.get_all_poses_voxels(self.conn)

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

            pose_database.set_pose_rula(self.conn, pose[0], rula_score)
            self.conn.commit()

    def optimal_position_in_polygon(self, polygon):
        metric = 'weighted_metrics'
        sql = '''SELECT voxels.id, voxels.x, voxels.y, voxels.z, arm_poses.arm_pose_id, MIN({}), arm_poses.reserve
                 FROM voxels LEFT OUTER JOIN arm_poses ON arm_poses.voxel_id = voxels.id
                 GROUP BY voxels.id'''.format(metric)

        cursor = pose_database.custom_query(self.conn, sql, [])
        voxels = cursor.fetchall()

        polygon = np.array(polygon)
        hull = ConvexHull(polygon.reshape([8, 3]))
        in_spec = []
        for voxel in voxels:
            if voxel[5] is None:
                continue
            pos = (voxel[1], voxel[2], voxel[3])
            if self.point_in_polygon(hull, pos):
                in_spec.append([voxel[1], voxel[2], voxel[3], voxel[5]])

        if len(in_spec) > 0:
            in_spec = np.array(in_spec)
            in_spec = in_spec[in_spec[:, 3].argsort()]
            self.last_interaction_space = in_spec
            self.is_version += 1
            return {
                "pos": in_spec.tolist()[0]
            }
        else:
            return {
                "pos": []
            }

    @staticmethod
    def point_in_polygon(polygon, point):
        """
        Checks if `pnt` is inside the convex hull. Currently necessary since sqlite python bindings do not support
        custom r*-tree queries.
        `hull` -- a QHull ConvexHull object
        `pnt` -- point array of shape (3,)
        """
        new_hull = ConvexHull(np.concatenate((polygon.points, [point])))
        if np.array_equal(new_hull.vertices, polygon.vertices):
            return True
        return False


def get_sql_constraint(axis, constraint, value):
    axis_strs = ['x', 'y', 'z']
    axis_str = axis_strs[axis]
    if constraint == '=':
        sql = 'min_{axis} <= ? AND max_{axis} > ? '.format(axis=axis_str)
        params = [value, value]
    else:
        sql = '{}_{axis} {constraint} ? '.format('max' if constraint == '<=' else 'min',
                                                 axis=axis_str, constraint=constraint)
        params = [value]
    return sql, params


def normalize_comfort_metric(array, comfort_index, metric):
    array_sorted = np.array([])
    if len(array) > 0:
        array = np.array(array)
        # Add a column for normalized comfort values
        array_new = np.zeros((array.shape[0], array.shape[1] + 1))
        array_new[:, :-1] = array
        array_new[:, -1] = array[:, comfort_index]

        # min_activation = np.amin(voxels_new[:, 6])
        # min_reserve = np.amin(voxels_new[:, 7])
        # max_activation = np.amax(voxels_new[:, 6])
        # max_reserve = np.amax(voxels_new[:, 7])
        # print(min_activation, min_reserve, max_activation, max_reserve, metric)

        metric_min = 0
        metric_max = 1
        if metric == 'muscle_activation':
            metric_min = 0.0012142493999999998
            metric_max = 0.1659012612
        elif metric == 'consumed_endurance':
            metric_min = 0.018610636123524517
            metric_max = 9.599405943409115
        elif metric == 'rula':
            metric_min = 3.0
            metric_max = 9

        array_new[:, -1] -= metric_min
        array_new[:, -1] /= metric_max - metric_min
        if metric == 'muscle_activation':
            array_new[:, -1] = array_new[:, -1] * 5 + array_new[:, comfort_index + 1]
        array_sorted = array_new[array_new[:, -1].argsort()]

    return array_sorted





