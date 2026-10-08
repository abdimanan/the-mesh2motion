"""Animation Lab: the Mesh2Motion animation library inside Blender.

Adds an "Animation Lab" tab to the 3D Viewport sidebar. The library itself (one .blend per
skeleton, catalog.json and thumbnails) ships inside the add-on, in library/, and is built
from the Mesh2Motion web app by tools/build_library/build.sh.
"""

from . import operators, preferences, preview, previews, properties, ui

# registered in this order, unregistered in reverse (so a running preview is stopped while
# the operators and properties it uses still exist)
_MODULES = (preferences, properties, operators, ui, preview)


def register():
    previews.register()
    for module in _MODULES:
        module.register()


def unregister():
    for module in reversed(_MODULES):
        module.unregister()
    previews.unregister()
