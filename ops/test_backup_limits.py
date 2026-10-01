import unittest
from backup_segments import CAP_BYTES,WARNING_BYTES,enforce_capacity,capacity_warning
class BackupLimits(unittest.TestCase):
    def test_effective_limits(self):
        self.assertEqual(CAP_BYTES,10737418240);self.assertEqual(WARNING_BYTES,8589934592)
    def test_warning_boundary(self):
        self.assertFalse(capacity_warning(WARNING_BYTES-1));self.assertTrue(capacity_warning(WARNING_BYTES));self.assertTrue(capacity_warning(WARNING_BYTES+1))
    def test_cap_boundary(self):
        enforce_capacity(CAP_BYTES-1,1)
        with self.assertRaisesRegex(RuntimeError,'10 GiB'):enforce_capacity(CAP_BYTES-1,2)
        with self.assertRaises(RuntimeError):enforce_capacity(CAP_BYTES,1)
if __name__=='__main__':unittest.main()
