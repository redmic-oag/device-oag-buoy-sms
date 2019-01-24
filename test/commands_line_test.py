import unittest
from os import EX_OSERR

from sms.sms_cli import run as sms_server


config_sms_file = "./test/config/sms.yaml"
config_log_file = "./test/config/logging.yaml"


class TestConsoleCLI(unittest.TestCase):
    def test_run_sms_server(self):
        with self.assertRaises(SystemExit) as cm:
            sms_server(config=config_sms_file, config_log_file=config_log_file)

        self.assertEqual(cm.exception.code, EX_OSERR)


if __name__ == '__main__':
    unittest.main()
