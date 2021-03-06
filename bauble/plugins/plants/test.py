# -*- coding: utf-8 -*-
#
# test.py
#
# Description: test for the Plant plugin
#

import os
import sys
import unittest

from sqlalchemy import *
from sqlalchemy.exc import *
from sqlalchemy.orm.exc import *

import bauble
import bauble.utils as utils
from bauble.utils.log import debug
from bauble.plugins.plants.species import *
from bauble.plugins.plants.family import *
from bauble.plugins.plants.genus import *
from bauble.plugins.plants.geography import *
from bauble.test import BaubleTestCase, check_dupids

#
# TODO: things to create tests for
#
# - test schema cascading works for all tables in the plants module
# - test unicode is working properly in the relevant fields, especially
# in the Species.str function
# - test the setting the default vernacular name on a species is working
# and that delete vernacular names and default vernacular names does
# proper  cascading
# make sure that deleting either of the species referred to in a synonym
# deletes the synonym

# TODO: create some scenarios that should fail

if sys.platform == 'win32':
    # on windows the hybrid char is set to 'x'in PlantPlugin.init but
    # these strings are initialized before init is called so we set it
    # here...this sort of breaks the string tests since we aren't
    # relying on the behavior of PlantPlugin.init but what can we do?
    Species.hybrid_char = 'x'


family_test_data = ({'id': 1, 'family': 'Orchidaceae'},
                    {'id': 2, 'family': 'Leguminosae'},
                    {'id': 3, 'family': 'Polypodiaceae'})

genus_test_data = ({'id': 1, 'genus': 'Maxillaria', 'family_id': 1},
                   {'id': 2, 'genus': 'Encyclia', 'family_id': 1},
                   {'id': 3, 'genus': 'Abrus', 'family_id': 2},
                   {'id': 4, 'genus': 'Campyloneurum', 'family_id': 3},
                   )

species_test_data = ({'id': 1, 'sp': u'variabilis', 'genus_id': 1,
                      'sp_author': u'Bateman ex Lindl.'},
                     {'id': 2, 'sp': u'cochleata', 'genus_id': 2,
                      'sp_author': u'(L.) Lem\xe9e'},
                     {'id': 3, 'sp': u'precatorius', 'genus_id': 3,
                      'sp_author': u'L.'},
                     {'id': 4, 'sp': u'alapense', 'genus_id': 4,
                      'hybrid': True, 'sp_author': u'F\xe9e'},
                     {'id': 5, 'sp': u'cochleata', 'genus_id': 2,
                      'sp_author': u'(L.) Lem\xe9e',
                      'infrasp1_rank': u'var.', 'infrasp1': u'cochleata'},
                     {'id': 6, 'sp': u'cochleata', 'genus_id': 2,
                      'sp_author': u'(L.) Lem\xe9e',
                      'infrasp1_rank': u'cv.', 'infrasp1': u'Black Night'},
                     {'id': 7, 'sp': u'precatorius', 'genus_id': 3,
                      'sp_author': u'L.', 'cv_group': u'SomethingRidiculous'},
                     {'id': 8, 'sp': u'precatorius', 'genus_id': 3,
                      'sp_author': u'L.',
                      'infrasp1_rank': u'cv.', 'infrasp1': u'Hot Rio Nights',
                      'cv_group': u'SomethingRidiculous'},
                     {'id': 9, 'sp': u'generalis', 'genus_id': 1,
                      'hybrid': True,
                      'infrasp1_rank': u'cv.', 'infrasp1': u'Red'},
                     {'id': 10, 'sp': u'generalis', 'genus_id': 1,
                      'hybrid': True, 'sp_author': u'L.',
                      'infrasp1_rank': u'cv.', 'infrasp1': u'Red',
                      'cv_group': u'SomeGroup'},
                     {'id': 11, 'sp': u'generalis', 'genus_id': 1,
                      'sp_qual': u'agg.'},
                     {'id': 12, 'genus_id': 1, 'cv_group': u'SomeGroup'},
                     {'id': 13, 'genus_id':1,
                      'infrasp1_rank': u'cv.', 'infrasp1': u'Red'},
                     {'id': 14, 'genus_id':1,
                      'infrasp1_rank': u'cv.', 'infrasp1': u'Red & Blue'},
                     {'id': 15, 'sp': u'cochleata', 'genus_id': 2,
                      'sp_author': u'L.',
                      'infrasp1_rank': u'subsp.', 'infrasp1': u'cochleata',
                      'infrasp1_author': u'L.',
                      'infrasp2_rank': u'var.', 'infrasp2': u'cochleata',
                      'infrasp2_author': u'L.',
                      'infrasp3_rank': u'cv.', 'infrasp3': u'Black',
                      'infrasp3_author': u'L.'},
                     {'id': 16, 'genus_id': 1, 'sp': u'test',
                      'infrasp1_rank': u'subsp.', 'infrasp1': u'test',
                      'cv_group': u'SomeGroup'},
                     )

