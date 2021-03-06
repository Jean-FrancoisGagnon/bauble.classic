#
# species_model.py
#

import traceback
import xml.sax.saxutils as sax
from itertools import chain

import gtk
from sqlalchemy import *
from sqlalchemy.orm import *
from sqlalchemy.orm.session import object_session
from sqlalchemy.ext.associationproxy import association_proxy

import bauble
import bauble.db as db
import bauble.utils as utils
from bauble.utils.log import debug
import bauble.btypes as types
from bauble.plugins.plants.geography import Geography#, geography_table

from sqlalchemy.orm.collections import collection


class VNList(list):
    """
    A Collection class for Species.vernacular_names

    This makes it possible to automatically remove a
    default_vernacular_name if the vernacular_name is removed from the
    list.
    """
    def remove(self, vn):
        super(VNList, self).remove(vn)
        try:
            if vn.species.default_vernacular_name == vn:
                del vn.species.default_vernacular_name
        except Exception, e:
            debug(e)


infrasp_rank_values = {u'subsp.': _('subsp.'),
                       u'var.': _('var.'),
                       u'subvar.': _('subvar'),
                       u'f.': _('f.'),
                       u'subf.': _('subf.'),
                       u'cv.': _('cv.'),
                       None: ''}



# TODO: there is a trade_name column but there's no support yet for editing
# the trade_name or for using the trade_name when building the string
# for the species, for more information about trade_names see,
# http://www.hortax.org.uk/gardenplantsnames.html

# TODO: the specific epithet should not be non-nullable but instead
# make sure that at least one of the specific epithet, cultivar name
# or cultivar group is specificed

