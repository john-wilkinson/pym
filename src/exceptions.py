class InstallerNotFoundException(Exception):
    """
    Raised when an installer cannot be found for the specified source
    """


class VersionNotFoundException(Exception):
    """
    Raised when the specified version cannot be found
    """


class PymPackageNotFoundException(Exception):
    """
    Raised when a package could not be found
    """


class PymPackageException(Exception):
    """
    Raised when not a PymPackage
    """
