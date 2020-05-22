using System.Collections.Generic;
using System.Threading;
using NetMQ;
using NetMQ.Sockets;
using UnityEngine;

public class PythonNetworking
{
    private bool clientStopped;
    private RequestSocket requestSocket;

    private byte[] frame;
    // for now only one request at a time is supported
    public string requestResult;
    private bool isAvailable;

    public PythonNetworking(bool sendWebCamFeed)
    {
        clientStopped = false;
        var clientThread = new Thread(NetMQClient);
        clientThread.Start();

        if (!sendWebCamFeed) return;
        var webCamUpload = new Thread(WebCamUpload);
        webCamUpload.Start();
    }
    
    

    public void StopClient()
    {
        clientStopped = true;
    }

    // ReSharper disable once InconsistentNaming
    private void NetMQClient()
    {
        AsyncIO.ForceDotNet.Force();

        requestSocket = new RequestSocket();
        requestSocket.Connect("tcp://127.0.0.1:5555");
        
        isAvailable = true;

        while (!clientStopped)
        {
            // Debug.Log("continuing");
        }

        requestSocket.Close();
        NetMQConfig.Cleanup();
    }

    private void WebCamUpload()
    {
        while (true)
        {
            if (clientStopped) return;
            if (frame == null) continue;
            requestSocket.SendMoreFrame("F");
            var frameBase64 = System.Convert.ToBase64String(frame);
            requestSocket.SendFrame(frameBase64);
            // handle result when response is sent
            requestSocket.ReceiveFrameString();
        }
    }

    public void SetFrame(byte[] currFrame)
    {
        frame = currFrame;
    }

    // Create queue of requests in case multiple have to be handled
    private void SimpleRequest(string endpoint, string request)
    {
        // wait until socket is available
        while (!isAvailable)
        {
            // Debug.Log("Socket unavailable");
        }

        isAvailable = false;
        if (request == null)
        {
            requestSocket.SendFrame(endpoint);
        }
        else
        {
            // Debug.Log(request);
            requestSocket.SendMoreFrame(endpoint);
            requestSocket.SendFrame(request);
        }

        var msg = requestSocket.ReceiveFrameBytes();
        isAvailable = true;
        requestResult = System.Text.Encoding.UTF8.GetString(msg);
        //requestResult = JsonUtility.FromJson<T>(msgString);
    }

    public void PerformRequest(string endpoint, string request)
    {
        requestResult = null;
        var requestThread = new Thread(() => SimpleRequest(endpoint, request));
        requestThread.Start();
    }

/*
    private Texture ByteArrayToTexture(IEnumerable<int> data)
    {
        // StreamReader reader = new StreamReader("Assets/img.json");
        // Client.ImgObject img = JsonUtility.FromJson<Client.ImgObject>(reader.ReadToEnd());
        //
        // reader.Close();

        byte[] image = new byte[640 * 480];
        int i = 0;
        foreach (int val in data) {
            image[i++] = (byte) val;
        }

        Texture2D tex = new Texture2D(640, 480, TextureFormat.R8, false);
        return tex;
    }
*/

}
