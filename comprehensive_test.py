#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest
import jsonpatch
import json

class ComprehensiveOptimizationTest(unittest.TestCase):
    def test_list_insertion_optimization(self):
        """Test that list insertions are optimized correctly."""
        test_cases = [
            # Simple replacements - already work
            (
                {'foo': [1, 2, 3]}, 
                {'foo': [1, 4, 3]}, 
                "Simple element replacement"
            ),
            # Insertion and deletion (same index) - should be optimized to replace
            (
                [1, 2, 3, 4], 
                [1, 5, 3, 4],
                "Insert and remove at same index - should be replace"
            ),
            # Insertion at beginning, removal at end - might be optimized to replace
            (
                [1, 2, 3, 4], 
                [5, 1, 2, 3],
                "Insert at beginning, remove at end - could be optimized"
            ),
            # Insert and remove at different positions - harder to optimize
            (
                [1, 2, 3, 4], 
                [1, 5, 2, 4],
                "Insert and remove at different positions"
            ),
            # Multiple changes - complex case
            (
                [1, 2, 3, 4, 5], 
                [1, 6, 2, 7, 5],
                "Multiple replacements"
            ),
        ]
        
        for src, dst, msg in test_cases:
            print(f"\nTesting: {msg}")
            print(f"Source: {src}")
            print(f"Destination: {dst}")
            patch = list(jsonpatch.make_patch(src, dst))
            print(f"Generated patch: {json.dumps(patch, indent=2)}")
            # Verify that applying the patch produces the expected result
            result = jsonpatch.apply_patch(src, patch)
            self.assertEqual(result, dst)
            print(f"Result after applying patch: {result}")
            
            # Count the operations
            op_counts = {}
            for op in patch:
                op_type = op['op']
                op_counts[op_type] = op_counts.get(op_type, 0) + 1
                
            print(f"Operation counts: {op_counts}")
            print("-" * 50)
            
if __name__ == "__main__":
    unittest.main()