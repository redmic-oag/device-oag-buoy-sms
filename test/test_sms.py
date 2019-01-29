import unittest
from unittest.mock import patch, MagicMock, call
from buoy.lib.utils.config import load_config
from sms.sms_cmd import SMSCMDDaemon, UnrecognizedCommandException, UnauthorizedPhoneNumberException

from nose.tools import ok_, eq_

config_file = "test/config/sms.yaml"


class FakeSMSCMDDaemon(SMSCMDDaemon):
    def __init__(self, **kwargs):
        SMSCMDDaemon.__init__(self, config=load_config(path_config=config_file))
        self.sms_received = kwargs.pop('sms_received', [])
        self._active = True

    def get_sms_unread(self):
        return self.sms_received.copy()

    def delete_sms(self, sms_in):
        for index, sms in enumerate(self.sms_received):
            if sms['id'] == sms_in['id']:
                self.sms_received.pop(index)
                break

        if not len(self.sms_received):
            self._active = False


class SMSIntegrationBaseMDTests(unittest.TestCase):
    item_class = None
    db_conf = None
    data = None
    skip_test = False

    @classmethod
    def setUpClass(cls):
        global skip_test

        if cls is SMSIntegrationSimulateCMDTests or cls is SMSIntegrationRunCMDTests:
            skip_test = True
        else:
            skip_test = False

        super(SMSIntegrationBaseMDTests, cls).setUpClass()

    def setUp(self):
        """ Module level set-up called once before any tests in this file are executed. Creates a temporary database
        and sets it up """

        if skip_test:
            self.skipTest("Skip BaseTest tests, it's a base class")


class SMSIntegrationSimulateCMDTests(SMSIntegrationBaseMDTests):

    @patch('sms.sms_cmd.check_output')
    def test_should_sendSMS_whenReceiveSMS(self, mock_check_output):
        sms_sended_expected = []
        executions = []

        for sms in self.sms_received:
            if 'execution' in sms:
                executions.append(sms['execution'])
            if 'sms_sent' in sms:
                sms_sended_expected += sms['sms_sent']

        mock_check_output.side_effect = executions

        sms_cli = FakeSMSCMDDaemon(sms_received=self.sms_received)
        sms_cli.time = 0.2
        sms_cli.send_sms = MagicMock(return_value=None)

        sms_cli.run()

        ok_(sms_cli.send_sms.call_args_list == sms_sended_expected)


class SMSIntegrationRunCMDTests(SMSIntegrationBaseMDTests):

    def test_should_sendSMS_whenReceiveSMS(self):
        sms_sended_expected = []

        for sms in self.sms_received:
            if 'sms_sent' in sms:
                sms_sended_expected += sms['sms_sent']

        sms_cli = FakeSMSCMDDaemon(sms_received=self.sms_received)
        sms_cli.time = 0.2
        sms_cli.send_sms = MagicMock(return_value=None)

        sms_cli.run()

        ok_(sms_cli.send_sms.call_args_list == sms_sended_expected)


class TestCommandOK(SMSIntegrationSimulateCMDTests):
    sms_received = [{'id': 1, 'number': '+34666666666', 'content': 'reboot_computer',
                     'execution': b'', 'sms_sent':
                         [call('+34666666666', 'Rebooting computer: systemctl reboot')]
                     }]


class TestExecuteCommandOK(SMSIntegrationRunCMDTests):
    sms_received = [{'id': 1, 'number': '+34666666666', 'content': 'exec echo "hola"',
                    'sms_sent': [call('+34666666666', 'Executing command: echo "hola"'),
                                 call('+34666666666', 'Command executed: hola\n')]
                     }]


class TestExecuteCommandKO(SMSIntegrationRunCMDTests):
    sms_received = [{'id': 2, 'number': '+34666666666', 'content': 'exec echo "hola"; exit 1',
                     'execution': 'Hola', 'sms_sent':
                         [call('+34666666666', 'Executing command: echo "hola"; exit 1'),
                          call('+34666666666', 'ERROR: None | CMD: echo "hola"; exit 1 | RC: 1')]
                     }]


class TestExecuteCommandNotExists(SMSIntegrationRunCMDTests):
    sms_received = [{'id': 3, 'number': '+34666666666', 'content': 'exec lsaa',
                     'execution': 'Hola', 'sms_sent':
                         [call('+34666666666', 'Executing command: lsaa'),
                          call('+34666666666', 'ERROR: None | CMD: lsaa | RC: 127')]
                     }]


class TestUnathorizedNumber(SMSIntegrationRunCMDTests):
    sms_received = [{'id': 4, 'number': '+34666666667', 'content': 'restart_current_meter',
                     'sms_sent':
                         [call('+34666666666', 'Unauthorized phone number +34666666667')]
                     }]


class TestUnrecognizedCommand(SMSIntegrationRunCMDTests):
    sms_received = [{'id': 5, 'number': '+34666666666', 'content': 'connect_vpn',
                     'sms_sent':
                         [call('+34666666666', 'Unrecognized command connect_vpn sent from +34666666666')]
                     }]


