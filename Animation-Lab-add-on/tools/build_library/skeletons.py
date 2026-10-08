"""The skeletons in the Mesh2Motion library and the files each one is built from.

Mirrors mesh2motion-app/src/lib/RigConfig.ts. tests/test_library.py checks that the two
agree, so a skeleton or animation file added to the web app shows up as a failing test
here instead of silently missing from the add-on.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class AnimationPack:
    file: str  # GLB file name inside mesh2motion-app/static/animations
    pack: str  # short pack name shown in the catalog ("base", "addon", "mocap")


@dataclass(frozen=True)
class Skeleton:
    key: str             # SkeletonType value in the web app, also the .blend file name
    display_name: str    # shown in Blender
    rig_file: str        # GLB file name inside mesh2motion-app/static/rigs
    preview_folder: str  # folder inside mesh2motion-app/static/animpreviews
    # the one bone (besides root) whose position keys the web app keeps (RigConfig position_tracking_bone_name)
    position_bone: str
    packs: list = field(default_factory=list)

    @property
    def blend_file(self) -> str:
        return f"{self.key}.blend"

    @property
    def rig_name(self) -> str:
        return f"{self.display_name} Rig"


SKELETONS = [
    Skeleton("human", "Human", "rig-human.glb", "human", "pelvis", [
        AnimationPack("human-base-animations.glb", "base"),
        AnimationPack("human-addon-animations.glb", "addon"),
        AnimationPack("human-mocap-animations.glb", "mocap"),
    ]),
    Skeleton("fox", "Fox", "rig-fox.glb", "fox", "hips", [AnimationPack("fox-animations.glb", "base")]),
    Skeleton("bird", "Bird", "rig-bird.glb", "bird", "hips", [AnimationPack("bird-animations.glb", "base")]),
    Skeleton("dragon", "Dragon", "rig-dragon.glb", "dragon", "hips", [AnimationPack("dragon-animations.glb", "base")]),
    Skeleton("kaiju", "Kaiju", "rig-kaiju.glb", "kaiju", "hips", [AnimationPack("kaiju-animations.glb", "base")]),
    Skeleton("spider", "Spider", "rig-spider.glb", "spider", "hips", [AnimationPack("spider-animations.glb", "base")]),
    Skeleton("snake", "Snake", "rig-snake.glb", "snake", "head", [AnimationPack("snake-animations.glb", "base")]),
    Skeleton("fish", "Fish", "rig-shark.glb", "shark", "pelvis", [AnimationPack("shark-animations.glb", "base")]),
    Skeleton("horse", "Horse", "rig-horse.glb", "horse", "hips", [AnimationPack("horse-animations.glb", "base")]),
]
