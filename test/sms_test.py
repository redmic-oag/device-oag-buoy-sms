import unittest
from unittest.mock import patch, MagicMock

from nose.tools import eq_, ok_

from buoy.sms.sms_cli import SMSCliDaemon, UnrecognizedCommandException, UnauthorizedPhoneNumberException
from buoy.lib.utils.config import load_config

config_file = "test/config/sms.yaml"


class FakeSMSCliDaemon(SMSCliDaemon):
    def __init__(self, **kwargs):
        self.sms_received = kwargs.pop('sms_received', [])
        self.alerts_phones = kwargs.pop('alerts_phones', ['+34666666666', '+34666666667'])
        self.active = True
        self.num_iteration = len(self.sms_received)

    def get_sms_unread(self):
        return self.sms_received

    def delete_sms(self, sms_id):
        self.num_iteration -= 1
        if self.num_iteration:
            self.active = False


class TestSMSCli(unittest.TestCase):

    def setUp(self):
        self.sms_config = load_config(path_config=config_file)
        self.authorized_phones = ['+34666666666', '5087']
        self.no_authorized_phones = ['+34666666667', '3217']
        self.sms_received = [{'id': 1, 'number': '+34660045151', 'content': 'reboot_computer'},
                             {'id': 2, 'number': '+34660045151', 'content': 'connect_vpn'},
                             {'id': 3, 'number': '+34660045213', 'content': 'connect_vpn',
                              'exception': UnauthorizedPhoneNumberException},
                             {'id': 4, 'number': '+34660045151', 'content': 'connect_vpn22',
                              'exception': UnrecognizedCommandException}
                             ]

    def test_should_returnTrue_when_isAuthorizedPhoneNumber(self):

        sms_cli = FakeSMSCliDaemon()
        sms_cli.authorized_phones = self.authorized_phones

        for phone in self.authorized_phones:
            ok_(sms_cli.is_authorized_phone(phone))

    def test_should_throwUnauthorizedPhoneNumberException_when_isUnauthorizedPhoneNumber(self):
        sms_cli = FakeSMSCliDaemon()
        sms_cli.authorized_phones = self.authorized_phones

        for phone in self.no_authorized_phones:
            self.assertRaises(UnauthorizedPhoneNumberException, sms_cli.is_authorized_phone, phone)

    def test_shuold_returnCommand_when_validKey(self):
        sms_cli = FakeSMSCliDaemon()
        sms_cli.commands = self.sms_config['commands']

        for k, v in self.sms_config['commands'].items():
            eq_(sms_cli.get_command(k), v)

    def test_shuold_throwUnrecognizedCommandException_when_invalidKey(self):
        sms_cli = FakeSMSCliDaemon()
        sms_cli.commands = self.sms_config['commands']

        for k in ['no_key', 'reboot_ra']:
            self.assertRaises(UnrecognizedCommandException, sms_cli.get_command, k)

    def test_should_returnTrue_when_commandNeedCofirmMessage(self):
        for cmd in ['reboot_computer']:
            cmd = self.sms_config['commands'][cmd]
            ok_(not SMSCliDaemon.need_confirm(cmd))

        for cmd in ['reboot_modem', 'connect_vpn', 'update_dns']:
            cmd = self.sms_config['commands'][cmd]
            ok_(SMSCliDaemon.need_confirm(cmd))

    def test_ad(self):
        sms_cli = FakeSMSCliDaemon()
        sms_cli.commands = self.sms_config['commands']
        cli_expected = 'ls -la /var/log/buoy'
        content = 'exec ' + cli_expected
        cmd = sms_cli.get_command(content)

        ok_(cmd['cli'] == cli_expected)

    def test_should_substituteVarsInMessage_when_commandStartedMsgHasVars(self):
        sms_cli = FakeSMSCliDaemon()
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
        sms_cli = FakeSMSCliDaemon()
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

    @unittest.skip("Necesario corregir")
    @patch('buoy.sms.sms_cli.check_call', return_value=0)
    def test_should_sendVarious_notifications_whenReceivedVariousSms(self, mock_check_call):
        sms_cli = FakeSMSCliDaemon(sms_received=self.sms_received)
        sms_cli.time = 0
        sms_cli.commands = self.sms_config['commands']
        sms_cli.authorized_phones = self.authorized_phones
        sms_cli.send_confirm_started = MagicMock(return_value=None)
        sms_cli.send_confirm_ended = MagicMock(return_value=None)
        sms_cli.send_error = MagicMock(return_value=None)

        call_confirm_started = []
        call_with_confirm_expected = []
        call_error_expected = []
        for sms in self.sms_received:
            number, content = sms['number'], sms['content']
            if 'exception' in sms:
                cls_exception = sms['exception']
                exception_expected = None
                if cls_exception is UnauthorizedPhoneNumberException:
                    exception_expected = UnauthorizedPhoneNumberException(phone=number)
                elif cls_exception is UnrecognizedCommandException:
                    exception_expected = UnrecognizedCommandException(command=content)

                    exception_expected.phone = number
                call_error_expected.append((exception_expected,))
            else:
                command = self.sms_config['commands'][content]
                call_confirm_started.append(((number, command),))

                if SMSCliDaemon.need_confirm(command):
                    call_with_confirm_expected.append(((number, command),))

        sms_cli.run()

        ok_(sms_cli.send_confirm_started.call_args_list == call_confirm_started)
        ok_(sms_cli.send_confirm_ended.call_args_list == call_with_confirm_expected)
        eq_(sms_cli.send_error.call_count, len(call_error_expected))


if __name__ == '__main__':
    unittest.main()
