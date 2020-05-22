using System;
using System.Collections.Generic;
using System.Runtime.InteropServices;
using UnityEngine;

public static class Helpers
{
    public static GameObject CreatePrimitiveGameObject(PrimitiveType type, Vector3 position, Vector3 scale, 
        Transform parent = null, string name = null, bool defaultMaterial = true, Material material = null)
    {
        var obj = GameObject.CreatePrimitive(type);
        obj.transform.position = position;
        obj.transform.localScale = scale;
        obj.transform.parent = parent;
        if (name != null)
        {
            obj.name = name;
        }

        if (!defaultMaterial)
        {
            obj.GetComponent<Renderer>().material = material;
        }
        return obj;
    }
    
    public static byte[] Color32ArrayToByteArray(IReadOnlyCollection<Color32> colors)
    {
        if (colors == null || colors.Count == 0)
            return null;

        var lengthOfColor32 = Marshal.SizeOf(typeof(Color32));
        var length = lengthOfColor32 * colors.Count;
        var bytes = new byte[length];

        var handle = default(GCHandle);
        try
        {
            handle = GCHandle.Alloc(colors, GCHandleType.Pinned);
            var ptr = handle.AddrOfPinnedObject();
            Marshal.Copy(ptr, bytes, 0, length);
        }
        finally
        {
            if (handle != default(GCHandle))
                handle.Free();
        }

        return bytes;
    }
}
