
import jsonpatch
import json


def run_test(test):
    if 'comment' in test:
        print test['comment']

    if 'doc' in test and 'patch' in test:
        try:
            res = jsonpatch.apply_patch(test['doc'], test['patch'])





def tests_from_obj(tests):
    for test in tests:
        run_test(test)

