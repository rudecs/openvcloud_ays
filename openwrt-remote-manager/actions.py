from JumpScale import j

ActionsBase = j.packages.getActionsBaseClass()


class Actions(ActionsBase):

    """
    process for install
    -------------------
    step1: prepare actions
    step2: check_requirements action
    step3: download files & copy on right location (hrd info is used)
    step4: configure action
    step5: check_uptime_local to see if process stops  (uses timeout $process.stop.timeout)
    step5b: if check uptime was true will do stop action and retry the check_uptime_local check
    step5c: if check uptime was true even after stop will do halt action and retry the check_uptime_local check
    step6: use the info in the hrd to start the application
    step7: do check_uptime_local to see if process starts
    step7b: do monitor_local to see if package healthy installed & running
    step7c: do monitor_remote to see if package healthy installed & running, but this time test is done from central location
    """

    def build(self, **kwargs):
        import zipfile

        BUILD_BASE = '/opt/build/openwrt-remote-manager'
        PKG = BUILD_BASE + '/pkg'
        j.system.fs.createDir(BUILD_BASE)

        SOURCE_ZIP_URL = 'https://github.com/Jumpscale/openwrt-remote-manager/archive/master.zip'
        local_file = j.system.fs.joinPaths(
            BUILD_BASE, 'openwrt-remote-manager.tar.gz')
        j.system.net.downloadIfNonExistent(SOURCE_ZIP_URL, local_file)

        uncompressed_path = j.system.fs.joinPaths(BUILD_BASE, 'uncompressed')
        with zipfile.ZipFile(local_file, 'r') as zipped:
            zipped.extractall(uncompressed_path)

        if j.system.fs.exists(PKG):
            j.system.fs.removeDirTree(PKG)

        j.system.fs.copyDirTree(
            j.system.fs.joinPaths(uncompressed_path, 'openwrt-remote-manager-master'), PKG)

        def python_deps():
            return open(j.system.fs.joinPaths(PKG, 'requirements.txt')).read().split()

        for python_dep in python_deps():
            install_path = j.system.fs.joinPaths(PKG, 'pip-' + python_dep)
            install_command = 'pip install --exists-action=w --target="%(target)s" %(dep)s' % {
                'dep': python_dep, 'target': install_path}
            j.system.process.executeWithoutPipe(
                install_command, dieOnNonZeroExitCode=False, printCommandToStdout=True)
            copy_command = 'cp -r %(install_path)s/* %(pkg_path)s/' % {
                'install_path': install_path, 'pkg_path': PKG}
            j.system.process.executeWithoutPipe(
                copy_command, dieOnNonZeroExitCode=False, printCommandToStdout=True)

            # Delete all the leftover 'pip-*' directories
            command = 'rm -r %s/pip-*' % PKG
            j.system.process.executeWithoutPipe(
                command, dieOnNonZeroExitCode=False, printCommandToStdout=True)