species_str_map = {\
    1: 'Maxillaria variabilis',
    2: 'Encyclia cochleata',
    3: 'Abrus precatorius',
    4: 'Campyloneurum %s alapense' % Species.hybrid_char,
    5: 'Encyclia cochleata var. cochleata',
    6: "Encyclia cochleata 'Black Night'",
    7: 'Abrus precatorius SomethingRidiculous Group',
    8: "Abrus precatorius (SomethingRidiculous Group) 'Hot Rio Nights'",
    9: "Maxillaria %s generalis 'Red'" % Species.hybrid_char,
    10:"Maxillaria %s generalis (SomeGroup Group) 'Red'" % Species.hybrid_char,
    11:"Maxillaria generalis agg.",
    12:"Maxillaria SomeGroup Group",
    13:"Maxillaria 'Red'",
    14:"Maxillaria 'Red & Blue'",
    15:"Encyclia cochleata subsp. cochleata var. cochleata 'Black'",
    16:"Maxillaria test subsp. test SomeGroup Group"
    }

species_markup_map = {\
    1: '<i>Maxillaria</i> <i>variabilis</i>',
    2: '<i>Encyclia</i> <i>cochleata</i>',
    3: '<i>Abrus</i> <i>precatorius</i>',
    4: '<i>Campyloneurum</i> %s <i>alapense</i>' % Species.hybrid_char,
    5: '<i>Encyclia</i> <i>cochleata</i> var. <i>cochleata</i>',
    6: '<i>Encyclia</i> <i>cochleata</i> \'Black Night\'',
    12:"<i>Maxillaria</i> SomeGroup Group",
    14:"<i>Maxillaria</i> 'Red &amp; Blue'",
    15:"<i>Encyclia</i> <i>cochleata</i> subsp. <i>cochleata</i> var. <i>cochleata</i> 'Black'",
    }

species_str_authors_map = {\
    1: 'Maxillaria variabilis Bateman ex Lindl.',
    2: u'Encyclia cochleata (L.) Lem\xe9e',
    3: 'Abrus precatorius L.',
    4: u'Campyloneurum %s alapense F\xe9e' % Species.hybrid_char,
    5: u'Encyclia cochleata (L.) Lem\xe9e var. cochleata',
    6: u'Encyclia cochleata (L.) Lem\xe9e \'Black Night\'',
    7: 'Abrus precatorius L. SomethingRidiculous Group',
    8: "Abrus precatorius L. (SomethingRidiculous Group) 'Hot Rio Nights'",
    15:"Encyclia cochleata L. subsp. cochleata L. var. cochleata L. 'Black' L.",
}

species_markup_authors_map = {\
    1: '<i>Maxillaria</i> <i>variabilis</i> Bateman ex Lindl.',
    2: u'<i>Encyclia</i> <i>cochleata</i> (L.) Lem\xe9e',
    3: '<i>Abrus</i> <i>precatorius</i> L.',
    4: u'<i>Campyloneurum</i> %s <i>alapense</i> F\xe9e' % Species.hybrid_char,
    5: u'<i>Encyclia</i> <i>cochleata</i> (L.) Lem\xe9e var. <i>cochleata</i>',
    6: u'<i>Encyclia</i> <i>cochleata</i> (L.) Lem\xe9e \'Black Night\''}

sp_synonym_test_data = ({'id': 1, 'synonym_id': 1, 'species_id': 2},
                        )

