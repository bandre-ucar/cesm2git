#!/usr/bin/env python
"""create "shallow" git clones of cesm by pulling in specified svn
branch tags.

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

import argparse
import json
import os
import shutil
import subprocess
import traceback
import xml.etree.ElementTree as etree
import xml.dom.minidom as minidom

if sys.version_info[0] == 2:
    from ConfigParser import SafeConfigParser as config_parser
else:
    from configparser import ConfigParser as config_parser


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

    parser.add_argument('--authors', nargs=1, default=['author-map.json'],
                        help='path to authors json file')

    parser.add_argument('--backtrace', action='store_true',
                        help='show exception backtraces as extra debugging '
                        'output')

    parser.add_argument('--debug', action='store_true',
                        help='extra debugging output')

    parser.add_argument('--config', nargs=1, required=True,
                        help='path to config file')

    parser.add_argument('--repo', nargs=1, default=['clm-experimental'],
                        help='path to rtm git repo, relative to cwd.')

    parser.add_argument('--feelin-lucky', action='store_true', default=False,
                        help='push update back to the master repo')

    options = parser.parse_args()
    return options


def read_config_file(filename):
    """The configuration file contains information about which cesm tag to
    check out and which svn externals need to be changed:

    [cesm]
    repo = https://svn-ccsm-models.cgd.ucar.edu
    piorepo = https://parallelio.googlecode.com
    tag = cesm1/alphas/tags/cesm1_3_alpha13b

    [externals]
    scripts = scripts/trunk_tags/scripts4_140915
    models/ocn/pop2  = pop2/trunk_tags/cesm_pop_2_1_20140828



    NOTE: the options in the external sections are exactly the
    directory paths used in SVN_EXTERNAL_DIRECTORIES, the values are
    the url minus the repo prefix.

    FIXME(bja, 201410) This assumes we won't want to update an
    external that isn't stored in svn. Probably a bad assumption.

    """
    print("Reading configuration file : {0}".format(filename))

    cfg_file = os.path.abspath(filename)
    if not os.path.isfile(cfg_file):
        raise RuntimeError("Could not find config file: {0}".format(cfg_file))

    config = config_parser()
    config.read(cfg_file)

    repo_config = {}

    def _check_for_required_section(conf, section):
        if not conf.has_section(section):
            raise RuntimeError("ERROR: repo config file must contain a "
                               "'{0}' section".format(section))

    def _get_section_required_option(conf, section, option, upper_case=False):
        sect = list_to_dict(conf.items(section))
        if option not in sect and option.upper() not in sect:
            raise RuntimeError("ERROR: repo config section '{0}' must contain"
                               "a '{1}' keyword.".format(section, option))

        opt = {option: sect[option]}
        if upper_case is True:
            opt = {option.upper(): sect[option]}

        return opt

    section = "git"
    repo_config[section] = {}
    _check_for_required_section(config, section)
    keys = ["branch", ]
    for k in keys:
        repo_config[section].update(
            _get_section_required_option(
                config, section, k))

    section = "cesm"
    repo_config[section] = {}
    _check_for_required_section(config, section)
    for k in config.items(section):
        key = k[0]
        repo_config[section].update(
            _get_section_required_option(
                config,
                section,
                key))

    section = "externals"
    repo_config[section] = {}
    if config.has_section(section):
        repo_config[section].update(list_to_dict(config.items(section)))

    return repo_config


# -------------------------------------------------------------------------------
#
# misc work functions
#
# -------------------------------------------------------------------------------
def list_to_dict(input_list, upper_case=False):
    output_dict = {}
    for item in input_list:
        key = item[0]
        value = item[1]
        if upper_case is True:
            key = key.upper()
        output_dict[key] = value
    return output_dict


def string_to_bool(bool_string):
    """Convert a boolean string to a boolean value
    """
    value = None
    if bool_string.lower() == 'false':
        value = False
    elif bool_string.lower() == 'true':
        value = True
    else:
        raise RuntimeError("Invalid string for boolean conversion "
                           "'{0}'".format(bool_string))
    return value


def new_tag_from_config(config):
    """Generate a meaningful, if very verbose tag name from the specified
    cesm tag and externals

    """
    new_tag = config["cesm"]["tag"].split('/')[-1]
    for ext in config["externals"]:
        tag = config["externals"][ext].split('/')[-1]
        new_tag += "-{0}".format(tag)

    print("Creating new tag: {0}".format(new_tag))
    return new_tag


def remove_current_working_copy(cesm_config):
    """Removes the current working copy of cesm so that svn checkout will work.

    NOTE(bja, 2016, 2017): if the list of files in the root directory
    changes from the hard coded list below, then svn co will have
    problems with an error like:

        svn co https://svn-ccsm-models.cgd.ucar.edu/clm2/trunk_tags/clm4_5_12_r197 .
        Tree conflict on 'parse_cime.cs.status'
           > local file unversioned, incoming file add upon update

    The hard coded lists of files and directories can be replaced with
    something like:

        preserve_list = [".gitignore", ".git", ".github", ]
        dir_listing = os.listdir(os.getcwd())
        for item in dir_listing:
            if item not in preserve_list:
                if os.path.isfile(item):
                    os.remove(item)
                elif os.path.isdir(item):
                    shutil.rmtree(item)

    The above is dangerous and comes with its own set of problems. For
    example if something is added to the repo from the git side and
    not updated by svn, it won't be updated and removal won't be
    flagged! But this is only suppose to be used on branches that
    exactly track the svn repo w/o modification. So in principle it
    shouldn't be an issue....

    """
    suffix = "standalone"
    if "shift_root_suffix" in cesm_config:
        suffix = cesm_config["shift_root_suffix"]

    rm_files = [
        "ChangeLog",
        ".ChangeLog_template",
        "ChangeSum",
        "KnownBugs",
        ".CLMTrunkChecklist",
        "UpDateChangeLog.pl",
        "README",
        "README_cime",
        "README_EXTERNALS",
        "SVN_EXTERNAL_DIRECTORIES",
        "ExpectedTestFails.xml",
        "parse_cime.cs.status",
        "Copyright",
        "COPYRIGHT",
        "README.DGVM",
        "Quickstart.GUIDE",
        "Quickstart.userdatasets",
        "PTCLM.py",
        "PTCLMmkdata",
        "PTCLMsublist",
        "PTCLMsublist_prog.py",
        "batchque.py",
        "buildtools",
        "testcases.csh",
    ]

    for f in rm_files:
        if os.path.exists(f):
            os.remove(f)

        shift_file = "{0}.{1}".format(f, suffix)
        if os.path.exists(shift_file):
            os.remove(shift_file)

    rm_dirs = [
        "components",
        "models",
        "cime",
        "doc",
        "bld",
        "src",
        "src_clm40",
        "tools",
        "test",
        "cimetest",
        "cime_config",
        "cesmtest",
        "source_glc",
        "source_glc.latest",
        "source_glimmer",
        "source_glimmer-cism",
        "source_glimmer.latest",
        "source_slap",
        "drivers",
        "mpi",
        "input_templates",
        "PTCLM_sitedata",
        "mydatafiles",
        "test",
        "usr_files",

    ]

    for d in rm_dirs:
        if os.path.exists(d):
            shutil.rmtree(d)


# -------------------------------------------------------------------------------
#
# svn wrapper functions
#
# -------------------------------------------------------------------------------
def svn_checkout_cesm(cesm_config, debug):
    """Checkout the user specified cesm tag
    """
    print("Checking out cesm tag from svn...", end='')
    url = cesm_config['repo']
    cesm_tag = cesm_config['tag']
    tag = os.path.join(url, cesm_tag)
    if string_to_bool(cesm_config["collapse_standalone"]):
        tag = os.path.join(tag, cesm_config['standalone_path'])

    cmd = [
        "svn",
        "export",
        "--force",
        "--ignore-externals",
        "--ignore-keywords",
        tag,
        "."
    ]
    output = subprocess.STDOUT
    if debug:
        print("\n")
        print(" ".join(cmd))
        output = None
    try:
        subprocess.check_output(cmd, shell=False, stderr=output)
    except subprocess.CalledProcessError as error:
        print(error)
        print("    {0}".format(" ".join(cmd)))
        raise RuntimeError(error)

    if not debug:
        print(" done.")
    if string_to_bool(cesm_config['shift_root_files']):
        svn_shift_root_files(cesm_config)


def update_svn_externals(temp_repo_dir, repo_url, external_mods):
    """Backup the svn externals file, read it in and modify according to
    the user config, then write the new externals file.

    """
    print("Updating svn externals...", end='')
    externals_filename = "{0}/SVN_EXTERNAL_DIRECTORIES".format(temp_repo_dir)
    if not os.path.isfile(externals_filename):
        return

    shutil.copy2(externals_filename, "{0}.orig".format(externals_filename))

    new_externals = []
    with open(externals_filename, 'r') as externals_file:
        externals = externals_file.readlines()
    for line in externals:
        temp = line.split()
        if len(temp) == 2:
            ext = temp[0]
            for e in external_mods:
                if e.strip() == ext:
                    line = "{0}            {1}/{2}\n".format(
                        ext,
                        repo_url,
                        external_mods[e])
        new_externals.append(line)

    with open(externals_filename, 'w') as externals_file:
        for line in new_externals:
            externals_file.write(line)

    svn_set_new_externals()
    svn_update("components")
    print(" done.")


def svn_set_new_externals():
    """
    """
    cmd = [
        "svn",
        "propset",
        "svn:externals",
        "-F",
        "SVN_EXTERNAL_DIRECTORIES",
        ".",
    ]
    subprocess.check_output(cmd, shell=False, stderr=subprocess.STDOUT)


def svn_update(path):
    """
    """
    cmd = [
        "svn",
        "update",
        path,
    ]
    subprocess.check_output(cmd, shell=False, stderr=subprocess.STDOUT)


def svn_switch(temp_repo_dir, switch_dir, url, tag):
    """run svn switch to update an external to a different tag

    FIXME(bja, 20141008): this means the SVN_EXTERNAL_DIRECTORIES are
    wrong. Need to update the externals file then update so everything
    is in sync!

    """
    os.chdir("{0}/{1}".format(temp_repo_dir, switch_dir))
    cmd = [
        "svn",
        "switch",
        "{0}/{1}".format(url, tag),
    ]
    subprocess.check_output(cmd, shell=False, stderr=subprocess.STDOUT)
    os.chdir(temp_repo_dir)


def svn_log_info(cesm_config, author_map, debug):
    """Extract the svn commit info so we can use it in the git commit.

    """
    print("Extracting cesm tag info from svn...", end='')
    url = cesm_config['repo']
    cesm_tag = cesm_config['tag']
    cmd = [
        "svn",
        "log",
        "--limit", "1",
        "--xml",
        "{0}/{1}".format(url, cesm_tag),
    ]

    if debug:
        print("\n")
        print(" ".join(cmd))
        output = None
    output = subprocess.check_output(
        cmd, shell=False, stderr=subprocess.STDOUT)

    if not debug:
        print(" done.")

    # print(output)
    log_info = {}
    xml = etree.fromstring(output)
    # print(xml)
    author = xml.findall('logentry/author')[0].text

    # setup a sane default based on svn user info
    if '@' in author:
        name = author.split('@')[0]
        email = author
    else:
        name = author
        email = '{0}@ucar.edu'.format(author)

    # try to find real name from our map file
    if name in author_map:
        # NOTE(bja, 2017-11) must set name last because overwritting
        # name will cause a key error!
        email = author_map[name]['email']
        name = author_map[name]['name']

    author = '{0} <{1}>'.format(name, email)
    log_info['author'] = author

    log_info['date'] = xml.findall('logentry/date')[0].text
    log_info['msg'] = xml.findall('logentry/msg')[0].text
    # print(log_info)
    return log_info


def svn_list_root_files(cesm_config):
    """
    """
    url = cesm_config['repo']
    cesm_tag = cesm_config['tag']
    cmd = [
        "svn",
        "list",
        "{0}/{1}".format(url, cesm_tag)
    ]
    output = subprocess.check_output(cmd, shell=False,
                                     stderr=subprocess.STDOUT)
    return output


def svn_shift_root_files(cesm_config):
    """The main checkout shifted the standalone checkout contents back to
    the root of the repo directory. To preserve all information
    associated with a tag we need to grab the files from the
    standalone root, e.g. top level externals.

    Note that the finest level of granularity that svn checkout works
    on is the directory level. Inorder to grab single files, we need
    to export (or jump through hoops doing an empty checkout + update
    single files. But since we already have a checkout of the main
    model/component dir, export is simpler and avoids confusing svn.)

    """
    root_files = svn_list_root_files(cesm_config).split()
    existing_files = os.listdir('.')

    url = cesm_config['repo']
    cesm_tag = cesm_config['tag']
    tag = os.path.join(url, cesm_tag)

    for root_file in root_files:
        if "trunk" in root_file:
            # one-off mistake in clm4_5_32 that we need to skip to have
            # everything run automatically
            continue
        if root_file in cesm_config["standalone_path"]:
            # 'models' and 'components' directories are returned by svn
            # list, but we want to skip them.
            continue
        if root_file in ['ChangeLog', 'ChangeSum']:
            # don't copy changelog because it is in doc !
            continue
        # by default we just use the same filename
        destination = root_file
        if destination == "SVN_EXTERNAL_DIRECTORIES":
            # always want standalone externals renamed with suffix.
            destination = "{0}.{1}".format(root_file,
                                           cesm_config["shift_root_suffix"])
        if destination in existing_files:
            # any other duplicate files get renamed
            destination = "{0}.{1}".format(root_file,
                                           cesm_config["shift_root_suffix"])
        checkout_path = os.path.join(tag, root_file)
        cmd = [
            "svn",
            "export",
            checkout_path,
            destination,
        ]
        subprocess.check_output(cmd, shell=False,
                                stderr=subprocess.STDOUT)


# -------------------------------------------------------------------------------
#
# git wrapper functions
#
# -------------------------------------------------------------------------------
def clone_cesm_git(repo_dir, temp_repo_dir):
    """Clone the existing git repo.

    NOTE: assumes a fixed directory structure. If this script is
    executed from directory 'work', then work/ed-clm-git is the main git
    repo to pull new src into.

    """
    print("Cloning git repo at : {0}".format(repo_dir))
    cmd = [
        "git",
        "clone",
        repo_dir,
        temp_repo_dir,
    ]
    subprocess.check_output(cmd, shell=False, stderr=subprocess.STDOUT)


def switch_git_branch(branch):
    """All cesm changes from upstream svn are pulled onto the git 'trunk' branch
    """
    cmd = [
        "git",
        "checkout",
        branch,
    ]
    subprocess.check_output(cmd, shell=False, stderr=subprocess.STDOUT)


def find_git_externals(temp_repo_dir):
    """search the svn externals file for any git externals that will be
    updated with subtrees.

    """
    print("finding git based externals....")
    externals_filename = "{0}/SVN_EXTERNAL_DIRECTORIES".format(temp_repo_dir)
    externals = []
    git_externals = []
    if not os.path.isfile(externals_filename):
        return git_externals

    with open(externals_filename, 'r') as externals_file:
        externals = externals_file.readlines()

    for e in externals:
        if 'gen_domain' in e:
            # clm insists in pulling in part of cime into it's own
            # dir. don't try to put that into a subtree.
            continue
        ext = e.split()
        if len(ext) < 2:
            continue
        ext_dir = ext[0]
        url = ext[1]
        # FIXME(bja, 2017-04) just move git check up here!
        if 'svn' in url:
            continue
        # doesn't work if extracting a subdir of a tag, needs to be -2.
        # Count from the beginning of the array to void the special case...
        # ext_commit = url.split('/')[-1]
        ext_commit = url.split('/')[6]
        ext_url = '/'.join(url.split('/')[0:5])
        if ext_url.find('git') > 0:
            git_ext = {}
            git_ext['ext_dir'] = ext_dir
            git_ext['ext_url'] = ext_url
            git_ext['ext_commit'] = ext_commit
            git_externals.append(git_ext)

    return git_externals


def git_update_subtree(git_externals):
    """update any git subtree to the correct version.

    """
    print("Updating git subtrees....")
    print(git_externals)
    for e in git_externals:
        cmd = [
            'git',
            'subtree',
            'pull',
            '--squash',
            '--prefix',
            e['ext_dir'],
            e['ext_url'],
            e['ext_commit'],
        ]
        print("    {0}".format(' '.join(cmd)))
        try:
            subprocess.check_call(cmd, shell=False, stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError:
                git_remove_add_subtree(cmd, e['ext_dir'])


def git_remove_add_subtree(subtree_cmd, ext_dir):
    """When a subtree can't be updated because of a git error, it seems
    like the only path forward is remove it and readd it. so try
    that...

    """
    cmd = ['git',
           'rm',
           '-r',
           ext_dir,
           ]
    print("    {0}".format(' '.join(cmd)))
    commit_removal = False
    try:
        subprocess.check_call(cmd, shell=False, stderr=subprocess.STDOUT)
        commit_removal = True
    except subprocess.CalledProcessError as e:
        # error 128 seems to be the return code for non-existant
        # file. It's ok if it doesn't exist.
        if e.returncode != 128:
            raise e

    if commit_removal:
        cmd = ['git',
               'commit',
               '-m',
               'manually remove "{0}" subtree that can not be updated'.format(
                   ext_dir),
        ]
        print("    {0}".format(' '.join(cmd)))
        subprocess.check_call(cmd, shell=False, stderr=subprocess.STDOUT)

    # NOTE(bja, 201609) directory won't be empty because of the hidden
    # .svn directory. need to use shutil.rmtree instead of os.rmdir.
    print("    removing remants of {0} directory.".format(ext_dir))
    shutil.rmtree(ext_dir, ignore_errors=True)

    subtree_cmd[2] = 'add'
    print("    {0}".format(' '.join(subtree_cmd)))
    try:
        subprocess.check_call(subtree_cmd, shell=False,
                              stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as error:
        print("subtree error :\n{0}".format(error))
        raise RuntimeError(error)


def git_add_new_cesm(new_tag, git_externals, log_info):
    """Add the new cesm files to git
    """
    print("Removing git_externals changes from delta.")
    for ext in git_externals:
        # reset any changed files
        cmd = [
            'git',
            'checkout',
            '--',
            ext['ext_dir'],
        ]
        subprocess.check_output(cmd, shell=False, stderr=subprocess.STDOUT)
        # remove any added files
        cmd = [
            'git',
            'clean',
            '-d',
            '-f',
            ext['ext_dir'],
        ]
        subprocess.check_output(cmd, shell=False, stderr=subprocess.STDOUT)

    print("Committing new cesm to git")
    cmd = [
        "git",
        "add",
        "--all",
    ]
    subprocess.check_output(cmd, shell=False, stderr=subprocess.STDOUT)

    tmp_filename = 'svn-msg.tmp'
    with open(tmp_filename, 'w') as msg:
        msg.write('{0}\n\n'.format(new_tag))
        if log_info['msg']:
            msg.write("{0}\n".format(log_info['msg']))

    cmd = [
        "git",
        "commit",
        "--author='{0}'".format(log_info['author']),
        "--date='{0}'".format(log_info['date']),
        "-F", tmp_filename,
    ]
    if True:
        print(" ".join(cmd))
    subprocess.check_output(cmd, shell=False, stderr=subprocess.STDOUT)
    os.remove(tmp_filename)

    cmd = [
        "git",
        "tag", "--annotate",
        "-m", "tag {0} from svn".format(new_tag),
        new_tag
    ]
    if True:
        print(" ".join(cmd))
    subprocess.check_output(cmd, shell=False, stderr=subprocess.STDOUT)


def git_status():
    """run the git status command
    """
    print("Running git status")
    cmd = [
        "git",
        "status",
    ]
    subprocess.check_output(cmd, shell=False, stderr=subprocess.STDOUT)


def push_to_origin_and_cleanup(branch, new_dir, temp_repo_dir):
    """
    """
    print("Pushing changes to git origin and removing update directory...")
    cmd = [
        "git",
        "push",
        "--tags",
        "origin",
        branch,
    ]
    subprocess.check_output(cmd, shell=False, stderr=subprocess.STDOUT)
    os.chdir(new_dir)
    shutil.rmtree(temp_repo_dir)


def convert_externals_to_model_definition_xml(
        externals_filename, model_filename):
    """
    """
    print("Converting externals to model definition xml : {0} : {1}".format(
        externals_filename, model_filename))
    externals_list = []
    try:
        with open(externals_filename, 'r') as externals_file:
            for e in externals_file:
                externals_list.append(e)
    except IOError as e:
        return

    externals = {}
    for e in externals_list:
        # check for blank lines and comments
        e = e.strip()
        if e:
            if e[0] == '#':
                e = ''
        if not e:
            break

        tree_path, url = e.split()
        _, name = os.path.split(tree_path)
        externals[name] = {}
        externals[name]["tree_path"] = tree_path
        externals[name]["repo"] = {}
        if "svn" in url:
            externals[name]["repo"]["protocol"] = "svn"
            url_split = url.split('/')
            root = "/".join(url_split[0:4])
            tag = "/".join(url_split[4:])
            externals[name]["repo"]["root"] = root
            externals[name]["repo"]["tag"] = tag
        elif "git" in url:
            externals[name]["repo"]["protocol"] = "git"
            if "http" in url:
                url_split = url.split('/')
                root = "/".join(url_split[0:5])
                tag = "/".join(url_split[5:])
            elif "git@" in url:
                url_split = url.split('/')
                tag = '/'.join(url_split[-2:])
                root = '/'.join(url_split[0:-2])
            externals[name]["repo"]["root"] = root
            externals[name]["repo"]["tag"] = tag
        else:
            raise RuntimeError("unknown repo type {0} : {1}".format(name, url))

    # pp.pprint(externals)

    doc = minidom.Document()
    doc.appendChild(doc.createComment(" Automatically converted from "
                                      "{0} ".format(externals_filename)))
    source_tree = doc.createElement("config_sourcetree")
    source_tree.setAttribute("version", "1.0.0")
    for e in externals:
        source = doc.createElement("source")
        source.setAttribute("name", e)

        tree_path = doc.createElement("tree_path")
        text = doc.createTextNode(externals[e]["tree_path"])
        tree_path.appendChild(text)
        source.appendChild(tree_path)

        repo = doc.createElement('repo')
        repo.setAttribute('protocol', externals[e]['repo']['protocol'])

        root = doc.createElement("root")
        text = doc.createTextNode(externals[e]['repo']['root'])
        root.appendChild(text)
        repo.appendChild(root)

        tag = doc.createElement('tag')
        text = doc.createTextNode(externals[e]['repo']['tag'])
        tag.appendChild(text)
        repo.appendChild(tag)

        source.appendChild(repo)
        source_tree.appendChild(source)
    doc.appendChild(source_tree)
    xml = doc.toprettyxml(indent='    ')
    # pp.pprint(xml)
    with open(model_filename, 'w') as xml_file:
        xml_file.write(xml)


# -------------------------------------------------------------------------------
#
# main
#
# -------------------------------------------------------------------------------
def main(options):

    config = read_config_file(options.config[0])
    new_tag = new_tag_from_config(config)

    # NOTE: just assume git is available in the path!
    cwd = os.getcwd()

    repo_dir = os.path.abspath("{0}/{1}".format(cwd, options.repo[0]))

    temp_repo_dir = "{0}/{1}-update-{2}".format(cwd, options.repo[0], new_tag)
    if os.path.isdir(temp_repo_dir):
        raise RuntimeError("ERROR: temporary git repo dir already exists:\n"
                           "{0}".format(temp_repo_dir))

    clone_cesm_git(repo_dir, temp_repo_dir)
    os.chdir(temp_repo_dir)
    switch_git_branch(config["git"]["branch"])
    remove_current_working_copy(config["cesm"])

    svn_checkout_cesm(config['cesm'], debug=options.debug)
    authors_path = os.path.join(repo_dir, options.authors[0])
    with open(authors_path, 'r') as author_file:
        author_map = json.load(author_file)
    svn_log = svn_log_info(config['cesm'], author_map, debug=options.debug)
    git_externals = []
    if string_to_bool(config['cesm']['checkout_externals']):
        update_svn_externals(
            temp_repo_dir,
            config['cesm']['repo'],
            config['externals'])

        git_externals = find_git_externals(temp_repo_dir)

    if string_to_bool(config['cesm']['generate_model_description']):
        file_list = [
            ("SVN_EXTERNAL_DIRECTORIES.standalone", "CLM.standalone.xml"),
            ("SVN_EXTERNAL_DIRECTORIES", "CLM.xml"),
        ]
        for group in file_list:
            convert_externals_to_model_definition_xml(group[0], group[1])

    git_add_new_cesm(new_tag, git_externals, svn_log)
    git_update_subtree(git_externals)

    if (options.feelin_lucky):
        push_to_origin_and_cleanup(config["git"]["branch"], cwd, temp_repo_dir)

    print("Finished updating cesm to git.")
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
