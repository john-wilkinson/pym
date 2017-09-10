import os
import shutil
import errno
import stat
import package
from git import Repo


def make():
    return {
        InstallCommand.COMMAND: InstallCommand,
    }


class InstallCommand(object):
    COMMAND = 'install'

    @classmethod
    def args(cls, subparsers):
        subparser = subparsers.add_parser(InstallCommand.COMMAND, help='Install the specified package',
                                          epilog='Example: pym install --save https://github.com/tornadoweb/tornado.git')
        subparser.add_argument('package', help='Package name (or git location)')
        subparser.add_argument('--save', help='Save the package to local config', action='store_true')

    def __init__(self, config):
        self.installers = [
            GitInstaller
        ]

        self.dest = config.get('install_location', 'packages')

    def run(self, args):
        name = args['package']
        installer = self.find_installer(name)
        print('Installing {}'.format(name))

        pym_package = installer.install(self.dest)
        try:
            pym_package.config
        except package.PymPackageException:
            print('No pym config file found, creating...')
            creator = package.PymConfigCreator()
            src_guess = self.guess_src(pym_package)
            print('Guessing source location: '.format(src_guess))
            config = creator.create(use_suggestions=True, name=pym_package.name, description=pym_package.description,
                                    version=pym_package.version, src=src_guess)
            pym_package.config = config
            print(config)

        print('Successfully installed {}!'.format(pym_package.name))

    def find_installer(self, package_name):
        pym_package = package.PymPackage(package_name)

        for installer in self.installers:
            if installer.can_install(pym_package.source):
                return installer(pym_package)
        else:
            raise Exception('Failed to find an installer for {}'.format(package_name))

    def guess_src(self, pym_package):
        def make_guess(path, suffixes):
            for suffix in suffixes:
                yield os.path.join(path, suffix)

        for guess in make_guess(pym_package.path, ['src', pym_package.name]):
            if os.path.exists(guess):
                return os.path.relpath(guess, pym_package.path)


class GitInstaller(object):
    @classmethod
    def can_install(cls, source):
        return source.endswith('.git')

    def __init__(self, pym_package):
        self.pym_package = pym_package

    def install(self, dest):
        path = self.clone(os.path.join(dest, self.pym_package.name))
        self.remove_git(path)
        self.pym_package.path = path
        return self.pym_package

    def remove_git(self, path):

        def handle_readonly(func, path, exc):
            excvalue = exc[1]
            if excvalue.errno == errno.EACCES:
                os.chmod(path, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)  # 0777
                func(path)
            else:
                raise exc[1]

        git_dir = os.path.join(path, '.git')
        shutil.rmtree(git_dir, ignore_errors=False, onerror=handle_readonly)

    def clone(self, dest):
        repo = Repo.clone_from(self.pym_package.source, dest)
        self.pym_package.description = repo.description
        self.pym_package.version = str(repo.active_branch)
        print(repo.active_branch)
        return repo.working_dir
