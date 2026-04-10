#!/usr/bin/env python3
'''
Transition script from envsetup to UbiCast security packages.
'''

import subprocess
import sys


def migrate():
    print(__doc__)
    # Rename UbiCast source list and get miris manager url
    subprocess.run('mv /etc/apt/sources.list.d/skyreach.list /etc/apt/sources.list.d/ubicast.list', shell=True)
    if subprocess.run(
        'grep -E "^deb https://skyreach.ubicast.net" /etc/apt/sources.list.d/ubicast.list', shell=True
    ).returncode == 0:
        mirismanager_url = 'https://skyreach.ubicast.net'
    else:
        mirismanager_url = 'https://mirismanager.ubicast.eu'

    # Add UbiCast security repository and packages
    subprocess.run('apt-get update', shell=True)
    subprocess.run('apt-get install -y apt-transport-https curl', shell=True)
    subprocess.run('curl -s -o- %s/media/public.gpg | apt-key add -' % mirismanager_url, shell=True)
    with open('/etc/apt/sources.list.d/ubicast-secu.list', 'w') as fo:
        fo.write('deb %s packaging/apt/ubicast-security-updates/' % mirismanager_url)
    subprocess.run('apt-get update', shell=True)
    subprocess.run('apt-get install -y ubicast-env ubicast-tester ubicast-ssh-access', shell=True)

    # Mark old test packages as automatically installed
    subprocess.run(
        'apt-mark auto '
        'bsd-mailx python3-apt python3-defusedxml python3-dnspython python3-openssl python3-psutil '
        'python3-packaging python3-lxml python3-psycopg2 python3-pydbus python3-requests python3-spf '
        'openjdk-8-jre-headless openjdk-11-jre-headless',
        shell=True
    )

    # Check that security automatic updates are enabled
    subprocess.run('apt-get install -y unattended-upgrades grep', shell=True)
    p = subprocess.run('grep -r \'APT::Periodic::Unattended-Upgrade "1"\' /etc/apt/apt.conf.d/', shell=True)
    if p.returncode != 0:
        with open('/etc/apt/apt.conf.d/20auto-upgrades', 'w') as fo:
            fo.write('APT::Periodic::Update-Package-Lists "1";\nAPT::Periodic::Unattended-Upgrade "1";')

    # Enable UbiCast security repository in automatic updates
    unattended_conf = '/etc/apt/apt.conf.d/50unattended-upgrades'
    with open(unattended_conf, 'r') as fo:
        content = fo.read()
    if 'Unattended-Upgrade::Origins-Pattern {\n' in content:
        # Unattended upgrades 1.11+ (Debian 10)
        if '"origin=UbiCast,label=UbiCast-Security";' not in content:
            new_content = content.replace(
                'Unattended-Upgrade::Origins-Pattern {\n',
                'Unattended-Upgrade::Origins-Pattern {\n        "origin=UbiCast,label=UbiCast-Security";\n')
            with open(unattended_conf, 'w') as fo:
                fo.write(new_content)
            print('Updated "%s"' % unattended_conf)
    elif 'Unattended-Upgrade::Allowed-Origins {\n' in content:
        # Unattended upgrades 1.1 (Ubuntu 18)
        if '"UbiCast:UbiCast-Security";' not in content:
            new_content = content.replace(
                'Unattended-Upgrade::Allowed-Origins {\n',
                'Unattended-Upgrade::Allowed-Origins {\n        "UbiCast:UbiCast-Security";\n')
            with open(unattended_conf, 'w') as fo:
                fo.write(new_content)
            print('Updated "%s"' % unattended_conf)
    else:
        print('Unrecognized unattended-upgrades version.')

    # Remove old tester files
    to_remove = [
        '/root/envsetup/.docker',
        '/root/envsetup/.flake8',
        '/root/envsetup/.git',
        '/root/envsetup/.githooks',
        '/root/envsetup/.gitignore',
        '/root/envsetup/.gitlab-ci.yml',
        '/root/envsetup/.lint',
        '/root/envsetup/ansible',
        '/root/envsetup/doc',
        '/root/envsetup/Makefile',
        '/root/envsetup/README.md',
        '/root/envsetup/tests',  # the file itself
    ]
    for path in to_remove:
        subprocess.run(['rm', '-rf', path])

    # Disable and remove systemd scripts
    subprocess.run(['systemctl', 'disable', 'envsetup-tester.timer'])
    subprocess.run(['systemctl', 'stop', 'envsetup-tester.timer'])
    subprocess.run(['systemctl', 'disable', 'envsetup-tester.service'])
    subprocess.run(['rm', '-rf', '/lib/systemd/system/envsetup-tester.timer'])
    subprocess.run(['rm', '-rf', '/lib/systemd/system/envsetup-tester.service'])

    # Run tester
    subprocess.run(['python3', '/root/ubicast-tester/tester.py', '-e'])

    return 0


if __name__ == '__main__':
    sys.exit(migrate())
