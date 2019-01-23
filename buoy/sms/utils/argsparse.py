# -*- coding: utf-8 -*-

import argparse
from os import path


def is_valid_file(filename):
    if not path.isfile(filename):
        raise argparse.ArgumentTypeError("{0} does not exist".format(filename))

    return filename


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config-file", help="Ruta al fichero de configuración del servicio",
                        default='/etc/buoy/buoy.yaml', type=is_valid_file)
    parser.add_argument("--config-log-file", help="Ruta al fichero de configuración de los logs",
                        default='/etc/buoy/logging.yaml', type=is_valid_file)
    return parser.parse_args()


def parse_args_sender():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config-file", help="Ruta al fichero de configuración del servicio",
                        default='/etc/buoy/server.yaml', type=is_valid_file)
    parser.add_argument("--config-log-file", help="Ruta al fichero de configuración de los logs",
                        default='/etc/buoy/logging.yaml', type=is_valid_file)

    return parser.parse_args()
