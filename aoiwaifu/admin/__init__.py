"""Admin command modules loader for AoiWaifu Bot."""

import glob
import logging
from os.path import basename, dirname, isfile

LOGGER = logging.getLogger(__name__)

LOAD = []
NO_LOAD = []


def __list_all_admin_modules():
    mod_paths = glob.glob(dirname(__file__) + "/*.py")
    all_modules = sorted(
        basename(f)[:-3]
        for f in mod_paths
        if isfile(f) and f.endswith(".py") and not f.endswith("__init__.py")
    )

    if LOAD or NO_LOAD:
        to_load = list(LOAD) if LOAD else all_modules
        if LOAD:
            if not all(mod in all_modules for mod in to_load):
                LOGGER.error("Invalid admin loadorder names, quitting...")
                raise SystemExit(1)
            remaining = sorted(set(all_modules) - set(to_load))
            to_load = remaining + to_load
        if NO_LOAD:
            LOGGER.info("Not loading admin modules: %s", NO_LOAD)
            return [item for item in to_load if item not in NO_LOAD]
        return to_load

    return all_modules


ALL_ADMIN_MODULES = __list_all_admin_modules()
LOGGER.info("Admin modules to load: %s", str(ALL_ADMIN_MODULES))
__all__ = ALL_ADMIN_MODULES + ["ALL_ADMIN_MODULES"]
