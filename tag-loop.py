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
import json
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

    parser.add_argument('--dry-run', action='store_true', default=False,
                        help='dry run setting up changes, '
                        'but not calling external programs.')

    parser.add_argument('--repo', nargs=1, required=True,
                        help='path to repo')

    parser.add_argument('--resume', nargs=1, default=[''],
                        help='resume interrupted look at specified tag.')

    parser.add_argument('--tag-file', nargs=1, required=True,
                        help='path to text file containing tags '
                        'to be imported')

    options = parser.parse_args()
    return options


# -------------------------------------------------------------------------------
#
# work functions
#
# -------------------------------------------------------------------------------
def write_config_file(config, filename):
    """Read the configuration file and process

    """
    # print("Writing configuration file : {0}".format(filename))

    cfg_file = os.path.abspath(filename)
    with open(cfg_file, 'w') as configfile:
        config.write(configfile)


def get_tag_list(tag_filename):
    """read the list of tags to be converted.

    tag_file is a plain text in containing json
    """
    with open(tag_filename, 'r') as tag_file:
        tags = json.load(tag_file)

    return tags


# -------------------------------------------------------------------------------
#
# main
#
# -------------------------------------------------------------------------------
def main(options):
    # git repo that is being manipulated
    local_git_repo = options.repo[0]
    config_filename = os.path.join(local_git_repo, 'tmp.cfg')

    tag_file = os.path.join(local_git_repo, options.tag_file[0])
    tag_input = get_tag_list(tag_file)

    base_info = tag_input['config']
    # assume we are doing every tag in the tag file
    found_resume_tag = True
    resume = options.resume[0].strip()
    if resume:
        # user requested resuming in the middle of the tag file
        found_resume_tag = False
        print("Searching for tag {0}".format(resume))

    for tag in tag_input["tags"]:
        if found_resume_tag is False:
            # we looking to resume a tag
            # print("Comparing '{0}' : '{1}'".format(resume, tag["tag"]))
            if resume == tag["tag"]:
                # current tag is resume point
                found_resume_tag = True
            else:
                # skip this tag and keep looking
                continue

        if 'skip' in tag and tag['skip'] is True:
                # skip tag for some reason, e.g. bad svn tag
                continue
        print("Processing : {0}".format(tag["tag"]))
        # setup the config file
        config = config_parser()
        config.add_section('git')
        config.add_section('cesm')
        config.add_section('externals')

        # local git branch that new tags are added to
        config.set('git', 'branch', base_info['branch'])

        # configuration for this tag
        config.set('cesm', 'repo', base_info['repo'])
        tag_path = os.path.join(base_info["tag_directory"], tag["tag"])
        config.set('cesm', 'tag', tag_path)

        config.set('cesm', 'checkout_externals',
                   str(tag['checkout_externals']))
        config.set('cesm', 'collapse_standalone',
                   str(tag['collapse_standalone']))
        config.set('cesm', 'shift_root_files',
                   str(tag['shift_root_files']))
        value = str(False)
        if 'generate_externals_description' in tag:
            value = str(tag['generate_externals_description'])
        config.set('cesm', 'generate_externals_description', value)

        optional_keys = ['shift_root_suffix',
                         'standalone_path', ]
        for k in optional_keys:
            try:
                config.set('cesm', k, tag[k])
            except KeyError:
                config.set('cesm', k, str(None))

        write_config_file(config, config_filename)

        executable = os.path.join(local_git_repo, 'cesm2git.py')
        cmd = [executable,
               '--repo', local_git_repo,
               '--config', config_filename,
               '--feelin-lucky',
               ]

        if not options.dry_run:
            subprocess.check_output(cmd, shell=False,
                                    stderr=subprocess.STDOUT)
        else:
            print(tag_path)

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
