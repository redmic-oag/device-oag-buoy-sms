# -*- coding: utf-8 -*-

import logging
from os import path

import yaml

logger = logging.getLogger(__name__)


def load_config(path_config):
    if not path.isfile(path_config):
        logger.error("No exists config file %s" % (path_config,))

    f = open(path_config, 'r')
    config = yaml.load(f)
    f.close()

    return config


def load_config_device(device_name, path_config='/etc/buoy/buoy.yaml'):
    config = load_config(path_config=path_config)

    return config['device'][device_name]


def load_config_device_serial(device_name, path_config='/etc/buoy/device.yaml'):
    config = load_config_device(device_name, path_config=path_config)

    return config['device'][device_name]['serial']


def load_config_logger(path_config='/etc/buoy/logging.yaml'):
    config = load_config(path_config=path_config)

    return config
