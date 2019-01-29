#!/usr/bin/env python3.6
# -*- coding: utf-8 -*- pyversions=3.6+

import logging.config
import time
from argparse import ArgumentParser
from subprocess import DEVNULL, STDOUT, check_output, CalledProcessError

from flatten_dict import flatten

import buoy.lib.utils.config as load_config
from buoy.lib.service.daemon import Daemon
from buoy.lib.utils.argsparse import is_valid_file
import sys

DAEMON_NAME = 'sms-cmd'

logger = logging.getLogger(__name__)


class SMSExceptionBase(Exception):
    def __init__(self, message: str, **kwargs):
        self.message = message
        self.phone = kwargs.pop('phone', None)

    def __str__(self):
        return self.message.format(**self.__dict__)


class UnrecognizedCommandException(SMSExceptionBase):
    def __init__(self, command: str):
        SMSExceptionBase.__init__(self, message="Unrecognized command {command} sent from {phone}")
        self.command = command


class UnauthorizedPhoneNumberException(SMSExceptionBase):
    def __init__(self, phone: str):
        SMSExceptionBase.__init__(self, message="Unauthorized phone number {phone}")
        self.phone = phone


class NotExistsCommandException(SMSExceptionBase):
    def __init__(self, command: str):
        SMSExceptionBase.__init__(self, message="Not exists command {command}")
        self.command = command


class NotExecutionCommand(SMSExceptionBase):
    def __init__(self, command: str, code):
        SMSExceptionBase.__init__(self, message="Error executed command - {command} - Return code: {code}")
        self.command = command
        self.code = code


class SMSCMDDaemon(Daemon):
    def __init__(self, config):
        Daemon.__init__(self, daemon_name=DAEMON_NAME, daemon_config=config['service'])

        conf = config['service']
        self.time = conf['time']
        self.commands = config['commands']
        self.authorized_phones = set(config['phones']['authorized'])
        self.alerts_phones = set(config['phones']['alerts'])
        self.preffix_custom_cmd = "exec "

    def run(self):
        while self.is_active():
            messages = self.get_sms_unread()
            for sms in messages:
                self.delete_sms(sms)
                try:
                    logger.info("Phone: " + sms['number'] + " - Content: " + sms['content'])
                    self.check_authorized_phone(sms['number'])
                    sms['command'] = self.get_command(sms['content'])
                    self.send_confirm_started(sms)
                    self.exectution_command(sms)
                    if self.need_confirm(sms['command']):
                        self.send_confirm_endend(sms)

                except SMSExceptionBase as ex:
                    ex.phone = sms['number']
                    self.send_error(ex)
                    pass
                except BaseException as ex:
                    logging.info(ex)
                    self.error()

            time.sleep(self.time)

    @staticmethod
    def exectution_command(sms):
        cmd = sms['command']['cli']
        active_shell = not isinstance(cmd, list)
        try:
            sms['command']['output'] = check_output(cmd, stderr=STDOUT, shell=active_shell).decode("utf-8")
        except CalledProcessError as ex:
            if ex.returncode == 127:
                raise NotExistsCommandException(sms['content'])
            else:
                raise NotExecutionCommand(sms['content'], code=ex.returncode)

    def get_sms_unread(self):
        import vodem.simple
        try:
            return vodem.simple.sms_inbox_unread()
        except Exception as e:
            self.error()

    def check_authorized_phone(self, number):
        if number in self.authorized_phones:
            return True

        raise UnauthorizedPhoneNumberException(number)

    def get_command(self, cmd_key):
        if cmd_key in self.commands:
            cmd = self.commands[cmd_key]
        elif cmd_key.startswith(self.preffix_custom_cmd):
            cmd = self.commands[self.preffix_custom_cmd[:-1]]
            cmd['cli'] = cmd_key[len(self.preffix_custom_cmd):]
        else:
            raise UnrecognizedCommandException(command=cmd_key)

        return cmd

    def send_confirm_started(self, sms):
        sms_flat = self.flatten(sms)
        msg = sms['command']['msg']['started'].format(**sms_flat)
        logger.info("Send confirmation started message '" + msg + "' to '" + sms['number'] + "'")
        self.send_sms(sms['number'], msg)

    def send_confirm_endend(self, sms):
        sms_flat = self.flatten(sms)
        msg = sms['command']['msg']['finished'].format(**sms_flat)
        logger.info("Send finished endend message '" + msg + "' to '" + sms['number'] + "'")
        self.send_sms(sms['number'], msg)

    def send_error(self, exception: SMSExceptionBase):
        for phone in self.alerts_phones:
            self.send_sms(phone, str(exception))

    @staticmethod
    def need_confirm(command):
        return 'finished' in command['msg']

    @staticmethod
    def send_sms(phone, msg):
        import vodem.simple
        vodem.simple.sms_send(phone, msg)

    @staticmethod
    def delete_sms(sms):
        import vodem.simple
        vodem.simple.sms_delete(sms['id'])
        logging.info("SMS deleted: " + sms['content'])

    @staticmethod
    def flatten(d):
        def underscore_reducer(k1, k2):
            if k1 is None:
                return k2
            else:
                return k1 + "_" + k2

        f = flatten(d, reducer=underscore_reducer)
        if isinstance(f['command_cli'], list):
            f['command_cli'] = " ".join(f['command_cli'])
        return f


def run(config: str, config_log_file: str):
    logging.config.dictConfig(load_config.load_config_logger(path_config=config_log_file))
    buoy_config = load_config.load_config(path_config=config)

    daemon = SMSCMDDaemon(config=buoy_config)
    daemon.start()


def main():
    parser = ArgumentParser()
    parser.add_argument("--config-file", help="Ruta al fichero de configuración del servicio",
                        default='/etc/buoy/sms.yaml', type=is_valid_file)
    parser.add_argument("--config-log-file", help="Ruta al fichero de configuración de los logs",
                        default='/etc/buoy/logging-sms.yaml', type=is_valid_file)
    args = parser.parse_args()

    run(config=args.config_file, config_log_file=args.config_log_file)


if __name__ == "__main__":
    main()
