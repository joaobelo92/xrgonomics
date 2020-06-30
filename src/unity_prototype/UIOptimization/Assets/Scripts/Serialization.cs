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
        [JsonProperty(PropertyName = "muscle_activation")]
        public float? muscleActivation;
        public float? reserve;

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
    }
    
    [Serializable]
    public class VoxelRequest
    {
        public string x;
        public string y;
        public string z;
        public string metric;
    }
    
    [Serializable]
    public class Pose
    {
        public int id;
        public float[] elbow;
    }
    
    
}