vn_test_data = ({'id': 1, 'name': u'SomeName', 'language': u'English',
                 'species_id': 1},
                {'id': 2, 'name': u'SomeName 2', 'language': u'English',
                 'species_id': 1},
                )

test_data_table_control = ((Family, family_test_data),
                           (Genus, genus_test_data),
                           (Species, species_test_data),
                           (VernacularName, vn_test_data),
                           (SpeciesSynonym, sp_synonym_test_data))

def setUp_data():
    """
    bauble.plugins.plants.test.setUp_test_data()

    if this method is called again before tearDown_test_data is called you
    will get an error about the test data rows already existing in the database
    """
    import copy
    for mapper, data in test_data_table_control:
        table = mapper.__table__
        # insert row by row instead of doing an insert many since each
        # row will have different columns
        for row in data:
            table.insert().execute(row).close()
        for col in table.c:
            utils.reset_sequence(col)


def test_duplicate_ids():
    """
    Test for duplicate ids for all .glade files in the plants plugin.
    """
    import bauble.plugins.plants as mod
    import glob
    head, tail = os.path.split(mod.__file__)
    files = glob.glob(os.path.join(head, '*.glade'))
    for f in files:
        assert(not check_dupids(f))


class PlantTestCase(BaubleTestCase):

    def __init__(self, *args):
        super(PlantTestCase, self).__init__(*args)

    def setUp(self):
        super(PlantTestCase, self).setUp()
        setUp_data()

    def tearDown(self):
        super(PlantTestCase, self).tearDown()


class FamilyTests(PlantTestCase):
    """
    Test for Family and FamilySynonym
    """
    def test_cascades(self):
        """
        Test that cascading is set up properly
        """
        family = Family(family=u'family')
        genus = Genus(family=family, genus=u'genus')
        self.session.add_all([family, genus])
        self.session.commit()

        # test that deleting a family deletes an orphaned genus
        self.session.delete(family)
        self.session.commit()
        query = self.session.query(Genus).filter_by(family_id=family.id)
        self.assertRaises(NoResultFound, query.one)


    def test_synonyms(self):
        """
        Test that Family.synonyms works correctly
        """
        family = Family(family=u'family')
        family2 = Family(family=u'family2')
        family.synonyms.append(family2)
        self.session.add_all([family, family2])
        self.session.commit()

        # test that family2 was added as a synonym to family
        family = self.session.query(Family).filter_by(family=u'family').one()
        self.assert_(family2 in family.synonyms)

        # test that the synonyms relation and family backref works
        self.assert_(family._synonyms[0].family == family)
        self.assert_(family._synonyms[0].synonym == family2)

        # test that the synonyms are removed properly
        family.synonyms.remove(family2)
        self.session.commit()
        self.assert_(family2 not in family.synonyms)

        # test synonyms contraints, e.g that a family cannot have the
        # same synonym twice
        family.synonyms.append(family2)
        self.session.commit()
        family.synonyms.append(family2)
        self.assertRaises(IntegrityError, self.session.commit)
        self.session.rollback()

        # test that clearing all the synonyms works
        family.synonyms.clear()
        self.session.commit()
        self.assert_(len(family.synonyms) == 0)
        self.assert_(self.session.query(FamilySynonym).count() == 0)

        # test that deleting a family that is a synonym of another family
        # deletes all the dangling object s
        family.synonyms.append(family2)
        self.session.commit()
        self.session.delete(family2)
        self.session.commit()
        self.assert_(self.session.query(FamilySynonym).count() == 0)

        # test that deleting the previous synonyms didn't delete the
        # family that it refered to
        self.assert_(self.session.query(Family).get(family.id))

        # test that deleting a family that has synonyms deletes all
        # the synonyms that refer to that family deletes all the
        family2 = Family(family=u'family2')
        self.session.add(family2)
        family.synonyms.append(family2)
        self.session.commit()
        self.session.delete(family)
        self.session.commit()
        self.assert_(self.session.query(FamilySynonym).count() == 0)


    def test_constraints(self):
        """
        Test that the family constraints were created correctly
        """
        values = [dict(family=u'family'),
                  dict(family=u'family', qualifier=u's. lat.')]
        for v in values:
            self.session.add(Family(**v))
            self.session.add(Family(**v))
            self.assertRaises(IntegrityError, self.session.commit)
            self.session.rollback()

        # test that family cannot be null
        self.session.add(Family(family=None))
        self.assertRaises(IntegrityError, self.session.commit)
        self.session.rollback()


    def test_str(self):
        """
        Test that the family str function works as expected
        """
        f = Family()
        self.assert_(str(f) == repr(f))
        f = Family(family=u'fam')
        self.assert_(str(f) == 'fam')
        f.qualifier = 's. lat.'
        self.assert_(str(f) == 'fam s. lat.')

    def itest_editor(self):
        """
        Interactively test the PlantEditor
        """
        #loc = self.create(Family, name=u'some site')
        fam = Family(family='some family')
        editor = FamilyEditor(model=fam)
        editor.start()
        del editor
        assert utils.gc_objects_by_type('FamilyEditor') == [], \
            'FamilyEditor not deleted'
        assert utils.gc_objects_by_type('FamilyEditorPresenter') == [], \
            'FamilyEditorPresenter not deleted'
        assert utils.gc_objects_by_type('FamilyEditorView') == [], \
            'FamilyEditorView not deleted'