class Species(db.Base):
    """
    :Table name: species

    :Columns:
        *sp*:
        *sp2*:
        *sp_author*:

        *hybrid*:
            Hybrid flag

        *infrasp1*:
        *infrasp1_rank*:
        *infrasp1_author*:

        *infrasp2*:
        *infrasp2_rank*:
        *infrasp2_author*:

        *infrasp3*:
        *infrasp3_rank*:
        *infrasp3_author*:

        *infrasp4*:
        *infrasp4_rank*:
        *infrasp4_author*:

        *cv_group*:
        *trade_name*:

        *sp_qual*:
            Species qualifier

            Possible values:
                *agg.*: An aggregate species

                *s. lat.*: aggregrate species (sensu lato)

                *s. str.*: segregate species (sensu stricto)

        *label_distribution*:
            UnicodeText
            This field is optional and can be used for the label in case
            str(self.distribution) is too long to fit on the label.

    :Properties:
        *accessions*:

        *vernacular_names*:

        *default_vernacular_name*:

        *synonyms*:

        *distribution*:

    :Constraints:
        The combination of sp, sp_author, hybrid, sp_qual,
        cv_group, trade_name, genus_id
    """
    __tablename__ = 'species'
    __mapper_args__ = {'order_by': ['sp', 'sp_author']}


    # columns
    sp = Column(Unicode(64), index=True)
    sp2 = Column(Unicode(64), index=True) # in case hybrid=True
    sp_author = Column(Unicode(128))
    hybrid = Column(Boolean, default=False)
    sp_qual = Column(types.Enum(values=['agg.', 's. lat.', 's. str.', None]),
                     default=None)
    cv_group = Column(Unicode(50))
    trade_name = Column(Unicode(64))

    infrasp1 = Column(Unicode(64))
    infrasp1_rank = Column(types.Enum(values=infrasp_rank_values.keys(),
                                      translations=infrasp_rank_values))
    infrasp1_author = Column(Unicode(64))

    infrasp2 = Column(Unicode(64))
    infrasp2_rank = Column(types.Enum(values=infrasp_rank_values.keys(),
                                      translations=infrasp_rank_values))
    infrasp2_author = Column(Unicode(64))

    infrasp3 = Column(Unicode(64))
    infrasp3_rank = Column(types.Enum(values=infrasp_rank_values.keys(),
                                      translations=infrasp_rank_values))
    infrasp3_author = Column(Unicode(64))

    infrasp4 = Column(Unicode(64))
    infrasp4_rank = Column(types.Enum(values=infrasp_rank_values.keys(),
                                      translations=infrasp_rank_values))
    infrasp4_author = Column(Unicode(64))

    genus_id = Column(Integer, ForeignKey('genus.id'), nullable=False)

    label_distribution = Column(UnicodeText)
    bc_distribution = Column(UnicodeText)

    # relations
    synonyms = association_proxy('_synonyms', 'synonym')
    _synonyms = relation('SpeciesSynonym',
                         primaryjoin='Species.id==SpeciesSynonym.species_id',
                         cascade='all, delete-orphan', uselist=True,
                         backref='species')

    # this is a dummy relation, it is only here to make cascading work
    # correctly and to ensure that all synonyms related to this genus
    # get deleted if this genus gets deleted
    _syn = relation('SpeciesSynonym',
                     primaryjoin='Species.id==SpeciesSynonym.synonym_id',
                     cascade='all, delete-orphan', uselist=True)

    vernacular_names = relation('VernacularName', cascade='all, delete-orphan',
                                 collection_class=VNList,
                                backref=backref('species', uselist=False))
    _default_vernacular_name = relation('DefaultVernacularName', uselist=False,
                                         cascade='all, delete-orphan',
                                         backref=backref('species',
                                                         uselist=False))
    distribution = relation('SpeciesDistribution',
                            cascade='all, delete-orphan',
                            backref=backref('species', uselist=False))

    habit_id = Column(Integer, ForeignKey('habit.id'), default=None)
    habit = relation('Habit', uselist=False, backref='species')

    flower_color_id = Column(Integer, ForeignKey('color.id'), default=None)
    flower_color = relation('Color', uselist=False, backref='species')

    #hardiness_zone = Column(Unicode(4))

    awards = Column(UnicodeText)

    def __init__(self, *args, **kwargs):
        super(Species, self).__init__(*args, **kwargs)


    def __str__(self):
        '''
        returns a string representation of this species,
        calls Species.str(self)
        '''
        return Species.str(self)


    def _get_default_vernacular_name(self):
        if self._default_vernacular_name is None:
            return None
        return self._default_vernacular_name.vernacular_name
    def _set_default_vernacular_name(self, vn):
        if vn is None:
            del self.default_vernacular_name
            return
        if vn not in self.vernacular_names:
            self.vernacular_names.append(vn)
        d = DefaultVernacularName()
        d.vernacular_name = vn
        self._default_vernacular_name = d
    def _del_default_vernacular_name(self):
        utils.delete_or_expunge(self._default_vernacular_name)
        del self._default_vernacular_name
    default_vernacular_name = property(_get_default_vernacular_name,
                                       _set_default_vernacular_name,
                                       _del_default_vernacular_name)

    def distribution_str(self):
        if self.distribution is None:
            return ''
        else:
            dist = ['%s' % d for d in self.distribution]
            return unicode(', ').join(sorted(dist))


    def markup(self, authors=False):
        '''
        returns this object as a string with markup

        :param authors: flag to toggle whethe the author names should be
        included
        '''
        return Species.str(self, authors, True)


    # in PlantPlugins.init() we set this to 'x' for win32
    hybrid_char = utils.utf8(u'\u2a09') # U+2A09

    @staticmethod
    def str(species, authors=False, markup=False):
        '''
        returns a string for species

        :param species: the species object to get the values from
        :param authors: flags to toggle whether the author names should be
        included
        :param markup: flags to toggle whether the returned text is marked up
        to show italics on the epithets
        '''
        # TODO: this method will raise an error if the session is none
        # since it won't be able to look up the genus....we could
        # probably try to query the genus directly with the genus_id
        genus = str(species.genus)
        sp = species.sp
        sp2 = species.sp2
        if markup:
            escape = utils.xml_safe_utf8
            italicize = lambda s: u'<i>%s</i>' % escape(s)
            genus = italicize(genus)
            if sp is not None:
                sp = italicize(species.sp)
            if sp2 is not None:
                sp2 = italicize(species.sp2)
        else:
            italicize = lambda s: u'%s' % s
            escape = lambda x: x

        author = None
        if authors and species.sp_author:
            author = escape(species.sp_author)

        infrasp = ((species.infrasp1_rank, species.infrasp1,
                    species.infrasp1_author),
                   (species.infrasp2_rank, species.infrasp2,
                    species.infrasp2_author),
                   (species.infrasp3_rank, species.infrasp3,
                    species.infrasp3_author),
                   (species.infrasp4_rank, species.infrasp4,
                    species.infrasp4_author))

        infrasp_parts = []
        group_added = False
        for rank, epithet, iauthor in infrasp:
            if rank == 'cv.' and epithet:
                if species.cv_group and not group_added:
                    group_added = True
                    infrasp_parts.append(_("(%(group)s Group)") % \
                                             dict(group=species.cv_group))
                infrasp_parts.append("'%s'" % escape(epithet))
            else:
                if rank:
                    infrasp_parts.append(rank)
                if epithet and rank:
                    infrasp_parts.append(italicize(epithet))
                elif epithet:
                    infrasp_parts.append(escape(epithet))

            if authors and iauthor:
                infrasp_parts.append(escape(iauthor))
        if species.cv_group and not group_added:
            infrasp_parts.append(_("%(group)s Group") % \
                                     dict(group=species.cv_group))

        # create the binomial part
        binomial = []
        if species.hybrid:
            if species.sp2:
                binomial = [genus, sp, species.hybrid_char, sp2, author]
            else:
                binomial = [genus, species.hybrid_char, sp, author]
        else:
            binomial = [genus, sp, sp2, author]

        # create the tail a.k.a think to add on to the end
        tail = []
        if species.sp_qual:
            tail = [species.sp_qual]

        parts = chain(binomial, infrasp_parts, tail)
        s = utils.utf8(' '.join(filter(lambda x: x not in ('', None), parts)))
        return s


    infrasp_attr = {1: {'rank': 'infrasp1_rank',
                        'epithet': 'infrasp1',
                        'author': 'infrasp1_author'},
                    2: {'rank': 'infrasp2_rank',
                        'epithet': 'infrasp2',
                        'author': 'infrasp2_author'},
                    3: {'rank': 'infrasp3_rank',
                        'epithet': 'infrasp3',
                        'author': 'infrasp3_author'},
                    4: {'rank': 'infrasp4_rank',
                        'epithet': 'infrasp4',
                        'author': 'infrasp4_author'}}


    def get_infrasp(self, level):
        """
        level should be 1-4
        """
        return getattr(self, self.infrasp_attr[level]['rank']), \
            getattr(self, self.infrasp_attr[level]['epithet']), \
            getattr(self, self.infrasp_attr[level]['author'])


    def set_infrasp(self, level, rank, epithet, author=None):
        """
        level should be 1-4
        """
        setattr(self, self.infrasp_attr[level]['rank'], rank)
        setattr(self, self.infrasp_attr[level]['epithet'], epithet)
        setattr(self, self.infrasp_attr[level]['author'], author)



