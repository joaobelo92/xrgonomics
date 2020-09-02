using System;
using Newtonsoft.Json;


public static class Serialization
{
        
    [Serializable]
    public class Voxel
    {
        public int id;
        public float[] position;
        [JsonProperty(PropertyName = "num_poses")]
        public int? numPoses;
        [JsonProperty(PropertyName = "pose_id")]
        public int? poseId;
        public float? comfort;

        public override string ToString()
        {
            return "x: " + position[0] + " " + "y: " + position[1] + " " +
                   "z: " + position[2] + " ";
        }
    }

    [Serializable]
    public class Limits
    {
        [JsonProperty(PropertyName = "min_x")]
        public float minX;
        [JsonProperty(PropertyName = "max_x")]
        public float maxX;
        [JsonProperty(PropertyName = "min_y")]
        public float minY;
        [JsonProperty(PropertyName = "max_y")]
        public float maxY;
        [JsonProperty(PropertyName = "min_z")]
        public float minZ;
        [JsonProperty(PropertyName = "max_z")]
        public float maxZ;
    }
    
    [Serializable]
    public class PoseRequest
    {
        public float x;
        public float y;
        public float z;
        public string metric;
    }
    
    
    [Serializable]
    public class ComputeErgonomicCostRequest
    {
        public ComputeErgonomicCostRequest(float armProperLength, float forearmHandLength, int voxelSideLength)
        {
            this.armProperLength = armProperLength;
            this.forearmHandLength = forearmHandLength;
            this.voxelSideLength = voxelSideLength;
        }
        public float armProperLength;
        public float forearmHandLength;
        public float voxelSideLength;
    }
    
    [Serializable]
    public class VoxelRequest
    {
        public string metric;

        public Constraint[] constraints;
    }
    
    [Serializable]
    public class OptimalPosRequest
    {
        public float[] polygon;
    }
    
    [Serializable]
    public class Pose
    {
        public int id;
        public float[] elbow;
        public float comfort;
    }

    [Serializable]
    public class Constraint
    {
        public int axis;
        public string constraint;
        public float value;

        public Constraint(int axis, string constraint, float value)
        {
            this.axis = axis;
            this.constraint = constraint;
            this.value = value;
        }
        
        public override string ToString()
        {
            var axisStr = new string[] {"X", "Y", "Z"};
            return $"{axisStr[axis]} {constraint} {value:n2}";
        }
    }
    
}
