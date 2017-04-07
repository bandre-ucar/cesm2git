#!/usr/bin/env python
"""FIXME: A nice python program to do something useful.

Author: Ben Andre <andre@ucar.edu>

"""

from __future__ import print_function

import sys

if sys.hexversion < 0x02070000:
    print(70 * "*")
    print("ERROR: {0} requires python >= 2.7.x. ".format(sys.argv[0]))
    print("It appears that you are running python {0}".format(
        ".".join(str(x) for x in sys.version_info[0:3])))
    print(70 * "*")
    sys.exit(1)

#
# built-in modules
#
import argparse
import os
import subprocess
import traceback

if sys.version_info[0] == 2:
    from ConfigParser import SafeConfigParser as config_parser
else:
    from configparser import ConfigParser as config_parser

#
# installed dependencies
#

#
# other modules in this package
#

# -------------------------------------------------------------------------------
#
# User input
#
# -------------------------------------------------------------------------------

def commandline_options():
    """Process the command line arguments.

    """
    parser = argparse.ArgumentParser(
        description='FIXME: python program template.')

    parser.add_argument('--backtrace', action='store_true',
                        help='show exception backtraces as extra debugging '
                        'output')

    parser.add_argument('--debug', action='store_true',
                        help='extra debugging output')

    parser.add_argument('--config', nargs=1, required=True,
                        help='path to config file')

    options = parser.parse_args()
    return options


# -------------------------------------------------------------------------------
#
# work functions
#
# -------------------------------------------------------------------------------
def read_config_file(filename):
    """Read the configuration file and process

    """
    print("Reading configuration file : {0}".format(filename))

    cfg_file = os.path.abspath(filename)
    if not os.path.isfile(cfg_file):
        raise RuntimeError("Could not find config file: {0}".format(cfg_file))

    config = config_parser()
    config.read(cfg_file)

    return config


def write_config_file(config, filename):
    """Read the configuration file and process

    """
    print("Writing configuration file : {0}".format(filename))

    cfg_file = os.path.abspath(filename)
    if not os.path.isfile(cfg_file):
        raise RuntimeError("Could not find config file: {0}".format(cfg_file))

    with open(cfg_file, 'w') as configfile:
        config.write(configfile)


# -------------------------------------------------------------------------------
#
# main
#
# -------------------------------------------------------------------------------

def main(options):
    tags = [
        'rtm1_0_02',
        'rtm1_0_03',
        'rtm1_0_04',
        'rtm1_0_05',
        'rtm1_0_06',
        'rtm1_0_07',
        'rtm1_0_08',
        'rtm1_0_09',
        'rtm1_0_10',
        'rtm1_0_11',
        'rtm1_0_12',
        'rtm1_0_13',
        'rtm1_0_14',
        'rtm1_0_15',
        'rtm1_0_16',
        'rtm1_0_17',
        'rtm1_0_18',
        'rtm1_0_19',
        'rtm1_0_20',
        'rtm1_0_21',
        'rtm1_0_22',
        'rtm1_0_23',
        'rtm1_0_24',
        'rtm1_0_25',
        'rtm1_0_26',
        'rtm1_0_27',
        'rtm1_0_28',
        'rtm1_0_29',
        'rtm1_0_30',
        'rtm1_0_31',
        'rtm1_0_32',
        'rtm1_0_33',
        'rtm1_0_34',
        'rtm1_0_35',
        'rtm1_0_36',
        'rtm1_0_37',
        'rtm1_0_38',
        'rtm1_0_39',
        'rtm1_0_40',
        'rtm1_0_41',
        'rtm1_0_42',
        'rtm1_0_43',
        'rtm1_0_44',
        'rtm1_0_45',
        'rtm1_0_46',
        'rtm1_0_47',
        'rtm1_0_48',
        'rtm1_0_49',
        'rtm1_0_50',
        'rtm1_0_51',
        'rtm1_0_52',
        'rtm1_0_53',
        'rtm1_0_54',
        'rtm1_0_55',
        'rtm1_0_56',
        'rtm1_0_57',
        'rtm1_0_58',
        'rtm1_0_59',
        'rtm1_0_60',
        'rtm1_0_61',
    ]

    config_filename = options.config[0]
    for t in tags:
        config = read_config_file(config_filename)

        tag = "rivrtm/trunk_tags/{0}".format(t)
        config.set('cesm', 'tag', tag)

        write_config_file(config, config_filename)

        cmd = ['./rtm/cesm2git.py',
               '--config',
               config_filename,
               '--feelin-lucky',
               ]
        print(tag)
        subprocess.check_output(cmd, shell=False, stderr=subprocess.STDOUT)

    return 0


if __name__ == "__main__":
    options = commandline_options()
    try:
        status = main(options)
        sys.exit(status)
    except Exception as error:
        print(str(error))
        if options.backtrace:
            traceback.print_exc()
        sys.exit(1)
