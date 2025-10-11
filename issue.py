import jsonpatch

src_obj = {'a': [{'id': [1]}, {'id': [2]}], 'b': [{'id': 5}]}
tgt_obj = {'a': [{'id': []}, {'id': [1]}], 'b': [{'id': 5, 'newKey': 2}]}

patch = jsonpatch.make_patch(src_obj, tgt_obj)
print(patch)

# Check normal application of the patch
try:
    tgt_obj_check = jsonpatch.apply_patch(src_obj, patch)
    print('Forward', 'OK' if len(jsonpatch.make_patch(tgt_obj, tgt_obj_check).patch) == 0 else 'ERROR', '->', tgt_obj_check)
except Exception as e:
    print('Forward', 'Error', '->', type(e).__name__)

# Check reverse application of the patch
try:
    tgt_obj_check = jsonpatch.apply_patch(src_obj, patch.patch[::-1])
    print('Reverse', 'OK' if len(jsonpatch.make_patch(tgt_obj, tgt_obj_check).patch) == 0 else 'ERROR', '->', tgt_obj_check)
except Exception as e:
    print('Reverse', 'Error', '->', type(e).__name__)