class SpeciesNote(db.Base):
    """
    Notes for the species table
    """
    __tablename__ = 'species_note'
    __mapper_args__ = {'order_by': 'species_note.date'}

    date = Column(types.Date, default=func.now())
    user = Column(Unicode(64))
    category = Column(Unicode(32))
    note = Column(UnicodeText, nullable=False)
    species_id = Column(Integer, ForeignKey('species.id'), nullable=False)
    species = relation('Species', uselist=False,
                       backref=backref('notes', cascade='all, delete-orphan'))



class SpeciesSynonym(db.Base):
    """
    :Table name: species_synonym
    """
    __tablename__ = 'species_synonym'

    # columns
    species_id = Column(Integer, ForeignKey('species.id'),
                        nullable=False)
    synonym_id = Column(Integer, ForeignKey('species.id'),
                        nullable=False, unique=True)

    # relations
    synonym = relation('Species', uselist=False,
                       primaryjoin='SpeciesSynonym.synonym_id==Species.id')

    def __init__(self, synonym=None, **kwargs):
        # it is necessary that the first argument here be synonym for
        # the Species.synonyms association_proxy to work
        self.synonym = synonym
        super(SpeciesSynonym, self).__init__(**kwargs)

    def __str__(self):
        return str(self.synonym)



class VernacularName(db.Base):
    """
    :Table name: vernacular_name

    :Columns:
        *name*:
            the vernacular name

        *language*:
            language is free text and could include something like UK
            or US to identify the origin of the name

        *species_id*:
            key to the species this vernacular name refers to

    :Properties:

    :Constraints:
    """
    __tablename__ = 'vernacular_name'
    name = Column(Unicode(128), nullable=False)
    language = Column(Unicode(128))
    species_id = Column(Integer, ForeignKey('species.id'), nullable=False)
    __table_args__ = (UniqueConstraint('name', 'language',
                                       'species_id', name='vn_index'), {})

    def __str__(self):
        if self.name:
            return self.name
        else:
            return ''



class DefaultVernacularName(db.Base):
    """
    :Table name: default_vernacular_name

    DefaultVernacularName is not meant to be instantiated directly.
    Usually the default vernacular name is set on a species by setting
    the default_vernacular_name property on Species to a
    VernacularName instance

    :Columns:
        *id*:
            Integer, primary_key

        *species_id*:
            foreign key to species.id, nullable=False

        *vernacular_name_id*:

    :Properties:

    :Constraints:
    """
    __tablename__ = 'default_vernacular_name'
    __table_args__ = (UniqueConstraint('species_id', 'vernacular_name_id',
                                       name='default_vn_index'), {})

    # columns
    species_id = Column(Integer, ForeignKey('species.id'), nullable=False)
    vernacular_name_id = Column(Integer, ForeignKey('vernacular_name.id'),
                                nullable=False)

    # relations
    vernacular_name = relation(VernacularName, uselist=False)

    def __str__(self):
        return str(self.vernacular_name)


class SpeciesDistribution(db.Base):
    """
    :Table name: species_distribution

    :Columns:

    :Properties:

    :Constraints:
    """
    __tablename__ = 'species_distribution'

    # columns
    geography_id = Column(Integer, ForeignKey('geography.id'), nullable=False)
    species_id = Column(Integer, ForeignKey('species.id'), nullable=False)

    def __str__(self):
        return str(self.geography)

# late bindings
SpeciesDistribution.geography = relation('Geography',
                primaryjoin='SpeciesDistribution.geography_id==Geography.id',
                                         uselist=False)

class Habit(db.Base):
    __tablename__ = 'habit'

    name = Column(Unicode(64))
    code = Column(Unicode(8), unique=True)

    def __str__(self):
        if self.name:
            return '%s (%s)' % (self.name, self.code)
        else:
            return str(self.code)


class Color(db.Base):
    __tablename__ = 'color'

    name = Column(Unicode(32))
    code = Column(Unicode(8), unique=True)

    def __str__(self):
        if self.name:
            return '%s (%s)' % (self.name, self.code)
        else:
            return str(self.code)

