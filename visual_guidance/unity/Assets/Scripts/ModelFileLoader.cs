using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using System.IO;
using Dummiesman;

public class ModelFileLoader : MonoBehaviour
{

    [SerializeField] private GameObject modelContainerObj;
    private string modelFileFolderPath = "/";
    [SerializeField] private string modelFileName = "specimen.obj";
    [SerializeField] private string materialFileName = "specimen.mtl";
    private bool isFileLoaded = false; // Prevent concurrent loading calls

    // Start is called before the first frame update
    void Start()
    {
        modelFileFolderPath = Path.Combine(System.Environment.GetFolderPath(System.Environment.SpecialFolder.MyDocuments)); // Path.GetDirectoryName(modelFileFolderPath);
    }

    // Update is called once per frame
    void Update()
    {
        if (!isFileLoaded)
        {
            CheckAndLoadFile();
        }
    }
    private void CheckAndLoadFile()
    {
        string filePath = Path.Combine(modelFileFolderPath, modelFileName);
        string mtlPath = Path.Combine(modelFileFolderPath, materialFileName);

        Debug.Log(filePath);
        if (File.Exists(filePath))
        {
            Debug.Log($"File found: {filePath}");
            // Call your function to load the GLTF file
            loadObjFile(filePath, mtlPath, modelContainerObj);
            isFileLoaded = true;
        }
        else
        {
            Debug.Log("File not found.");
        }
    }

    private void loadObjFile(string filePath, string mtlPath, GameObject parentObj)
    {
        Debug.Log($"Loading OBJ file: {filePath}");
        // Your OBJ loading logic goes here
        var loadedObj = new OBJLoader().Load(filePath, mtlPath);
        loadedObj.transform.SetParent(parentObj.transform);
        loadedObj.transform.localEulerAngles = Vector3.zero;
        loadedObj.transform.localPosition = Vector3.zero;
    }
}