class GenusTests(PlantTestCase):

    def test_synonyms(self):
        family = Family(family=u'family')
        genus = Genus(family=family, genus=u'genus')
        genus2 = Genus(family=family, genus=u'genus2')
        genus.synonyms.append(genus2)
        self.session.add_all([genus, genus2])
        self.session.commit()

        # test that genus2 was added as a synonym to genus
        genus = self.session.query(Genus).filter_by(genus=u'genus').one()
        self.assert_(genus2 in genus.synonyms)

        # test that the synonyms relation and genus backref works
        self.assert_(genus._synonyms[0].genus == genus)
        self.assert_(genus._synonyms[0].synonym == genus2)

        # test that the synonyms are removed properly
        genus.synonyms.remove(genus2)
        self.session.commit()
        self.assert_(genus2 not in genus.synonyms)

        # test synonyms contraints, e.g that a genus cannot have the
        # same synonym twice
        genus.synonyms.append(genus2)
        self.session.commit()
        genus.synonyms.append(genus2)
        self.assertRaises(IntegrityError, self.session.commit)
        self.session.rollback()

        # test that clearing all the synonyms works
        genus.synonyms.clear()
        self.session.commit()
        self.assert_(len(genus.synonyms) == 0)
        self.assert_(self.session.query(GenusSynonym).count() == 0)

        # test that deleting a genus that is a synonym of another genus
        # deletes all the dangling objects
        genus.synonyms.append(genus2)
        self.session.commit()
        self.session.delete(genus2)
        self.session.commit()
        self.assert_(self.session.query(GenusSynonym).count() == 0)

        # test that deleting the previous synonyms didn't delete the
        # genus that it refered to
        self.assert_(self.session.query(Genus).get(genus.id))

        # test that deleting a genus that has synonyms deletes all
        # the synonyms that refer to that genus
        genus2 = Genus(family=family, genus=u'genus2')
        self.session.add(genus2)
        genus.synonyms.append(genus2)
        self.session.commit()
        self.session.delete(genus)
        self.session.commit()
        self.assert_(self.session.query(GenusSynonym).count() == 0)


    def test_contraints(self):
        """
        Test that the genus constraints were created correctly
        """
        family = Family(family=u'family')
        self.session.add(family)

        # if any of these values are inserted twice they should raise
        # an IntegrityError because the UniqueConstraint on Genus
        values = [dict(family=family, genus=u'genus'),
                  dict(family=family, genus=u'genus', author=u'author'),
                  dict(family=family, genus=u'genus', qualifier=u's. lat.'),
                  dict(family=family, genus=u'genus', qualifier=u's. lat.',
                       author=u'author')
                  ]
        for v in values:
            self.session.add(Genus(**v))
            self.session.add(Genus(**v))
            self.assertRaises(IntegrityError, self.session.commit)
            self.session.rollback()


    def test_str(self):
        """
        Test that the Genus string functions works as expected
        """
        pass


    def itest_editor(self):
        """
        Interactively test the PlantEditor
        """
        #loc = self.create(Genus, name=u'some site')
        fam = Family(family=u'family')
        fam2 = Family(family=u'family2')
        fam2.synonyms.append(fam)
        self.session.add_all([fam, fam2])
        self.session.commit()
        gen = Genus(genus='some genus')
        editor = GenusEditor(model=gen)
        editor.start()
        del editor
        assert utils.gc_objects_by_type('GenusEditor') == [], \
            'GenusEditor not deleted'
        assert utils.gc_objects_by_type('GenusEditorPresenter') == [], \
            'GenusEditorPresenter not deleted'
        assert utils.gc_objects_by_type('GenusEditorView') == [], \
            'GenusEditorView not deleted'


