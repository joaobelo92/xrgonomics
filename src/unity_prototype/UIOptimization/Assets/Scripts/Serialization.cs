using System;
using Newtonsoft.Json;


public static class Serialization
{
        
    [Serializable]
    public class Anchor
    {
        public int id;
        public float[] position;

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
    public class AnchorRequest
    {
        public string x;
        public string y;
        public string z;
    }
    
    [Serializable]
    public class Pose
    {
        public int id;
        public float[] elbow;
    }
    
    
}
