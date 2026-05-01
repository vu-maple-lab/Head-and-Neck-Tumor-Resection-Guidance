from paraview.simple import *

all_sources = GetSources()

for key, source in list(all_sources.items()):
    Delete(source)

Render()
