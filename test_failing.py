#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest
import jsonpatch

class FailingOptimizationTest(unittest.TestCase):
    def test_list_replacement_optimization(self):
        # A case where a list element is replaced with a new value
        src = {'foo': [1, 2, 3]}
        dst = {'foo': [1, 4, 3]}
        patch = list(jsonpatch.make_patch(src, dst))
        print("Patch:", patch)
        self.assertEqual(len(patch), 1)
        self.assertEqual(patch[0]['op'], 'replace')
        self.assertEqual(patch[0]['path'], '/foo/1')
        self.assertEqual(patch[0]['value'], 4)

    def test_list_insertion_deletion(self):
        # A case where elements are both inserted and deleted
        src = [1, 2, 3, 4]
        dst = [1, 5, 2, 4]
        patch = list(jsonpatch.make_patch(src, dst))
        print("Insertion/Deletion Patch:", patch)
        # Expected: replace operation at index 1 and removal of index 2
        # Instead of producing multiple operations
        # The optimization should collapse sequential operations when possible
        
if __name__ == "__main__":
    unittest.main()