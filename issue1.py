from jsonpatch import apply_patch, make_patch

old = [
    {"x": ["a", {"y": ["b"]}], "z": "a"},
    {"x": ["c", {"d": ["d"]}], "z": "c"},
    {},
]

new = [
    {"x": ["c", {"y": ["d"]}], "z": "c"},
    {},
]

patch = make_patch(old, new)

assert apply_patch(old, patch) == new
