#!/usr/bin/env python3
'''
Script to set the domain of the locally installed Nudgis, Miris Manager or Monitor application.
'''
from pathlib import Path
import argparse
import os
import re
import subprocess
import sys
import time


UNIX_USER_PATTERN = r'[a-z0-9\-]+'
DOMAIN_PATTERN = r'([a-z0-9\-]+\.)*[a-z0-9\-]+(\.[a-z]+){0,1}'


def log(text, error=False):
    fo = sys.stderr if error else sys.stdout
    print(text, file=fo)
    fo.flush()


def main():
    # Parse args
    parser = argparse.ArgumentParser(description=__doc__.strip())
    parser.add_argument('-d', '--dry-run', action='store_true', help='Enable dry run mode.')
    parser.add_argument('app', help='''The application for which the new domain should be set.
Possible values: "ms" (Nudgis), "mm" (Miris Manager), "mon" (Monitor).
It is possible to specify which MediaServer instance should be targetted
by using this format: "ms-<instance name>" (for example "ms-msuser").''')
    parser.add_argument('current_domain', help='The current domain.')
    parser.add_argument('new_domain', help='The new domain.')
    args = parser.parse_args()

    # Check user
    if os.getuid() != 0:
        print('This script must be run as root.')
        return 1

    # Get domains
    old_domain = args.current_domain.strip()
    if not args.current_domain or not re.match(DOMAIN_PATTERN, old_domain):
        log(f'The given domain "{old_domain}" does not match the expected pattern ({DOMAIN_PATTERN}).')
        return 1
    new_domain = args.new_domain.strip()
    if not args.new_domain or not re.match(DOMAIN_PATTERN, new_domain):
        log(f'The given domain "{new_domain}" does not match the expected pattern ({DOMAIN_PATTERN}).')
        return 1

    # Get files to change
    if args.app == 'mon':
        paths = [
            Path('/etc/ubicast-webmonitor/install.ini'),
            Path('/etc/webmonitor/install.ini'),  # Old path
            Path('/etc/nginx/sites-available/ubicast-webmonitor.conf'),
            Path('/etc/nginx/sites-available/webmonitor.conf'),  # Old path
            Path('/etc/nginx/sites-available/msmonitor.conf'),  # Old path
            Path('/var/lib/ubicast-webmonitor/private/settings_override.py'),
            Path('/home/webmonitor/webmonitor/private/settings_override.py'),  # Old path
            Path('/home/msmonitor/msmonitor/data/settings_override.py'),  # Old path
        ]
        warning = None
    elif args.app == 'mm':
        paths = [
            Path('/etc/ubicast-skyreach/install.ini'),
            Path('/etc/skyreach/install.ini'),  # Old path
            Path('/etc/nginx/sites-available/ubicast-skyreach.conf'),
            Path('/etc/nginx/sites-available/skyreach.conf'),  # Old path
            Path('/var/lib/ubicast-skyreach/private/settings_override.py'),
            Path('/home/skyreach/skyreach_data/private/settings_override.py'),  # Old path
        ]
        warning = '''Some steps to change the domain should be done manually:
        - Change the url of Miris Manager in the related Nudgis.'''
    elif args.app == 'ms' or args.app.startswith('ms-'):
        if args.app.startswith('ms-'):
            instance = args.app[3:].strip('. -\t\n')
            if not re.match(UNIX_USER_PATTERN, instance):
                log(f'The instance name does not match the expected pattern ({UNIX_USER_PATTERN}).')
                return 1
        else:
            instance = 'msuser'
        paths = [
            Path(f'/etc/nginx/sites-available/ubicast-mediaserver_{instance}.conf'),
            Path(f'/etc/nginx/sites-available/mediaserver-{instance}.conf'),  # Old path
            Path(f'/var/lib/ubicast-mediaserver/portals/{instance}/private/mssettings.py'),
            Path(f'/home/{instance}/msinstance/conf/mssettings.py'),  # Old path
            Path('/etc/ubicast-celerity/config.py'),
            Path('/etc/celerity/config.py'),  # Old path
        ]
        warning = f'''Some steps to change the domain should be done manually:
        - Change the domain in configuration file "/etc/ubicast-celerity/config.py" of Celerity server and workers.
          Command to use:
                sed -i 's/{old_domain}/{new_domain}/g' /etc/*celerity/config.py
        - Change the domain used in Miris Manager systems configuration.'''
    else:
        log('Invalid app name requested.')
        return 1
    paths.extend([
        Path('/root/envsetup/conf.sh'),
        Path('/root/envsetup/auto-generated-conf.sh'),
        Path('/etc/hosts'),
    ])

    # Change domain
    for path in paths:
        if path.exists():
            log(f'Searching old domain in file "{path}".')
            p = subprocess.run(['grep', old_domain, str(path)])
            if p.returncode != 0:
                log('No occurrence in file.')
            elif not args.dry_run:
                log(f'Replacing domain in file "{path}".')
                subprocess.run(['sed', '-i', f's/{old_domain}/{new_domain}/g', str(path)], check=True)

    # Restart Nginx
    log('Checking Nginx configuration.')
    subprocess.run(['nginx', '-t'], check=True)
    if args.dry_run:
        log('Nginx will be reloaded when the script is not in dry run mode.')
    else:
        log('Reloading Nginx.')
        subprocess.run(['systemctl', 'reload', 'nginx'], check=True)

    # Wait for reloads (Nginx & application) to be effective
    time.sleep(3)

    log('\033[92mDone\033[0m')
    if warning:
        log('\033[93mWarning:\033[0m')
        log(warning)
    return 0


if __name__ == '__main__':
    sys.exit(main())
