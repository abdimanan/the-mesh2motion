"""Add-on preferences (Edit > Preferences > Add-ons > Animation Lab)."""

import bpy
from bpy.props import FloatProperty, IntProperty
from bpy.types import AddonPreferences

from . import library


def get(context):
    return context.preferences.addons[__package__].preferences


class ANIMLAB_AP_preferences(AddonPreferences):
    bl_idname = __package__

    thumbnail_scale: FloatProperty(
        name="Thumbnail Size",
        description="How large animation previews are drawn in the Animation Lab panel",
        default=4.5,
        min=2.0,
        max=12.0,
    )
    page_size: IntProperty(
        name="Animations per Page",
        description="How many animations the browser shows at once",
        default=12,
        min=4,
        max=48,
    )

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "thumbnail_scale")
        layout.prop(self, "page_size")

        box = layout.box()
        box.label(text="Library", icon="ASSET_MANAGER")
        error = library.load_error()
        if error:
            box.label(text=error, icon="ERROR")
        else:
            animations = len(library.animations())
            box.label(text=f"{animations} animations for {len(library.skeletons())} skeletons")
        box.label(text=library.LIBRARY_DIR, icon="FILE_FOLDER")


def register():
    bpy.utils.register_class(ANIMLAB_AP_preferences)


def unregister():
    bpy.utils.unregister_class(ANIMLAB_AP_preferences)