class SpeciesTests(PlantTestCase):

    def setUp(self):
        super(SpeciesTests, self).setUp()

    def tearDown(self):
        super(SpeciesTests, self).tearDown()


    def itest_editor(self):
        # import default geography data
        import bauble.paths as paths
        default_path = os.path.join(paths.lib_dir(), "plugins", "plants",
                                "default")
        filenames = [os.path.join(default_path, f) for f in 'geography.txt',
                     'habit.txt']
        from bauble.plugins.imex.csv_ import CSVImporter
        importer = CSVImporter()
        importer.start(filenames, force=True)

        f = Family(family=u'family')
        g2 = Genus(genus=u'genus2', family=f)
        g = Genus(genus=u'genus', family=f)
        g2.synonyms.append(g)
        self.session.add(f)
        self.session.commit()
        sp = Species(genus=g, sp=u'sp')
        e = SpeciesEditor(model=sp)
        e.start()
        del e
        assert utils.gc_objects_by_type('SpeciesEditor') == [], \
            'SpeciesEditor not deleted'
        assert utils.gc_objects_by_type('SpeciesEditorPresenter') == [], \
            'SpeciesEditorPresenter not deleted'
        assert utils.gc_objects_by_type('SpeciesEditorView') == [], \
            'SpeciesEditorView not deleted'

    def test_str(self):
        """
        Test the Species.str() method
        """
        def get_sp_str(id, **kwargs):
            return Species.str(self.session.query(Species).get(id), **kwargs)

        for sid, s in species_str_map.iteritems():
                sp = self.session.query(Species).get(sid)
                spstr = get_sp_str(sid)
                self.assert_(spstr == s,
                             '"%s" != "%s" ** %s' % (spstr, s, unicode(spstr)))

        for sid, s in species_str_authors_map.iteritems():
            spstr = get_sp_str(sid, authors=True)
            self.assert_(spstr == s,
                         '%s != %s ** %s' % (spstr, s, unicode(spstr)))

        for sid, s in species_markup_map.iteritems():
            spstr = get_sp_str(sid, markup=True)
            self.assert_(spstr == s,
                         '%s != %s ** %s' % (spstr, s, unicode(spstr)))

        for sid, s in species_markup_authors_map.iteritems():
            spstr = get_sp_str(sid, markup=True, authors=True)
            self.assert_(spstr == s,
                         '%s != %s ** %s' % (spstr, s, unicode(spstr)))


    # def test_dirty_string(self):
    #     """
    #     That that the cache on a string is invalidated if the species
    #     is changed or expired.
    #     """
    #     family = Family(family=u'family')
    #     genus = Genus(family=family, genus=u'genus')
    #     sp = Species(genus=genus, sp=u'sp')
    #     self.session.add_all([family, genus, sp])
    #     self.session.commit()

    #     str1 = Species.str(sp)
    #     sp.sp = u'sp2'
    #     self.session.commit()
    #     self.session.refresh(sp)
    #     sp = self.session.query(Species).get(sp.id)
    #     self.assert_(Species.str(sp) != str1)


    def test_vernacular_name(self):
        """
        Test the Species.vernacular_name property
        """
        family = Family(family=u'family')
        genus = Genus(family=family, genus=u'genus')
        sp = Species(genus=genus, sp=u'sp')
        self.session.add_all([family, genus, sp])
        self.session.commit()

        # add a name
        vn = VernacularName(name=u'name')
        sp.vernacular_names.append(vn)
        self.session.commit()
        self.assert_(vn in sp.vernacular_names)

        # test that removing a name removes deleted orphaned objects
        sp.vernacular_names.remove(vn)
        self.session.commit()
        q = self.session.query(VernacularName).filter_by(species_id=sp.id)
        self.assertRaises(NoResultFound, q.one)


    def test_default_vernacular_name(self):
        """
        Test the Species.default_vernacular_name property
        """
        family = Family(family=u'family')
        genus = Genus(family=family, genus=u'genus')
        sp = Species(genus=genus, sp=u'sp')
        vn = VernacularName(name=u'name')
        sp.vernacular_names.append(vn)
        self.session.add_all([family, genus, sp, vn])
        self.session.commit()

        # test that setting the default vernacular names
        default = VernacularName(name=u'default')
        sp.default_vernacular_name = default
        self.session.commit()
        self.assert_(vn in sp.vernacular_names)
        self.assert_(sp.default_vernacular_name == default)

        # test that set_attr work on default vernacular name
        default = VernacularName(name=u'default')
        setattr(sp, 'default_vernacular_name', default)
        self.session.commit()
        self.assert_(vn in sp.vernacular_names)
        self.assert_(sp.default_vernacular_name == default)

        # test that if you set the default_vernacular_name on a
        # species then it automatically adds it to vernacular_names
        default = VernacularName(name=u'default')
        sp.default_vernacular_name = default
        self.session.commit()
        self.assert_(vn in sp.vernacular_names)
        self.assert_(sp.default_vernacular_name == default)


        # test that removing a vernacular name removes it from
        # default_vernacular_name, this test also effectively tests VNList
        dvid = sp._default_vernacular_name.id
        sp.vernacular_names.remove(default)
        self.session.commit()
        self.assertEquals(sp.default_vernacular_name, None)
        q = self.session.query(DefaultVernacularName)
        self.assertRaises(NoResultFound, q.filter_by(species_id=sp.id).one)
        self.assertRaises(NoResultFound, q.filter_by(id=dvid).one)

        # test that setting default_vernacular_name to None
        # removes the name properly and deletes any orphaned objects
        sp.vernacular_names.append(vn)
        sp.default_vernacular_name = vn
        self.session.commit()
        dvid = sp._default_vernacular_name.id
        sp.default_vernacular_name = None
        self.session.commit()
        q = self.session.query(DefaultVernacularName)
        self.assertRaises(NoResultFound, q.filter_by(species_id=sp.id).one)
        self.assertRaises(NoResultFound, q.filter_by(id=dvid).one)

        # test that calling __del__ on a default vernacular name removes it
        sp.default_vernacular_name = vn
        self.session.commit()
        dvid = sp._default_vernacular_name.id
        del sp.default_vernacular_name
        self.session.commit()
        self.assertEquals(sp.default_vernacular_name, None)
        q = self.session.query(DefaultVernacularName)
        self.assertRaises(NoResultFound, q.filter_by(species_id=sp.id).one)
        self.assertRaises(NoResultFound, q.filter_by(id=dvid).one)

        # test for regression in bug Launchpad #123286
        vn1 = VernacularName(name=u'vn1')
        vn2 = VernacularName(name=u'vn2')
        sp.default_vernacular_name = vn1
        sp.default_vernacular_name = vn2
        self.session.commit()


    def test_synonyms(self):
        """
        Test the Species.synonyms property
        """
        load_sp = lambda id: self.session.query(Species).get(id)

        def syn_str(id1, id2, isit='not'):
            sp1 = load_sp(id1)
            sp2 = load_sp(id2)
            return '%s(%s).synonyms: %s' % \
                   (sp1, sp1.id,
                    str(map(lambda s: '%s(%s)' % \
                            (s, s.id), sp1.synonyms)))

        def synonym_of(id1, id2):
            sp1 = load_sp(id1)
            sp2 = load_sp(id2)
            return sp2 in sp1.synonyms

        # test that appending a synonym works using species.synonyms
        sp1 = load_sp(1)
        sp2 = load_sp(2)
        sp1.synonyms.append(sp2)
        self.session.flush()
        self.assert_(synonym_of(1, 2), syn_str(1, 2))

        # test that removing a synonyms works using species.synonyms
        sp1.synonyms.remove(sp2)
        self.session.flush()
        self.failIf(synonym_of(1, 2), syn_str(1, 2))

        self.session.expunge_all()

        # test that appending a synonym works using species._synonyms
        sp1 = load_sp(1)
        sp2 = load_sp(2)
        syn = SpeciesSynonym(sp2)
        sp1._synonyms.append(syn)
        self.session.flush()
        self.assert_(synonym_of(1, 2), syn_str(1, 2))

        # test that removing a synonyms works using species._synonyms
        sp1._synonyms.remove(syn)
        self.session.flush()
        self.failIf(synonym_of(1, 2), syn_str(1, 2))

        # test adding a species and then immediately remove it
        self.session.expunge_all()
        sp1 = load_sp(1)
        sp2 = load_sp(2)
        sp1.synonyms.append(sp2)
        sp1.synonyms.remove(sp2)
        #self.session.flush()
        self.session.commit()
        assert sp2 not in sp1.synonyms

        # add a species and immediately add the same species
        sp2 = load_sp(2)
        sp1.synonyms.append(sp2)
        sp1.synonyms.remove(sp2)
        sp1.synonyms.append(sp2)
        #self.session.flush() # shouldn't raise an error
        self.session.commit()
        assert sp2 in sp1.synonyms

        # test that deleting a species removes it from the synonyms list
        assert sp2 in sp1.synonyms
        self.session.delete(sp2)
        self.session.commit()
        assert sp2 not in sp1.synonyms

        self.session.expunge_all()


