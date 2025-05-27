import unittest
import jsonpatch

class IssueBugTestCase(unittest.TestCase):
    def test_numeric_string_dict_keys(self):
        """Test the issue with numeric string dict keys"""
        src = {'1': 'def'}
        dst = {'test': '1', 'b': 'def'}
        # This should not raise an exception
        patch = jsonpatch.make_patch(src, dst)
        # Verify the patch works as expected
        applied = jsonpatch.apply_patch(src, patch)
        self.assertEqual(applied, dst)

if __name__ == '__main__':
    unittest.main()