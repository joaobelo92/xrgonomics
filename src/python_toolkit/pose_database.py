import sqlite3


def create_connection(db_file):
    """ create a database connection to the SQLite database
        specified by db_file
    :param db_file: database file
    :return: Connection object or None
    """
    conn = None
    try:
        conn = sqlite3.connect(db_file)
    except sqlite3.Error as e:
        print(e)

    return conn


def create_tables(conn):
    cursor = conn.cursor()

    # rtree_i32 for integers, rtree if higher precision is necessary
    # a voxel has its boundaries, for querying purposes, and center
    cursor.execute('''CREATE VIRTUAL TABLE IF NOT EXISTS voxels USING rtree_i32
                     (id,              -- Integer primary key
                      min_x, max_x,      -- Minimum and maximum X coordinate
                      min_y, max_y,      -- Minimum and maximum Y coordinate
                      min_z, max_z,       -- Minimum and maximum Z coordinate
                      +x REAL NOT NULL,
                      +y REAL NOT NULL,
                      +z REAL NOT NULL
        );''')

    # for each voxel we have multiple poses
    # constraints - perhaps elbow and end effector could be a cube?
    cursor.execute('''CREATE TABLE IF NOT EXISTS arm_poses
                 (arm_pose_id INTEGER PRIMARY KEY,
                  voxel_id INTEGER NOT NULL,
                  elbow_x REAL NOT NULL,
                  elbow_y REAL NOT NULL,
                  elbow_z REAL NOT NULL,
                  elv_angle REAL NOT NULL,
                  shoulder_elv REAL NOT NULL,
                  shoulder_rot REAL NOT NULL,
                  elbow_flexion REAL NOT NULL,
                  muscle_activation REAL,
                  reserve REAL,
                  consumed_endurance REAL,
                  rula INTEGER,
                  borg10 INTEGER,
                  muscle_activation_reserve REAL,
                  weighted_metrics REAL,
                  FOREIGN KEY (voxel_id) REFERENCES voxels (id))''')


def insert_voxel(conn, voxel):
    cursor = conn.cursor()
    sql = '''INSERT INTO voxels(min_x, max_x, min_y, max_y, min_z, max_z,
                                 x, y, z) 
             VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)'''

    cursor.execute(sql, voxel)
    return cursor.lastrowid


def insert_arm_pose(conn, arm_pose):
    cursor = conn.cursor()
    sql = '''INSERT INTO arm_poses(voxel_id, elbow_x, elbow_y, elbow_z,
                                   elv_angle, shoulder_elv, shoulder_rot, elbow_flexion)
             VALUES(?, ?, ?, ?, ?, ?, ?, ?)'''
    cursor.execute(sql, arm_pose)
    return cursor.lastrowid


def set_pose_activation_reserve(conn, pose_id, activation, reserve):
    cursor = conn.cursor()
    sql = '''UPDATE arm_poses
             SET muscle_activation = ? ,
                 reserve = ?
             WHERE arm_pose_id = ?'''
    cursor.execute(sql, (activation, reserve, pose_id))
    return cursor.lastrowid


def set_pose_consumed_endurance(conn, pose_id, consumed_endurance):
    cursor = conn.cursor()
    sql = '''UPDATE arm_poses
             SET consumed_endurance = ?
             WHERE arm_pose_id = ?'''
    cursor.execute(sql, (consumed_endurance, pose_id))
    return cursor.lastrowid


def set_pose_rula(conn, pose_id, rula):
    cursor = conn.cursor()
    sql = '''UPDATE arm_poses
             SET rula = ?
             WHERE arm_pose_id = ?'''
    cursor.execute(sql, (rula, pose_id))
    return cursor.lastrowid


def custom_query(conn, sql, params):
    cursor = conn.cursor()
    cursor.execute(sql, params)
    return cursor


def count_voxels(conn):
    cursor = conn.cursor()
    sql = '''SELECT COUNT() FROM voxels'''
    cursor.execute(sql)
    return cursor.fetchone()[0]


def get_voxel_point(conn, x, y, z):
    cursor = conn.cursor()
    sql = '''SELECT * FROM voxels
              WHERE min_x <= ? AND max_x > ?
                AND min_y <= ? AND max_y > ?
                AND min_z <= ? AND max_z > ?'''
    cursor.execute(sql, (x, x, y, y, z, z))
    # when looking for a particular pos, there will be at most
    return cursor.fetchone()


def get_all_voxels(conn):
    cursor = conn.cursor()
    sql = '''SELECT id, x, y, z FROM voxels'''
    cursor.execute(sql)
    return cursor.fetchall()


def get_voxel_by_id(conn, id):
    cursor = conn.cursor()
    sql = '''SELECT id, x, y, z FROM voxels
             WHERE id = ?'''
    cursor.execute(sql, (id,))
    return cursor.fetchone()


def get_all_poses(conn):
    cursor = conn.cursor()
    sql = '''SELECT * FROM arm_poses'''
    cursor.execute(sql)
    return cursor.fetchall()


