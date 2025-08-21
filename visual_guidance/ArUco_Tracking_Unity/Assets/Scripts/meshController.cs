using UnityEngine;
using System.Collections.Generic;
using Microsoft.MixedReality.Toolkit.Utilities;
using Microsoft.MixedReality.Toolkit.UI;

public class meshController : MonoBehaviour
{
    // Reference to your specimen object
    public ModelFileLoader modelFileLoader;
    public List<string> loadedObjectNamesList;
    public int curSpecimenIndx = 0;
    public GameObject specimen;
    public PinchSlider transparencySlider;
    public GameObject meshMenu;
    float alphaValue;

    // Material with transparency that will be modified
    private Material materialWithTransparency;

    void Start()
    {
        specimen = null;
        loadedObjectNamesList = modelFileLoader.loadedObjectNamesList;
        alphaValue = 0.5f;
        if (transparencySlider != null)
        {
            transparencySlider.SliderValue = alphaValue;
        }

    }


    void Update()
    {
        if (loadedObjectNamesList.Count > 0 && specimen == null)
        {
            SetCurSpecimenObject(curSpecimenIndx);
        }
    }

    public void UpdateCurSpecimenObject()
    {
        if (loadedObjectNamesList.Count == 0)
        {
            return;
        }
        curSpecimenIndx = (curSpecimenIndx + 1) % loadedObjectNamesList.Count;

        SetCurSpecimenObject(curSpecimenIndx);
    }

    public void SetCurSpecimenObject(int curIdx)
    {
        curSpecimenIndx = curIdx;

        if (curSpecimenIndx >= loadedObjectNamesList.Count)
        {
            return;
        }
        // Hide all Specimens
        SetObjectsInvisible(loadedObjectNamesList);

        // show the currently visible specimeh, by converting the hashset<String> loadedObjectNames to list
        specimen = SetObjectVisibleByIndex(loadedObjectNamesList, curSpecimenIndx);
        Debug.Log("Currently Setting " + curSpecimenIndx + " to visible");
        Debug.Log(specimen);

        if (specimen != null)
        {
            specimen = modelFileLoader.GetChildThatIsNotTarget(specimen);
            Renderer renderer = specimen.GetComponent<Renderer>();

            // Get the material (note: using sharedMaterial would affect all objects using this material)
            // Using material creates an instance that only affects this object
            materialWithTransparency = renderer.material;
            SetTransparencyBySlider();
        }

    }

    public void SetObjectsInvisible(List<string> objectNames)
    {
        foreach (string name in objectNames)
        {
            GameObject obj = GameObject.Find(name);
            if (obj != null)
            {
                Renderer rend = obj.GetComponent<Renderer>();
                if (rend != null)
                { // TODO: handle the cases where only sub-components have renderers.
                    rend.enabled = false;
                }
                SetAllChildRenderersInvisible(obj);
            }
            else
            {
                Debug.LogWarning($"Object not found: {name}");
            }
        }
    }

    public GameObject SetObjectVisibleByIndex(List<string> objectNames, int index)
    {
        if (index < 0 || index >= objectNames.Count)
        {
            Debug.LogError("Index out of range.");
            return null;
        }

        string targetName = objectNames[index];
        GameObject obj = GameObject.Find(targetName);
        if (obj != null)
        {
            Renderer rend = obj.GetComponent<Renderer>();
            if (rend != null)
            {
                rend.enabled = true;
            }
            SetAllChildRenderersVisible(obj);
            return obj;
        }
        else
        {
            Debug.LogWarning($"Object not found: {targetName}");
        }
        return null;
    }

    public void SetAllChildRenderersInvisible(GameObject parent)
    {
        Renderer[] renderers = parent.GetComponentsInChildren<Renderer>(includeInactive: true);
        foreach (Renderer rend in renderers)
        {
            rend.enabled = false;
        }
    }

    public void SetAllChildRenderersVisible(GameObject parent)
    {
        Renderer[] renderers = parent.GetComponentsInChildren<Renderer>(includeInactive: true);
        foreach (Renderer rend in renderers)
        {
            rend.enabled = true;
        }
    }

    public void SetTransparencyBySlider()
    {
        if (specimen != null && transparencySlider != null)
        {
            SetTransparency(transparencySlider.SliderValue);
        }
    }

    public void IncTransparency(float dAlpha=-0.2f)
    {
        // Lower Alpha = Higher Transparency
        UpdateTransparency(dAlpha);
    }

    public void DecTransparency(float dAlpha=0.2f)
    {
        // Higher Alpha = Lower Transparency
        UpdateTransparency(dAlpha);
    }

    // Call this method to update transparency + slider value
    public void UpdateTransparency(float dAlpha)
    {
        if (specimen == null)
        {
            return;
        }

        // Get current color and modify its alpha
        Color color = materialWithTransparency.color;
        alphaValue = Mathf.Clamp01(color.a + dAlpha);
        color.a = alphaValue;
        materialWithTransparency.color = color;
        if (transparencySlider != null)
        {
            transparencySlider.SliderValue = alphaValue; // TODO: this would involk SetTransparency, which is not ideal.
        }
    }

    // Call this method to set transparency, but not slider value (0 = fully transparent, 1 = fully opaque)
    public void SetTransparency(float newAlphaValue)
    {
        if (specimen == null)
        {
            return;
        }
        // Ensure the alpha value is within valid range
        alphaValue = Mathf.Clamp01(newAlphaValue);

        // Get current color and modify its alpha
        Color color = materialWithTransparency.color;
        color.a = alphaValue;
        materialWithTransparency.color = color;
    }

    private void SetupTransparentMaterial()
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
    //public void hideMenu()
    //{
    //    if (meshMenu  != null)
    //    {
    //        meshMenu.enabled = false;
    //    }
    //}

    //public void showMenu()
    //{
    //    myText.enabled = true;
    //}
}