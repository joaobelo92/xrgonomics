import opensim as osim
import math


def retrieve_dependent_coordinates(model, elv_angle, shoulder_elv, shoulder_rot, elbow_flexion):
    initial_state = model.initSystem()

    coordinates = {}
    for coordinate in model.getCoordinateSet():
        coordinates[coordinate.getName()] = coordinate

    # for name, coordinate in coordinates.items():
    #     print(name, coordinate.getValue(initial_state))

    coordinates["elv_angle"].setValue(initial_state, math.radians(elv_angle), True)
    coordinates["shoulder_elv"].setValue(initial_state, math.radians(shoulder_elv), True)
    coordinates["shoulder_rot"].setValue(initial_state, math.radians(shoulder_rot), True)
    coordinates["elbow_flexion"].setValue(initial_state, math.radians(elbow_flexion), True)

    coordinate_values = {}
    for name, coordinate in coordinates.items():
        coordinate_values[name] = math.degrees(coordinate.getValue(initial_state))

    # body_set = {}
    # for body_part in model.getBodySet():
    #     body_set[body_part.getName()] = body_part
    #     print(body_part.getName(), body_part.getPositionInGround(initial_state))

    marker_set = {}
    for marker in model.getMarkerSet():
        pos_vec = marker.getLocationInGround(initial_state)
        marker_set[marker.getName()] = (pos_vec[0], pos_vec[1], pos_vec[2])
        # print(marker.getName(), marker.getLocationInGround(initial_state))

    return coordinate_values, marker_set


def run_static_optimization(so_file):
    # model = osim.Model(model_path)
    tool = osim.AnalyzeTool(so_file)
    # # model t and r coordinates have to be locked
    tool.run()
    # print(model.updAnalysisSet())


# run_static_optimization("/Users/joaobelo/Code/xrgonomics/experiments/pose_1/pose_1_so.xml")
# anchors = [[30, 120, -20, 50], [30, 20, 20, 100], [30, 5, 0, 70], [0, 0, 0, 0]]
# model_path = "../../assets/MoBL_ARMS_module6_7_CMC_updated_unlocked.osim"
# rows = 20

# for idx, a in enumerate(anchors):
#     coordinates, values = retrieve_dependent_coordinates(model_path, a[0], a[1], a[2], a[3])
#     filename = 'anchor-{}.mot'.format(idx)
#     file_io.generate_arm_static_mot('../../assets/{}'.format(filename), list(coordinates), values, num_rows=rows)
#     # update setup xml
#     root = xml.etree.ElementTree.parse('/Users/joaobelo/Code/muscle-activation-optimization/assets/so.xml')
#     root.find('./AnalyzeTool/coordinates_file').text = filename
#     res_dir = '/Users/joaobelo/Code/muscle-activation-optimization/results/{}'.format(filename)
#     root.find('./AnalyzeTool/results_directory').text = res_dir
#     root.find('./AnalyzeTool/final_time').text = '0.{}'.format(rows)
#     root.write('/Users/joaobelo/Code/muscle-activation-optimization/assets/so.xml')
#     static_optimization(model_path)
# coordinates, values = retrieve_dependent_coordinates("../../assets/MoBL_ARMS_module6_7_CMC_updated_unlocked.osim",
#                                                      15, 45, 35, 100)
# coord, markers = retrieve_dependent_coordinates("../../assets/MoBL_ARMS_module6_7_CMC_updated_unlocked.osim",
#                                                      0, 90, 0, 0)
# print(str(coord) + "\n" + str(markers))

# file_io.generate_arm_static_mot("../../assets/hard.mot", list(coordinates), values, num_rows=50)
# static_optimization("../assets/ThoracoscapularShoulderModel.osim", "", "")
