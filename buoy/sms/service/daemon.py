# -*- coding: utf-8 -*-

import logging
import signal
import sys
import time
from os import getpid, makedirs, remove, EX_OK, EX_OSERR
from os.path import isfile, exists, join

logger = logging.getLogger(__name__)


def get_config(device_name, buoy_config):
    serial_config = buoy_config['device'][device_name]['serial']
    mqtt_config = buoy_config['device'][device_name]['mqtt']
    db_config = buoy_config['database']
    service_config = buoy_config['service']

    return serial_config, mqtt_config, db_config, service_config


class DaemonException(Exception):
    pass


class PID(object):
    """
        Clase para la gestión del PID de un servicio utilizando un fichero
    """

    def __init__(self, **kwargs):
        daemon_config = kwargs.pop('daemon_config')
        self.daemon_name = kwargs.pop('daemon_name')
        self.path_pidfile = daemon_config['path_pidfile']
        self.pid = getpid()
        self.pid_file = join(self.path_pidfile, self.daemon_name + ".pid")
        self.create_path_pid_file()

    def create_path_pid_file(self):
        if not exists(self.path_pidfile):
            makedirs(self.path_pidfile)

    def create_pid_file(self):
        if isfile(self.pid_file):
            remove(self.pid_file)

        with open(self.pid_file, 'w') as f:
            f.write(str(self.pid))

    def remove_pid_file(self):
        if isfile(self.pid_file):
            remove(self.pid_file)


class Daemon(PID):
    """
        Clase base para la creación de un servicio linux
        Cuenta con un ciclo de vida:
            * before_start
            * start
            * run
            * before_stop
            * stop
    """

    def __init__(self, **kwargs) -> None:
        self.start_timeout = kwargs.pop('start_timeout', 0)
        super(Daemon, self).__init__(**kwargs)

        self._active = False

        signal.signal(signal.SIGINT, self.handler_signal)
        signal.signal(signal.SIGTERM, self.handler_signal)

    def handler_signal(self, signum, frame):
        """ Maneja la captura de señales de interrupción, poniendo el servicio en modo inactivo """
        self._active = False

    def _before_start(self):
        self._active = True
        self.create_pid_file()
        self.before_start()

    def before_start(self):
        """ Función que se ejecuta antes de iniciar el servicio """
        pass

    def is_active(self):
        return self._active

    def start(self):
        logger.info("Start service")

        self._before_start()
        time.sleep(self.start_timeout)
        try:
            self.run()
        except Exception as ex:
            self.error()

        self._stop()

    def run(self):
        """ Función donde implementar la lógica del servicio """
        pass

    def _before_stop(self):
        self.before_stop()

    def before_stop(self):
        """ Función que se ejecuta antes de parar el servicio """
        pass

    def _stop(self, code=EX_OK):
        if self.is_active():
            self._active = False
            self._before_stop()
            self.remove_pid_file()
            sys.exit(code)

    def stop(self):
        logger.info("Stop service")
        self._stop()

    def error(self):
        """ Función que se ejecuta cuando se produce un error """
        logger.error("Service exit status fail")
        self._stop(code=EX_OSERR)
