import unittest
from os import EX_OSERR

from buoy.sms.sms_cli import run as sms_server


config_buoy_file = "./test/config/sms.yaml"
config_log_file = "./test/config/logging.yaml"


class TestConsoleCLI(unittest.TestCase):
    def test_run_sms_server(self):
        with self.assertRaises(SystemExit) as cm:
            sms_server(config=config_buoy_file, config_log_file=config_log_file)

        self.assertEqual(cm.exception.code, EX_OSERR)


    ''''
    def test_run_zte_disconnect(self):
        zte_disconnect(config_log_file=config_log_file)
    


    def test_run_zte_connect(self):
        zte_connect(config_buoy=config_buoy_file, config_log_file=config_log_file)


    def test_run_update_public_ip(self):
        update_public_ip(config_file=config_ip_file, config_log_file=config_log_file)



        

        
    def test_run_current_meter(self):
        current_meter(config_buoy=config_buoy_file, config_log_file=config_log_file)

    def test_run_public_ip(self):
        public_ip()

    def test_run_is_connected_to_internet(self):
        connected_to_internet(config=config_buoy_file, config_log_file=config_log_file)



    def test_run_weather_station(self):
        weather_station(config_buoy=config_buoy_file,  config_log_file=config_log_file)

'''

if __name__ == '__main__':
    unittest.main()
