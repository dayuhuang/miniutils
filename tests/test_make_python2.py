from unittest import TestCase
from miniutils.py2_wrap import MakePython2


class TestMakePython2(TestCase):
    def test_wrapper_basic(self):
        @MakePython2()
        def get_version():
            import sys
            return sys.version_info[0]

        self.assertEqual(get_version(), 2)
        self.assertEqual(get_version(), 2)  # Run a second time to ensure process is still alive

        import sys
        self.assertGreaterEqual(sys.version_info[0], 3)

    def test_wrapper_import(self):
        @MakePython2(imports=['sys'])
        def get_version():
            return sys.version_info[0]

        self.assertEqual(get_version(), 2)
        self.assertEqual(get_version(), 2)  # Run a second time to ensure process is still alive

        import sys
        self.assertGreaterEqual(sys.version_info[0], 3)

    def test_wrapper_globals(self):
        # noinspection PyUnresolvedReferences
        @MakePython2(global_values={'x': 5})
        def add(y):
            return x + y

        self.assertEqual(add(3), 8)
        self.assertEqual(add(10), 15)  # Run a second time to ensure process is still alive

    def test_wrapper_exception(self):
        @MakePython2()
        def fail():
            raise Exception('SUCCEED: just making sure exception passing works')

        self.assertRaisesRegex(RuntimeError, 'SUCCEED', fail)

    def test_wrapper_by_name(self):
        uname = MakePython2('os.uname', imports=['os'], copy_function_body=False).function
        import os
        self.assertEqual(uname(), os.uname())
