#!/usr/bin/env python
# encoding: utf-8

from ConfigParser import ConfigParser
from os.path import expanduser, dirname, realpath
import sys


class Sections(object):
    """Sections of CONF
    """
    DEFAULT = "setting"
    TEST = "test"


CONF = ConfigParser()
CONF.read("%s/proxy.ini" % dirname(sys.argv[0]))
CONF.read(expanduser("~/conf/proxy.ini"))
CONF.read(realpath("./proxy.ini"))

# make sure all Sections.sections exists in CONF
for s in dir(Sections):
    if s.startswith("_"):
        continue

    section = getattr(Sections, s)
    if not CONF.has_section(section) and section != "default":
        CONF.add_section(section)
