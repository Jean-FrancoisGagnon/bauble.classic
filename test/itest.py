#!/usr/bin/env python
#
# itest.py
#
# provides an interactive test environment
#
import sqlalchemy as sa
from sqlalchemy.orm import *

import bauble
import bauble.db as db
import bauble.meta as meta
import bauble.pluginmgr as pluginmgr

import logging
logging.basicConfig()

uri = 'sqlite:///:memory:'
db.open(uri, False)
pluginmgr.load()
# the one thing this script doesn't do that bauble does is called
# pluginmgr.init()
#pluginmgr.init(force=True)
db.create(import_defaults=False)

from bauble.plugins.plants import Family, Genus, Species
from bauble.plugins.garden import Accession, Plant, Location

accession_table = Accession.__table__
plant_table = Plant.__table__
#location_table = Location.__table__

session = db.Session()

f = Family(family=u'family')
g = Genus(family=f, genus=u'genus')
s = Species(genus=g, sp=u's')
l = Location(name=u'site', code=u'code')

# a = Accession(species=s, code=u'1')
# p = Plant(accession=a, location=l, code=u'1')
# p2 = Plant(accession=a, location=l, code=u'2')
# p3 = Plant(accession=a, location=l, code=u'3')

# a2 = Accession(species=s, code=u'2')
# p4 = Plant(accession=a2, location=l, code=u'4')
# p5 = Plant(accession=a2, location=l, code=u'5')
# p6 = Plant(accession=a2, location=l, code=u'6')


session.add_all([f, g, s])#, a, a2, p])
session.commit()

# print 'drop'
# pluginmgr.PluginRegistry.__table__.drop()
# print 'create'
# pluginmgr.PluginRegistry.__table__.create()
# print 'done.'

