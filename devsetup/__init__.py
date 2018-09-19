__all__ = ['package_list_translate', 'package_list_file_load',
           'package_install', 'package_is_installed', 'fedora_version_get', 'repo_rpm_urls_load',
           'gsettings_patch_apply', 'dbus_user_session_run', 'gnome_custom_keybindings_apply'
]

import sys
import os
import subprocess
import pwd

from .gsettings import gsettings_patch_apply
from .dbus import dbus_user_session_run
from .gnome_custom_keybindings import gnome_custom_keybindings_apply

machine_to_archs_in_repo = {
        'x86_64': ['x86_64', 'i686'],
}

def package_list_translate(pkgs, target_arch):
    # handle __ARCHS_IN_REPO_FOR_CPU__
    out = []
    archs = machine_to_archs_in_repo.get(target_arch, [target_arch])
    for i in pkgs:
        if i.endswith('.__ARCHS_IN_REPO_FOR_CPU__'):
            pkg = i[:-len('.__ARCHS_IN_REPO_FOR_CPU__')]
            for a in archs:
                out.append('%s.%s' % (pkg, a))
        else:
            out.append(i)
    pkgs = out
    return pkgs

def package_list_file_load(filename, target_arch):
    '''target_arch: uname().machine

    Input Format:
/usr/bin/vimx                        # vim with X11 clipboard support
nss-mdns.__ARCHS_IN_REPO_FOR_CPU__  # MDNS .local domain resolution
htop iotop nethogs'''

    with open(filename) as f:
        lines = f.readlines()

    # strip comments till end of line
    out = []
    for l in lines:
        in_quote = 0
        for (i, c) in enumerate(l):
            if in_quote:
                if c == "'":
                    in_quote = 0
            else:
                if c == "'":
                    in_quote = 1
                elif c == '#':
                    out.append(l[:i] + '\n')
                    break
        else:
            out.append(l)
    # no space in package names
    pkgs = ''.join(out).split()
    return package_list_translate(pkgs, target_arch)

def package_list_file_install(filename, target_arch):
    pkgs = package_list_file_load(filename, target_arch)
    package_install(pkgs)

def package_install(pkgs):
    subprocess.check_call(['dnf', 'install', '-y'] + pkgs)

def package_is_installed(pkg):
    r = subprocess.call(['rpm', '-q', pkg], stdout=subprocess.DEVNULL)
    return (r == 0)

def fedora_version_get():
    '-> "28"'
    fedora_version = subprocess.Popen(['rpm', '-E', '%fedora'], stdout=subprocess.PIPE).stdout.read().strip().decode('ascii')
    return fedora_version

def repo_rpm_urls_load(filename, target_arch):
    '''Input Format:
https://download1.rpmfusion.org/free/fedora/rpmfusion-free-release-{fedora_version!s}.noarch.rpm
'''
    d = dict(fedora_version=fedora_version_get(),
             target_arch=target_arch)

    with open(filename) as f:
        lines = f.readlines()
    out = []
    for l in lines:
        out.append(l.format_map(d))
    return out

DEFAULT_UID = 1000

def default_target_user():
    uid = os.getuid()
    if uid == 0:
        try:
            uid = int(os.environ['SUDO_UID'])
        except (ValueError, KeyError):
            uid = DEFAULT_UID
    return pwd.getpwuid(uid).pw_name