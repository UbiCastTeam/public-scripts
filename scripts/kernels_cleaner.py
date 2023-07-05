#!/usr/bin/env python3
"""
This script will delete all old non used kernels.
Tested on Ubuntu 12.04, 14.04, 16.04, 18.04, Debian 10, Debian 11.
"""
import sys
import subprocess
import re


RED = '\033[91m'
GREEN = '\033[92m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
PURPLE = '\033[95m'
TEAL = '\033[96m'
DEFAULT = '\033[0m'


def log(text, error=False):
    fo = sys.stderr if error else sys.stdout
    print(text, file=fo)
    fo.flush()


def clean_kernels():
    # Check that the user can use sudo
    p = subprocess.run(
        ['sudo', 'echo', 'ok'],
        stdin=sys.stdin, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if p.returncode != 0:
        log(RED + 'Failed to get sudo right.' + DEFAULT, error=True)
        return 1
    # List installed kernels
    p = subprocess.run(
        ['sudo', 'dpkg', '--get-selections'],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out = p.stdout.decode('utf-8').strip()
    err = p.stderr.decode('utf-8').strip()
    if p.returncode != 0:
        log(RED + 'Failed to list kernels.' + DEFAULT + '\nOut: ' + out + '\nErr: ' + err, error=True)
        return 1
    kernels = list()
    for line in out.split('\n'):
        m = re.match(r'linux-(?:headers|image|modules)(?:-extra){0,1}-([\d\.\-]+)', line)
        if m:
            version = m.groups()[0]
            if version[-1] == '-':
                version = version[:-1]
            version = [int(v) for v in version.replace('-', '.').split('.')]
            kernels.append((line.split('\t')[0], version))
    if not kernels:
        log('No kernels found.')
        return 1
    log('Installed kernels:\n\t' + '\n\t'.join([n for n, v in kernels]))
    # Get current kernel
    p = subprocess.run(
        ['uname', '-a'],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out = p.stdout.decode('utf-8').strip()
    err = p.stderr.decode('utf-8').strip()
    if p.returncode != 0:
        log(RED + 'Failed to get current kernel.' + DEFAULT + '\nOut: ' + out + '\nErr: ' + err, error=True)
        return 1
    try:
        current_str = out.split(' ')[2]
        if current_str.endswith('-generic'):
            current_str = current_str[:-len('-generic')]
        elif current_str.endswith('-amd64'):
            current_str = current_str[:-len('-amd64')]
        current = [int(v) for v in current_str.replace('-', '.').split('.')]
    except Exception as e:
        log(RED + 'Failed to get current kernel.' + DEFAULT + '\nError: ' + str(e), error=True)
        return 1
    log('Current kernel is: ' + PURPLE + current_str + DEFAULT)
    # Get most recent kernel
    latest = current
    for name, version in kernels:
        if version > latest:
            latest = version
    # Get kernel packages to purge
    to_purge = list()
    for name, version in kernels:
        if version < latest and version != current:
            to_purge.append(name)
    if not to_purge:
        log('No kernel package to purge.')
        return 0
    log('Kernel packages to purge:\n\t' + '\n\t'.join(to_purge))
    try:
        r = input('Do you confirm the deletion of these packages? [y]/n ')
    except (KeyboardInterrupt, EOFError):
        log('')
    else:
        if not r or r in ('y', 'yes'):
            log(PURPLE + 'Starting purge...' + DEFAULT)
            cmd = ['sudo', 'apt-get', '--yes', 'purge']
            cmd.extend(to_purge)
            p = subprocess.run(cmd, stdin=sys.stdin, stdout=sys.stdout, stderr=sys.stderr)
            sys.stdout.flush()
            sys.stderr.flush()
            if p.returncode != 0:
                log(RED + 'Failed to purge kernel packages.' + DEFAULT, error=True)
                return 1
            log(GREEN + 'Packages purged.' + DEFAULT)
    return 0


if __name__ == '__main__':
    sys.exit(clean_kernels())
