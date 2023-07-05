def classFactory(iface):  # pylint: disable=invalid-name
    from .code import Importer
    return Importer(iface)