class GeographyTests(PlantTestCase):

    def __init__(self, *args):
        super(GeographyTests, self).__init__(*args)

    def setUp(self):
        super(GeographyTests, self).setUp()
        self.family = Family(family=u'family')
        self.genus = Genus(genus=u'genus', family=self.family)
        self.session.add_all([self.family, self.genus])
        self.session.commit()


    def tearDown(self):
        super(GeographyTests, self).tearDown()


    def test_get_species(self):
        # import default geography data
        import bauble.paths as paths
        filename = os.path.join(paths.lib_dir(), "plugins", "plants",
                                "default", 'geography.txt')
        from bauble.plugins.imex.csv_ import CSVImporter
        importer = CSVImporter()
        importer.start([filename], force=True)

        mexico_id = 53
        mexico_central_id = 267
        oaxaca_id = 665
        northern_america_id = 7
        western_canada_id = 45

        # create a some species
        sp1 = Species(genus=self.genus, sp=u'sp1')
        dist = SpeciesDistribution(geography_id=mexico_central_id)
        sp1.distribution.append(dist)

        sp2 = Species(genus=self.genus, sp=u'sp2')
        dist = SpeciesDistribution(geography_id=oaxaca_id)
        sp2.distribution.append(dist)

        sp3 = Species(genus=self.genus, sp=u'sp3')
        dist = SpeciesDistribution(geography_id=western_canada_id)
        sp3.distribution.append(dist)

        self.session.commit()

        oaxaca = self.session.query(Geography).get(oaxaca_id)
        species = get_species_in_geography(oaxaca)
        self.assert_([s.id for s in species] == [sp2.id])

        mexico = self.session.query(Geography).get(mexico_id)
        species = get_species_in_geography(mexico)
        self.assert_([s.id for s in species] == [sp1.id, sp2.id])

        north_america = self.session.query(Geography).get(northern_america_id)
        species = get_species_in_geography(north_america)
        self.assert_([s.id for s in species] == [sp1.id, sp2.id, sp3.id])


# TODO: maybe the following could be in a seperate file called
# profile.py or something that would profile everything in the plants
# module

#def main():
#    from optparse import OptionParser
#    parser = OptionParser()
#    parser.add_option('-v', '--verbose', dest='verbose', action='store_true',
#                      help='verbose output')
#    parser.add_option('-p', '--profile', dest='profile', action='store_true',
#                      help='print run times')
#    options, args = parser.parse_args()
#
#    import profile
#    import time
#    if options.profile:
#        t1 = time.time()
#        #profile.run('test_speciesStr()')
#        profile.run('profile()')
#        t2 = time.time()
#        print 'time: %s' % (t2-t1)
#    else:
#        print 'starting tests...'
#        test_speciesStr(options.verbose)
#        print 'done.'
#
#
#if __name__ == '__main__':
#    main()
