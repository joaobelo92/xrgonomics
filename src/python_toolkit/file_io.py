import pandas as pd
import numpy as np


def generate_arm_static_mot(filename, coordinate_names, coordinates, num_rows=15, rate=100, default_pose=True):
    coordinate_names = ["time"] + coordinate_names
    build_mot_header(filename, num_rows, len(coordinate_names))

    with open(filename, 'a') as f:
        f.write('\t'.join(str(i) for i in coordinate_names) + '\n')

    time_offset = 1 / rate
    data = []

    if default_pose and len(coordinates) is 4:
        coordinates = [0, -90, 0, 0, 0, 0] + coordinates + [0, 0, 0, 0]

    for i in range(num_rows):
        data.append([time_offset * i] + coordinates)

    df = pd.DataFrame(data)
    write_data_trc(df, filename)


def write_data_trc(data, filepath):
    data.to_csv(filepath, sep='\t', index=False, mode='a', header=False)


def build_mot_header(filename, num_rows, num_cols, version=1, degrees=True):
    if not filename.endswith('.mot'):
        raise NameError('Filename must end in .mot')

    header = ['Coordinates',
              'version={}'.format(version),
              'nRows={}'.format(num_rows),
              'nColumns={}'.format(num_cols),
              'inDegrees={}'.format('yes' if degrees else 'no'),
              '',
              'endheader']

    with open(filename, 'w') as f:
        for h in header:
            f.write(h + '\n')


def read_so_results(filepath, num_muscles=50):
    data = pd.read_csv(filepath, sep='\t', skiprows=8)
    activations = data.to_numpy()[:, 1:num_muscles+1]
    avg_activations = np.average(activations, axis=1)
    reserve = np.abs(data.to_numpy()[:, num_muscles+1:])
    reserve_sum = np.sum(reserve, axis=1)
    min_activation_idx = np.argmin(avg_activations)
    min_reserve_idx = np.argmin(reserve_sum)
    # print(reserve_sum, len(reserve_sum))
    # print(avg_activations, len(avg_activations))
    print(min_activation_idx)
    print(min_reserve_idx)
    print(np.sum(avg_activations[min_reserve_idx]), reserve_sum[min_reserve_idx])


# for i in range(4):
#     read_so_results('../../results/anchor-{}.mot/MoBL_ARMS_Upper_Limb_Model_OpenSim_StaticOptimization_'
#                     'activation.sto'.format(i))

# read_so_results('../../results/very-hard/MoBL_ARMS_Upper_Limb_Model_OpenSim_StaticOptimization_activation.sto')
# read_so_results('../../results/hard/MoBL_ARMS_Upper_Limb_Model_OpenSim_StaticOptimization_activation.sto')
# read_so_results('../../assets/MoBL_ARMS_Upper_Limb_Model_OpenSim_StaticOptimization_activation.sto')
# generate_arm_static_mot('test.mot',
#                         ['time', 'r_x', 'r_y', 'r_z', 't_x', 't_y', 't_z', 'elv_angle', 'shoulder_elv', 'shoulder_rot',
#                          'elbow_flexion', 'pro_sup', 'deviation', 'flexion'],
#                         [elv_angle, shoulder_elv, shoulder_rot, elbow_flexion])
