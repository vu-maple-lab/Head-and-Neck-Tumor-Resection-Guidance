using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using System.IO;
using Dummiesman;
using UnityEngine.UI;


public class ModelFileLoader : MonoBehaviour
{
    public HashSet<string> loadedObjectNames = new HashSet<string>();
    public List<string> loadedObjectNamesList = new List<string>();

    public Text myText;
    [SerializeField] private GameObject modelContainerObj;
    private string modelFileFolderPath = "/";
    [SerializeField] private string modelFilePrefix = "specimen";
    private bool isFileLoaded = false; // Prevent concurrent loading calls

    // Start is called before the first frame update
    void Start()
    {
        modelFileFolderPath = Application.persistentDataPath; // Path.Combine(System.Environment.GetFolderPath(System.Environment.SpecialFolder.MyDocuments)); // Path.GetDirectoryName(modelFileFolderPath);
    }

    // Update is called once per frame
    void Update()
    {
        if (!isFileLoaded)
        {
            CheckandLoadAllSuitableFiles();
            //myText.text += "\n Finding File from " + modelFileFolderPath;
        }
        else
        {
            //myText.text += "\n File Loaded! from " + modelFileFolderPath;
        }
    }

    private void SetupTransparentMaterial(Material materialWithTransparency)
    {
        // Standard shader transparency setup
        materialWithTransparency.SetFloat("_Mode", 2); // 3 = Transparent mode; 2 = Fade mode
        materialWithTransparency.SetInt("_SrcBlend", (int)UnityEngine.Rendering.BlendMode.SrcAlpha);
        materialWithTransparency.SetInt("_DstBlend", (int)UnityEngine.Rendering.BlendMode.OneMinusSrcAlpha);
        materialWithTransparency.SetInt("_ZWrite", 0);
        materialWithTransparency.DisableKeyword("_ALPHATEST_ON");
        materialWithTransparency.EnableKeyword("_ALPHABLEND_ON");
        materialWithTransparency.DisableKeyword("_ALPHAPREMULTIPLY_ON");
        materialWithTransparency.renderQueue = 3000;
    }

    public GameObject GetChildThatIsNotTarget(GameObject parentObject)
    {
        // Make sure parent exists and has children
        if (parentObject == null || parentObject.transform.childCount == 0)
        {
            return null;
        }

        // Go through children (max 2 as per your description)
        for (int i = 0; i < parentObject.transform.childCount; i++)
        {
            Transform child = parentObject.transform.GetChild(i);

            // If this child is not named "target", return it
            if (child.name.ToLower() != "target" && child.name.ToLower() != "sphere")
            {
                return child.gameObject;
            }
        }

        // If all children are named "target" or there are no children
        return null;
    }

    public void initializeSpecimenObject(GameObject specimen)
    {
        Debug.Log(specimen.name);
        GameObject actualSpecimen = GetChildThatIsNotTarget(specimen);

        // Get the renderer component from the specimen
        Renderer renderer = actualSpecimen.GetComponent<Renderer>();

        // Get the material (note: using sharedMaterial would affect all objects using this material)
        // Using material creates an instance that only affects this object
        Material materialWithTransparency = renderer.material;
        SetupTransparentMaterial(materialWithTransparency);
    }

    private void CheckandLoadAllSuitableFiles()
    {
        string[] objFiles = Directory.GetFiles(modelFileFolderPath, modelFilePrefix + "*.obj");
        if (objFiles.Length == 0)
        {
            // Debug.Log("No OBJ files found with prefix: " + modelFilePrefix);
            return;
        }

        foreach (string objPath in objFiles)
        {
            string fileNameWithoutExt = Path.GetFileNameWithoutExtension(objPath);
            string mtlPath = Path.Combine(modelFileFolderPath, fileNameWithoutExt + ".mtl");

            if (loadedObjectNames.Contains(fileNameWithoutExt))
            {
                // Debug.Log($"GameObject '{fileNameWithoutExt}' already exists in the scene. Skipping.");
                continue;
            }

            if (File.Exists(mtlPath))
            {
                Debug.Log($"Found OBJ and MTL: {objPath}, {mtlPath}");

                // Load the model
                loadObjFile(objPath, mtlPath, modelContainerObj);
                // CheckAndLoadFile(objPath, mtlPath);
                // loadObjFile(objPath, mtlPath, modelContainerObj);
                
                GameObject curObj = GameObject.Find(fileNameWithoutExt);
                initializeSpecimenObject(curObj);
                loadedObjectNames.Add(curObj.name);
                loadedObjectNamesList.Add(curObj.name);
            }
        }
    }

    private void CheckAndLoadFile(string modelFileName, string materialFileName)
    {
        string filePath = Path.Combine(modelFileFolderPath, modelFileName);
        string mtlPath = Path.Combine(modelFileFolderPath, materialFileName);

        Debug.Log(filePath);
        if (File.Exists(filePath) && File.Exists(mtlPath))
        {
            Debug.Log($"File found: {filePath}");
            // Call your function to load the GLTF file
            loadObjFile(filePath, mtlPath, modelContainerObj);

            string fileNameWithoutExt = Path.GetFileNameWithoutExtension(filePath);
            GameObject curObj = GameObject.Find(fileNameWithoutExt);
            initializeSpecimenObject(curObj);
            loadedObjectNames.Add(curObj.name);
            loadedObjectNamesList.Add(curObj.name);
        }
        else
        {
            Debug.Log("File not found.");
        }
    }

    private void loadObjFile(string filePath, string mtlPath, GameObject parentObj)
    {
        // Your OBJ loading logic goes here
        var loadedObj = new OBJLoader().Load(filePath, mtlPath);
        loadedObj.transform.SetParent(parentObj.transform);
        loadedObj.transform.localEulerAngles = Vector3.zero;
        loadedObj.transform.localPosition = Vector3.zero;
        Debug.Log($"OBJ file loaded from: {filePath}");
    }
}
