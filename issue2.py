from jsonpatch import apply_patch, make_patch

old = ['a', 'b', ['d', 'e'], 'f']

new = ['a', 'd', ['e', 'g']]

patch = make_patch(old, new)

assert apply_patch(old, patch) == new
