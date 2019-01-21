#!/usr/bin/env python3.6
# -*- coding: utf-8 -*- pyversions=3.6+

import logging.config
import time
from argparse import ArgumentParser

from buoy.lib.utils.argsparse import is_valid_file
import buoy.lib.utils.config as load_config
from buoy.lib.service.daemon import Daemon
from subprocess import DEVNULL, STDOUT, check_output, CalledProcessError
from flatten_dict import flatten

DAEMON_NAME = 'sms-cli'

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


class NotExistsCommandException(Exception):
    def __init__(self, command: str):
        SMSExceptionBase.__init__(self, message="Not exists command {command}")
        self.command = command


class SMSCliDaemon(Daemon):
    def __init__(self, config):
        Daemon.__init__(self,  daemon_name=DAEMON_NAME, daemon_config=config['service'])

        conf = config['service']
        self.time = conf['time']
        self.commands = config['commands']
        self.authorized_phones = set(config['phones']['authorized'])
        self.alerts_phones = set(config['phones']['alerts'])

    def run(self):
        while self.is_active:
            for sms in self.get_sms_unread():
                try:
                    logger.info("Phone %(number) - Content %(content)", sms)
                    if self.is_authorized_phone(sms['number']):
                        sms['command'] = self.get_command(sms['content'])
                        self.send_confirm_started(sms)
                        try:
                            sms['command']['output'] = check_output(sms['command']['cli'], stdout=DEVNULL,
                                                                    stderr=STDOUT).decode('UTF-8')
                        except CalledProcessError as ex:
                            raise NotExistsCommandException(sms['content'])

                        if self.need_confirm(sms['command']):
                            self.send_confirm_endend(sms)
                    else:
                        raise UnauthorizedPhoneNumberException(sms['number'])

                except SMSExceptionBase as ex:
                    ex.phone = sms['number']
                    self.send_error(ex)
                    pass
                self.delete_sms(sms['id'])

            time.sleep(self.time)

    def get_sms_unread(self):
        import vodem.simple
        try:
            return vodem.simple.sms_inbox_unread()
        except Exception as e:
            self.error()

    def is_authorized_phone(self, number):
        if number in self.authorized_phones:
            return True

    def get_command(self, content):
        preffix = "exec "
        if content in self.commands:
            cmd = self.commands[content]
        elif content.startswith(preffix):
            cmd = self.commands[preffix[:-1]]
            cmd['cli'] = content[len(preffix):]

        if cmd:
            return cmd

        raise UnrecognizedCommandException(command=content)

    def send_confirm_started(self, sms):
        sms_flat = self.flatten(sms)
        msg = sms['command']['msg']['started'].format(**sms_flat)
        logger.info("Run %s - %s", sms['number'], msg)
        self.send_sms(sms['number'], msg)

    def send_confirm_endend(self, sms):
        sms_flat = self.flatten(sms)
        msg = sms['command']['msg']['finished'].format(**sms_flat)
        logger.info("Run %s - %s", sms['number'], msg)
        self.send_sms(sms['number'], msg)

    def send_error(self, exception: SMSExceptionBase):
        for phone in self.alerts_phones:
            self.send_sms(phone, str(exception))

    @staticmethod
    def need_confirm(command):
        return 'finished' in command['msg']

    @staticmethod
    def delete_sms(sms_id):
        import vodem.simple
        logger.info("Delete SMS with id value %s", sms_id)
        vodem.simple.sms_delete(sms_id)

    @staticmethod
    def send_sms(phone, msg):
        import vodem.simple
        vodem.simple.sms_send(phone, msg)

    @staticmethod
    def flatten(d):
        def underscore_reducer(k1, k2):
            if k1 is None:
                return k2
            else:
                return k1 + "_" + k2

        return flatten(d, reducer=underscore_reducer)


def run(config: str, config_log_file: str):
    logging.config.dictConfig(load_config.load_config_logger(DAEMON_NAME, path_config=config_log_file))
    buoy_config = load_config.load_config(path_config=config)

    daemon = SMSCliDaemon(config=buoy_config)
    daemon.start()


def main():
    parser = ArgumentParser()
    parser.add_argument("--config-file", help="Ruta al fichero de configuración del servicio",
                        default='/etc/buoy/sms.yaml', type=is_valid_file)
    parser.add_argument("--config-log-file", help="Ruta al fichero de configuración de los logs",
                        default='/etc/buoy/logging.yaml', type=is_valid_file)
    args = parser.parse_args()

    run(config=args.config_file, config_log_file=args.config_log_file)


if __name__ == "__main__":
    main()
