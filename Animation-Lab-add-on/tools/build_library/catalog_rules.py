"""Turns clip names into catalog fields: id, words, category and tags. No Blender needed."""

import json
import os
import re

CATEGORIES_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "categories.json")

# Mesh2Motion marks clips that move the character through the scene with an RM suffix
ROOT_MOTION_WORD = "rm"


def name_words(clip_name: str) -> list:
    """'Sword_Attack_RM' -> ['sword', 'attack', 'rm'], 'LayToIdle' -> ['lay', 'to', 'idle']."""
    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", clip_name)
    return [word.lower() for word in re.findall(r"[A-Za-z]+|\d+", spaced)]


def clip_slug(clip_name: str) -> str:
    """'Bow Pull Back' -> 'bow_pull_back'. Used in catalog ids."""
    return "_".join(re.findall(r"[a-z0-9]+", clip_name.lower()))


def load_rules(path: str = CATEGORIES_FILE) -> dict:
    with open(path, encoding="utf-8") as rules_file:
        return json.load(rules_file)


def category_for(clip_name: str, rules: dict) -> str:
    words = name_words(clip_name)
    text = " ".join(words)

    for rule in rules["rules"]:
        if any(text.startswith(prefix) for prefix in rule.get("prefixes", [])):
            return rule["category"]
        # a keyword has to start a word: 'eat' matches 'eating' but 'no' would not match 'nod'
        if any(re.search(r"(^| )" + re.escape(keyword), text) for keyword in rule.get("keywords", [])):
            return rule["category"]

    return rules["fallback"]


def tags_for(clip_name: str, skeleton_key: str, pack: str, root_motion: bool) -> list:
    tags = [word for word in name_words(clip_name) if word != ROOT_MOTION_WORD and len(word) > 1]
    tags += [skeleton_key, pack]
    if root_motion:
        tags.append("root-motion")

    # keep the order, drop repeats
    return list(dict.fromkeys(tags))