class TestAllSMSRunCMD(SMSIntegrationRunCMDTests):
    sms_received = [{'id': 1, 'number': '+34666666666', 'content': 'exec echo "hola"',
                    'sms_sent': [call('+34666666666', 'Executing command: echo "hola"'),
                                 call('+34666666666', 'Command executed: hola\n')]
                     },
                    {'id': 2, 'number': '+34666666666', 'content': 'exec echo "hola"; exit 1',
                     'execution': 'Hola', 'sms_sent':
                         [call('+34666666666', 'Executing command: echo "hola"; exit 1'),
                          call('+34666666666', 'ERROR: None | CMD: echo "hola"; exit 1 | RC: 1')]
                     },
                    {'id': 3, 'number': '+34666666666', 'content': 'exec lsaa',
                     'execution': 'Hola', 'sms_sent':
                         [call('+34666666666', 'Executing command: lsaa'),
                          call('+34666666666', 'ERROR: None | CMD: lsaa | RC: 127')]
                     },
                    {'id': 4, 'number': '+34666666667', 'content': 'restart_currentmeter',
                     'sms_sent':
                         [call('+34666666666', 'Unauthorized phone number +34666666667')]
                     },
                    {'id': 5, 'number': '+34666666666', 'content': 'connect_vpn',
                     'sms_sent':
                         [call('+34666666666', 'Unrecognized command connect_vpn sent from +34666666666')]
                     }
                    ]


class TestSMSCli(unittest.TestCase):

    def test_should_returnTrue_when_isAuthorizedPhoneNumber(self):

        sms_cli = FakeSMSCMDDaemon()
        authorized_phones = ['+34666666666', '5087']
        for phone in authorized_phones:
            ok_(sms_cli.check_authorized_phone(phone))

    def test_should_throwUnauthorizedPhoneNumberException_when_isUnauthorizedPhoneNumber(self):
        sms_cli = FakeSMSCMDDaemon()
        no_authorized_phones = ['+34666666667', '3217']

        for phone in no_authorized_phones:
            self.assertRaises(UnauthorizedPhoneNumberException, sms_cli.check_authorized_phone, phone)

    def test_shuold_returnCommand_when_validKey(self):
        sms_cli = FakeSMSCMDDaemon()
        config = load_config(path_config=config_file)

        for k, v in config['commands'].items():
            eq_(sms_cli.get_command(k), v)

    def test_shuold_throwUnrecognizedCommandException_when_invalidKey(self):
        sms_cli = FakeSMSCMDDaemon()

        for k in ['no_key', 'reboot_ra']:
            self.assertRaises(UnrecognizedCommandException, sms_cli.get_command, k)

    def test_should_returnTrue_when_commandNeedCofirmMessage(self):
        config = load_config(path_config=config_file)
        for cmd in ['reboot_computer']:
            cmd = config['commands'][cmd]
            ok_(not SMSCMDDaemon.need_confirm(cmd))

        for cmd in ['exec', 'restart_current_meter', 'update_dns']:
            cmd = config['commands'][cmd]
            ok_(SMSCMDDaemon.need_confirm(cmd))

    def test_should_returnCustomCmd_when_sendSMSwithExecCmd(self):
        sms_cli = FakeSMSCMDDaemon()
        cli_expected = 'ls -la /var/log/buoy'
        content = 'exec ' + cli_expected
        cmd = sms_cli.get_command(content)

        ok_(cmd['cli'] == cli_expected)

    def test_should_substituteVarsInMessage_when_commandStartedMsgHasVars(self):
        sms_cli = FakeSMSCMDDaemon()
        sms_cli.send_sms = MagicMock(return_value=None)
        sms = {'id': 1,
               'number': '+34660045151',
               'content': 'reboot_computer',
               'command': {
                   'msg': {
                       'started': 'Rebooting modem: {command_cli}',
                       'finished': 'Modem rebooted: {ouput}',
                       'error': 'Error rebooting modem'
                   },
                   'cli': 'zte_reboot'
               }
               }
        sms_flat = sms_cli.flatten(sms)

        msg_expected = sms['command']['msg']['started'].format(**sms_flat)

        sms_cli.send_confirm_started(sms)
        ok_(sms_cli.send_sms.call_args == ((sms['number'], msg_expected), ))

    def test_should_substituteVarsInMessage_when_commandFinishedMsgHasVars(self):
        sms_cli = FakeSMSCMDDaemon()
        sms_cli.send_sms = MagicMock(return_value=None)
        output = "127.0.0.1"
        sms = {'id': 1,
               'number': '+34660045151',
               'content': 'reboot_computer',
               'command': {
                   'msg': {
                       'started': 'Getting public IP',
                       'finished': 'Public IP: {command_output}',
                       'error': 'Error getting public IP'
                   },
                   'cli': 'zte_reboot',
                   'output': output

               }
               }

        sms_flat = sms_cli.flatten(sms)
        msg_expected = sms['command']['msg']['finished'].format(**sms_flat)

        sms_cli.send_confirm_endend(sms)
        ok_(sms_cli.send_sms.call_args == ((sms['number'], msg_expected), ))


if __name__ == '__main__':
    unittest.main()