def get_all_poses_muscle_activation(conn):
    cursor = conn.cursor()
    sql = '''SELECT arm_pose_id, muscle_activation, reserve 
             FROM arm_poses 
             WHERE muscle_activation IS NOT NULL AND reserve IS NOT NULL'''
    cursor.execute(sql)
    return cursor.fetchall()


def get_all_poses_all_metrics(conn):
    cursor = conn.cursor()
    sql = '''SELECT arm_pose_id, consumed_endurance, rula, muscle_activation_reserve
             FROM arm_poses'''
    cursor.execute(sql)
    return cursor.fetchall()


def get_all_poses_voxels(conn):
    cursor = conn.cursor()
    sql = '''SELECT arm_poses.arm_pose_id, voxels.x, voxels.y, voxels.z, arm_poses.elbow_x, arm_poses.elbow_y, 
             arm_poses.elbow_z, arm_poses.elv_angle, arm_poses.shoulder_elv, arm_poses.elbow_flexion
             FROM arm_poses INNER JOIN voxels ON arm_poses.voxel_id = voxels.id
             '''
    cursor.execute(sql)
    return cursor.fetchall()


def get_voxels_limits(conn):
    cursor = conn.cursor()
    result = []
    sql = '''SELECT MIN(x) FROM voxels'''
    cursor.execute(sql)
    result.append(cursor.fetchone()[0])
    sql = '''SELECT MAX(x) FROM voxels'''
    cursor.execute(sql)
    result.append(cursor.fetchone()[0])
    sql = '''SELECT MIN(y) FROM voxels'''
    cursor.execute(sql)
    result.append(cursor.fetchone()[0])
    sql = '''SELECT MAX(y) FROM voxels'''
    cursor.execute(sql)
    result.append(cursor.fetchone()[0])
    sql = '''SELECT MIN(z) FROM voxels'''
    cursor.execute(sql)
    result.append(cursor.fetchone()[0])
    sql = '''SELECT MAX(z) FROM voxels'''
    cursor.execute(sql)
    result.append(cursor.fetchone()[0])
    return result


def get_poses_in_voxel(conn, voxel_id, metric):
    cursor = conn.cursor()
    sql = '''SELECT arm_pose_id, elbow_x, elbow_y, elbow_z, {}, muscle_activation_reserve FROM arm_poses
             WHERE voxel_id = ?'''.format(metric)
    cursor.execute(sql, (voxel_id,))
    return cursor


def count_poses(conn):
    cursor = conn.cursor()
    sql = '''SELECT COUNT() FROM arm_poses'''
    cursor.execute(sql)
    return cursor.fetchone()[0]


def drop_tables(conn):
    cursor = conn.cursor()
    sql = '''DROP TABLE IF EXISTS voxels'''
    cursor.execute(sql)
    sql = '''DROP TABLE IF EXISTS arm_poses'''
    cursor.execute(sql)
    conn.commit()


# TODO: update name to activation something
def get_voxels_with_pose_cursor(conn):
    cursor = conn.cursor()
    sql = '''SELECT voxels.id, arm_poses.arm_pose_id, MIN(muscle_activation), arm_poses.reserve
             FROM voxels LEFT OUTER JOIN arm_poses ON arm_poses.voxel_id = voxels.id 
             GROUP BY voxels.id'''
    cursor.execute(sql)
    return cursor


def get_voxels_ca_with_pose_cursor(conn):
    cursor = conn.cursor()
    sql = '''SELECT voxels.id, arm_poses.arm_pose_id, MIN(consumed_endurance)
             FROM voxels LEFT OUTER JOIN arm_poses ON arm_poses.voxel_id = voxels.id 
             GROUP BY voxels.id'''
    cursor.execute(sql)
    return cursor


def get_max_ca(conn):
    cursor = conn.cursor()
    sql = '''SELECT MAX(consumed_endurance)
             FROM arm_poses'''
    cursor.execute(sql)
    return cursor.fetchone()


def get_min_max_rula(conn):
    cursor = conn.cursor()
    sql = '''SELECT MIN(rula), MAX(rula)
             FROM arm_poses'''
    cursor.execute(sql)
    return cursor.fetchone()

# max_activation = 0.23175466239999998
# max_reserve = 1135.5161096400002
# voxels_new[:, 6] /= max_activation
# voxels_new[:, 7] /= max_reserve
# # only for visualization purposes multiply muscle activation
# voxels_new[:, 8] = voxels_new[:, 6] * 7.5 + voxels_new[:, 7] * 2.5
# voxels_sorted = voxels_new[voxels_new[:, 8].argsort()]

#

# sql = '''SELECT id FROM voxels WHERE id MATCH circle(0, 0, 30.0)'''
# cursor.execute(sql)
# print(cursor.fetchone())
# print(get_min_max_rula(c))
# print(get_max_ca(c))
# print(get_voxels_with_pose_cursor(c).fetchall())
# print(get_voxels_with_pose_cursor(c).fetchall())
# print(get_voxels_limits(c))
# print(count_poses(c))
# create_tables(c)
# print(get_anchor_point(c, 4, 5, 2))
# insert_anchor(c, (1, 1, 4, 7, 3, 4))
# print(count_anchors(c))
# r = query_anchor_point(c, 10, 23, 10)
# for row in r:
#     print(row)
