#!/usr/bin/env python
#
# Copyright (C) 2016 Yann Diorcet
#
# This file is part of IDS.  IDS is free software: you can
# redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation, version 2.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 51
# Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#

"""Utilities for working with Mazda IDS XML data."""

__author__ = "Yann Diorcet"
__license__ = "GPL"
__version__ = "0.0.1"

try:
    import lxml.etree as ET
except ImportError:
    import xml.etree.ElementTree as ET
import os
import sys
import argparse
import itertools
import io
import termcolor
import re

try:
    from peak.util.proxies import ObjectWrapper
except ImportError:
    from objproxies import ObjectWrapper


class IDSQualifier(object):
    """Qualifiers attach additional values to IDS objects."""
    @classmethod
    def parse(cls, elem):
        id = elem.attrib['m']
        description = elem.attrib['v']
        return IDSQualifier(id, description)

    def __init__(self, id, description):
        self.__id = id
        self.__values = {}
        self.__description = description

    def id(self):
        return self.__id

    def description(self):
        return self.__description

    def values(self):
        return self.__values


# IDS Objects

class IDSXMLFile(object):
    """Representation of an XML file entry declared in the IDS metadata."""
    @classmethod
    def parse(cls, elem):
        name = elem.attrib['xmlType']
        filename = elem.attrib['xmlName']
        tsb = True if elem.attrib['TSBOnly'] != 'No' else False
        return IDSXMLFile(name, filename, tsb)

    def __init__(self, name, filename, tsb):
        super(IDSXMLFile, self).__init__()
        self.__name = name
        self.__filename = filename
        self.__tsb = tsb

    def id(self):
        return self.__name

    def name(self):
        return self.__name

    def filename(self):
        return self.__filename

    def tsb(self):
        return self.__tsb

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.__name == other.__name
        else:
            return False

    def __str__(self):
        return '%s' % (self.id())


class IDSXMLVehicle(object):
    """Vehicle description and associated qualifiers defined in IDS."""
    CODE_REG = re.compile(r'\(([^()]+) ([^()]+)\)')

    def code_key(txt):
        return [x for x, y in IDSXMLVehicle.CODE_REG.findall(txt)]

    def code_value(txt):
        return [y for x, y in IDSXMLVehicle.CODE_REG.findall(txt)]

    XML_MAPPINGS = {
        'CM_PROJECT': 'CM_Project',
        'model': 'CM_MODEL',
        'type': 'CM_ENGINE_TYPE',
        'subtype': 'CM_ENGINE_SUB_TYPE',
        'year': 'CM_YEAR_BREAKPOINT',
        'code': (code_key, code_value),
    }

    @classmethod
    def parse(cls, elem):
        attributes = {}
        for key1, key2 in cls.XML_MAPPINGS.items():
            if key1 in elem.attrib:
                if not isinstance(key2, str):
                    (get_key, get_value) = key2
                    keys = get_key(elem.attrib[key1])
                    values = get_value(elem.attrib[key1])
                else:
                    keys = [key2]
                    values = [elem.attrib[key1]]

                for key, value in zip(keys, values):
                    if key in cls.XML_MAPPINGS:
                        key = cls.XML_MAPPINGS[key]
                    attributes[key] = value
        return IDSXMLVehicle(attributes)

    def __init__(self, qualifiers):
        super(IDSXMLVehicle, self).__init__()
        self.__qualifiers = qualifiers
        self.__files = {}

    def base(self):
        return (
            'CM_BASE' in self.__qualifiers
            and self.__qualifiers['CM_BASE'] == 'BASE'
        )

    def qualifiers(self):
        return self.__qualifiers

    def files(self):
        return self.__files

    def check(self, other):
        for key, value in self.__qualifiers.items():
            if key not in other.qualifiers():
                return False
            if value != 'BASE' and other.qualifiers()[key] != value:
                return False
        return True


class IDSXMLModule(object):
    """IDS module entry grouping vehicles and related data."""
    @classmethod
    def parse(cls, elem):
        name = elem.attrib['dataName']
        return IDSXMLModule(name)

    def __init__(self, name):
        super(IDSXMLModule, self).__init__()
        self.__name = name
        self.__vehicles = []

    def id(self):
        return self.__name

    def name(self):
        return self.__name

    def vehicles(self):
        return self.__vehicles

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.__name == other.__name
        else:
            return False

    def __str__(self):
        return '%s' % (self.id())


class IDSVehicle(object):
    @classmethod
    def parse(cls, elem):
        n = elem.attrib['n']
        s = elem.attrib['s']
        qualifiers = {
            k: elem.attrib[k]
            for k in elem.attrib
            if k not in ('n', 's')
        }
        return IDSVehicle(n, s, qualifiers)

    def __init__(self, n, s, qualifiers):
        super(IDSVehicle, self).__init__()
        self.__n = n
        self.__s = s
        self.__qualifiers = qualifiers
        self.__references = {}
        self.__modules = {}

    def qualifiers(self):
        return self.__qualifiers

    def id(self):
        return IDSKey(self.__n, self.__s)

    def type(self):
        return 'CONFIG_ITEM_REC'

    def __str__(self):
        return '%s' % (self.id())

    def check(self, other):
        for key, value in self.__qualifiers.items():
            if key not in other.qualifiers():
                return False
            if value != 'BASE' and other.qualifiers()[key] != value:
                return False
        return True


class IDSAttribute(object):
    @classmethod
    def parse(cls, elem):
        name = elem.attrib['n']
        type = elem.attrib['t']
        array = True if elem.attrib['a'] == "1" else False
        return IDSAttribute(name, type, array)

    def __init__(self, name, type, array):
        super(IDSAttribute, self).__init__()
        self.__name = name
        self.__type = type
        self.__array = array

    def name(self):
        return self.__name

    def type(self):
        if self.__name == "filename":
            return 'CALID_VIDQID_REC'
        return self.__type

    def function(self, value):
        if self.__name == "filename":
            return 'FILE_%s' % (value)
        return value

    def array(self):
        return self.__array


class IDSType(object):
    @classmethod
    def parse(cls, elem):
        name = elem.attrib['t']
        return IDSType(name)

    def __init__(self, name):
        super(IDSType, self).__init__()
        self.__name = name
        self.__attributes = {}

    def name(self):
        return self.__name

    def attributes(self):
        return self.__attributes


class IDSKey(object):
    STRING_KEY = re.compile(r'\[(.*)\]\[(.*)\]')

    def __init__(self, a, b=None):
        super(IDSKey, self).__init__()
        if a and not b:
            match = self.STRING_KEY.match(a)
            if match:
                (a, b) = match.group(1, 2)
        self.__a = a
        self.__b = b
        if self.__a == self.__b:
            self.__b = None
        if self.__b and len(self.__b) == 0:
            self.__b = None

    def a(self):
        return self.__a

    def b(self):
        return self.__b

    def get_in(self, dic):
        return [dic[other] for other in dic if other == self]

    def __repr__(self):
        if not self.__b:
            return self.__a
        return '%s|%s' % (self.__a, self.__b)

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            if self.__b and other.__b:
                return self.__a == other.__a and self.__b == other.__b
            else:
                return self.__a == other.__a
        else:
            return False

    def __hash__(self):
        return hash(self.__a) ^ hash(self.__b)


class IDSObject(object):
    @classmethod
    def parse(cls, type, elem):
        d = elem.attrib['d']
        i = elem.attrib['i']
        attributes = {}
        for key in elem.attrib:
            if key.startswith('a'):
                attributes[int(key[1:])] = elem.attrib[key]
        return IDSObject(type, d, i, attributes)

    def __init__(self, type, d, i, attributes):
        super(IDSObject, self).__init__()
        self.__type = type
        self.__d = d
        self.__i = i
        self.__attributes = attributes
        self.__qualifications = []

    def type(self):
        return self.__type

    def id(self):
        return IDSKey(self.__d, self.__i)

    def qualifications(self):
        return self.__qualifications

    def parse_attribute(self, element, value):
        key = element.attrib['f']
        if key.startswith('s'):
            self.__attributes[int(key[1:])] = value
        else:
            raise ValueError("Invalid element name %s" % (key))

    def attributes(self):
        return self.__attributes

    def __str__(self):
        return '%s' % (self.id())


class Mnemonic(object):
    @classmethod
    def parse(cls, elem):
        m = elem.attrib['m']
        v = elem.attrib['v']
        f = elem.attrib['f']
        return Mnemonic(m, v, f)

    def __init__(self, key, value, f):
        super(Mnemonic, self).__init__()
        self.__key = key
        self.__value = value
        self.__f = f

    def key(self):
        return self.__key

    def value(self):
        return self.__value

    def f(self):
        return self.__f

    def __str__(self):
        return '%s' % (self.__value)


# XML

class XMLIO(ObjectWrapper):
    XML_ILLEGAL = [
        chr(a)
        for a in itertools.chain(
            itertools.chain(range(0x0, 0x09), range(0xb, 0xd)),
            range(0xe, 0x20),
        )
    ]
    __proxy = None

    def __init__(self, ob, encoding='utf-8'):
        super(XMLIO, self).__init__(ob)
        self.__proxy = ob
        self.__encoding = encoding

    def read(self, size):
        data = self.__proxy.read(size)
        for a in self.XML_ILLEGAL:
            data = data.replace(a, '?')
        return data.encode(self.__encoding)


def print_error(txt):
    print(termcolor.colored(txt, 'red'), file=sys.stderr)


def print_xml_error(txt, elem):
    err = ET.tostring(elem, encoding='utf-8').decode('utf-8').strip()
    print_error("%s %s" % (txt, err))


def open_xml(filename, encoding='iso-8859-1'):
    return io.open(filename, 'r', encoding=encoding)


def iterparse(file, encoding='utf-8', wrapper=True, recover=True):
    if wrapper:
        source = XMLIO(file, encoding=encoding)
    else:
        source = file
    # return ET.iterparse(
    #     source,
    #     events=('start', 'end'),
    #     parser=ET.XMLParser(target=ET.TreeBuilder(), encoding='utf-8'),
    # )
    return ET.iterparse(
        source,
        events=('start', 'end'),
        encoding=encoding,
        recover=recover,
    )


class IDSContext(object):
    """High level access to IDS data stored in a directory tree."""
    def __init__(self, context):
        super(IDSContext, self).__init__()

        self.__cache = {}
        self.__datatypes = None
        self.__mnemonics = None
        self.__vehicles = None
        self.__qualifiers = None
        self.__modules = None
        self.__texts = None
        self.__context = context

    def datatypes(self):
        """Return the list of datatypes defined in the IDS dataset."""
        if not self.__datatypes:
            self.__datatypes = {}
            data_dir = os.path.join(self.__context.root, 'Data')
            datatypes_file = os.path.join(data_dir, 'DataTypes.xml')
            if not os.path.isfile(datatypes_file):
                msg = "DataTypes.xml file not found %s" % datatypes_file
                raise ValueError(msg)

            i = 0
            with open_xml(datatypes_file) as file:
                for event, elem in iterparse(file):
                    if event == 'start':
                        if elem.tag == 'm':
                            j = 0
                            attributes = {}
                    elif event == 'end':
                        if elem.tag == 'a':
                            attribute = IDSAttribute.parse(elem)
                            attributes[j] = attribute
                            j += 1
                        elif elem.tag == 'm':
                            type = IDSType.parse(elem)
                            type.attributes().update(attributes)
                            self.__datatypes[i] = type
                            i += 1

        return self.__datatypes

    def datatypes_by_name(self):
        return dict((data.name(), data) for data in self.datatypes().values())

    def _load_values(self, name, create_obj):
        """Load object values from the corresponding XML file."""
        records = {}
        cs_file = os.path.join(
            os.path.join(self.__context.root, 'Data'),
            'values_%s.xml' % name,
        )
        if not os.path.isfile(cs_file):
            msg = "values_%s.xml file not found %s" % (name, cs_file)
            print_error(msg)
            return records

        with open_xml(cs_file) as file:
            for event, elem in iterparse(file):
                if event == 'end' and elem.tag == 'm':
                    try:
                        value = create_obj(name, elem)
                        d = elem.attrib['d']
                        i = elem.attrib['i']
                        records[IDSKey(d, i)] = value
                    except KeyError:
                        print_xml_error("Issue parsing", elem)
        return records

    def _load_arrays(self, name, set_array, records):
        """Populate array values for records."""
        cs_file = os.path.join(
            os.path.join(self.__context.root, 'Data'),
            'Arrays_%s.xml' % name,
        )
        if not os.path.isfile(cs_file):
            return

        with open_xml(cs_file) as file:
            for event, elem in iterparse(file):
                if event == 'start':
                    if elem.tag == 'z':
                        values = []
                    elif elem.tag == 'a':
                        f = elem
                elif event == 'end':
                    if elem.tag == 'm':
                        try:
                            value = elem.attrib['e']
                            values.append(value)
                        except KeyError:
                            print_xml_error("Issue parsing", elem)
                    elif elem.tag == 'z':
                        try:
                            d = elem.attrib['d']
                            n = elem.attrib['n']
                            set_array(records[IDSKey(d, n)], f, values)
                        except KeyError:
                            print_xml_error("Issue parsing", elem)

    def _load_qualifications(self, name, set_qualifications, records):
        """Attach qualifications to existing records."""
        cs_file = os.path.join(
            os.path.join(self.__context.root, 'Data'),
            'Qualifications_QT_%s.xml' % name,
        )
        if not os.path.isfile(cs_file):
            return

        with open_xml(cs_file) as file:
            for event, elem in iterparse(file):
                if event == 'start':
                    if elem.tag == 'm':
                        d = elem.attrib['d']
                    elif elem.tag == 'n':
                        n = elem.attrib['n']
                        values = []
                elif event == 'end':
                    if elem.tag == 'c':
                        try:
                            value = elem.attrib['c']
                            values.append(value)
                        except KeyError:
                            print_xml_error("Issue parsing", elem)
                    elif elem.tag == 'n':
                        try:
                            key = IDSKey(d, n)
                            set_qualifications(records[key], values)
                        except KeyError:
                            print_xml_error("Issue parsing", elem)

    def _load_rec(self, name, create_obj, set_array, set_qualifications):
        records = self._load_values(name, create_obj)
        self._load_arrays(name, set_array, records)
        self._load_qualifications(name, set_qualifications, records)
        return records

    def load_rec(self, name):
        if name == 'CONFIG_ITEM_REC':
            return self.vehicles()

        if name not in self.__cache:
            def set_qualifications(parent, qualifications):
                parent.qualifications().extend(qualifications)

            self.__cache[name] = self._load_rec(
                name,
                IDSObject.parse,
                IDSObject.parse_attribute,
                set_qualifications,
            )
        return self.__cache[name]

    def qualifiers(self):
        if self.__qualifiers is None:
            self.__qualifiers = {}
            data_dir = os.path.join(self.__context.root, 'Data')
            vehicle_file = os.path.join(data_dir, 'vehicle.xml')
            if not os.path.isfile(vehicle_file):
                msg = "vehicle.xml file not found %s" % vehicle_file
                raise ValueError(msg)
            vehicle_1_file = os.path.join(data_dir, 'vehicle_1.xml')
            if not os.path.isfile(vehicle_1_file):
                msg = "vehicle_1.xml file not found %s" % vehicle_1_file
                raise ValueError(msg)

            with open_xml(vehicle_file) as file:
                for event, elem in iterparse(file):
                    if event == 'end' and elem.tag == 'm':
                        qualifier = IDSQualifier.parse(elem)
                        self.__qualifiers[qualifier.id()] = qualifier

            with open_xml(vehicle_1_file) as file:
                for event, elem in iterparse(file):
                    if event == 'start' and elem.tag == 'm':
                        qualifier = self.__qualifiers[elem.attrib['t']]
                    elif event == 'end' and elem.tag == 'z':
                        key = elem.attrib['v']
                        qualifier.values()[key] = elem.attrib['m']

        return self.__qualifiers

    def texts(self):
        if self.__texts is None:
            self.__texts = {}
            lang = self.__context.lang.lower()
            texts_dir = os.path.join(
                os.path.join(self.__context.root, 'XMLFiles'),
                'Text',
            )
            for x in os.listdir(texts_dir):
                text_file = os.path.join(texts_dir, x)
                if os.path.isfile(text_file):
                    with open_xml(text_file) as file:
                        for event, elem in iterparse(file):
                            try:
                                if event == 'start' and elem.tag == 'tm':
                                    name = elem.attrib['id']
                                elif (
                                    event == 'end'
                                    and elem.tag == 'tu'
                                    and elem.nsmap['lang'] == lang
                                ):
                                    self.__texts[name] = elem.text
                            except KeyError:
                                print_xml_error("Issue parsing", elem)
        return self.__texts

    def vehicles(self):
        if self.__vehicles is None:
            self.__vehicles = {}
            vehicle_file = os.path.join(
                os.path.join(self.__context.root, 'Data'),
                'vehicle_2.xml',
            )
            if not os.path.isfile(vehicle_file):
                msg = "vehicle_2.xml file not found %s" % vehicle_file
                raise ValueError(msg)

            with open_xml(vehicle_file) as file:
                for event, elem in iterparse(file):
                    if event == 'end' and elem.tag == 'm':
                        vehicle = IDSVehicle.parse(elem)
                        self.__vehicles[vehicle.id()] = vehicle

        return self.__vehicles

    def modules(self):
        if self.__modules is None:
            self.__modules = {}
            mcprw_file = os.path.join(
                os.path.join(self.__context.root, 'Data'),
                'MCPRW_XMLFile.xml',
            )
            if not os.path.isfile(mcprw_file):
                msg = "MCPRW_XMLFile.xml file not found %s" % mcprw_file
                raise ValueError(msg)

            with open_xml(mcprw_file, encoding='utf-8-sig') as file:
                for event, elem in iterparse(
                    file,
                    encoding='utf-8',
                    wrapper=True,
                    recover=False,
                ):
                    if event == 'start':
                        if (
                            elem.tag
                            == '{VehicleModuleCorrel_XmlFile/RDS}ModuleDataName'
                        ):
                            module = IDSXMLModule.parse(elem)
                            self.__modules[module.id()] = module
                        elif (
                            elem.tag == '{VehicleModuleCorrel_XmlFile/RDS}Vehicle'
                        ):
                            vehicle = IDSXMLVehicle.parse(elem)
                            module.vehicles().append(vehicle)
                        elif (
                            elem.tag == '{VehicleModuleCorrel_XmlFile/RDS}XMLFile'
                        ):
                            f = IDSXMLFile.parse(elem)
                            vehicle.files()[f.id()] = f

        return self.__modules

    def mnemonics(self):
        if self.__mnemonics is None:
            self.__mnemonics = {}

            mnemonics_file = os.path.join(
                os.path.join(self.__context.root, 'Data'),
                'Mnemonics_%s.xml' % self.__context.lang,
            )
            if not os.path.isfile(mnemonics_file):
                msg = (
                    "Mnemonics_%s.xml file not found %s"
                    % (self.__context.lang, mnemonics_file)
                )
                raise ValueError(msg)

            with open_xml(mnemonics_file) as file:
                for event, elem in iterparse(file):
                    if event == 'end' and elem.tag == 'd':
                        self.__mnemonics[elem.attrib['m']] = Mnemonic.parse(elem)

        return self.__mnemonics


    #
    ## Utils
    #

    def get_references(self, obj):
        types = [(t, key, t.attributes()[key]) for t in self.datatypes().values() for key in t.attributes() if
                 t.attributes()[key].type() == obj.type()]

        ret = []
        for (t, key, attribute_type) in types:
            for n in self.load_rec(t.name()).values():
                if key in n.attributes():
                    attribute = n.attributes()[key]
                    if attribute_type.array():
                        if obj.id().a() in attribute:
                            ret.append(n)
                    else:
                        if obj.id().a() == attribute:
                            ret.append(n)
        if isinstance(obj, IDSVehicle):
            for t in self.datatypes().values():
                for n in self.load_rec(t.name()).values():
                    if isinstance(n, IDSObject):
                        for x in n.qualifications():
                            if IDSKey(x) == obj.id():
                                ret.append(n)
        return ret

    def get_vehicles(self, obj):
        return [self.vehicles()[IDSKey(x)] for x in obj.qualifications()]

    def get_parents(self, obj):
        return [v for v in self.vehicles().values() if v.check(obj)]

    def get_modules(self, obj):
        modules = {}
        for module in self.modules().values():
            ret = []
            for v in module.vehicles():
                if v.check(obj):
                    ret.append(v)
            if len(ret) != 0:
                modules[module.name()] = [x.files() for x in ret]
        return modules


#
## Display
#

SIMPLE_IDS_TYPES = ['STRING', 'INT', 'BOOL', 'MESSAGE', 'NUMERIC', None]
NULL_IDS_VALUES = ['NULL', '', '0']


def is_ids_object(obj, attribute_type=None):
    if isinstance(obj, IDSObject) or isinstance(obj, IDSVehicle) or attribute_type not in SIMPLE_IDS_TYPES:
        if obj not in NULL_IDS_VALUES:
            return True
    return False


def object_string(ctx, obj, attribute_type=None):
    if attribute_type == 'MESSAGE' and obj and len(obj) > 0:
        if obj in ctx.mnemonics():
            obj = ctx.mnemonics()[obj]

    if isinstance(obj, IDSObject):
        txt = "%s(%s)" % (str(obj), obj.type())
    elif isinstance(obj, IDSVehicle):
        txt = "%s" % (str(obj))
    elif isinstance(obj, dict):
        txt = "Dictionnary (%d entries)" % (len(obj))
    else:
        txt = str(obj)

    if is_ids_object(obj, attribute_type):
        return termcolor.colored(txt, 'white')
    return txt


def print_rec(ctx, obj, tab=0, limit=-1, attribute_type=None):
    print('\t' * tab + object_string(ctx, obj, attribute_type))

    if limit == 0:
        return

    if isinstance(obj, IDSObject):
        obj_attributes = obj.attributes()
        datatype = ctx.datatypes_by_name()[obj.type()]
        for key, attribute in datatype.attributes().items():
            if key in obj_attributes:
                value = obj_attributes[key]
                if isinstance(value, list):
                    print("%s- %s(%s)%s:" % (
                        '\t' * (tab + 1), attribute.name(), attribute.type(), "[]" if attribute.array() else ""))
                    for obj in value:
                        print_rec(ctx, obj, tab + 2, limit - 1, attribute.type())
                else:
                    print("%s- %s(%s)%s: %s" % (
                        '\t' * (tab + 1), attribute.name(), attribute.type(), "[]" if attribute.array() else "",
                        object_string(ctx, attribute.function(value), attribute.type())))
            else:
                print("%s- %s(%s)%s: -------" % (
                    '\t' * (tab + 1), attribute.name(), attribute.type(), "[]" if attribute.array() else ""))
    elif isinstance(obj, IDSVehicle):
        for key, value in obj.qualifiers().items():
            item = object_string(ctx, ctx.qualifiers()[key].description(), 'MESSAGE')
            if value in ctx.qualifiers()[key].values():
                value = object_string(ctx, ctx.qualifiers()[key].values()[value], 'MESSAGE')
            print("%s- %s: %s" % ('\t' * (tab + 1), item, value))

    elif isinstance(obj, IDSXMLFile):
        print("%s- %s" % ('\t' * (tab + 1), obj.filename()))

        # elif isinstance(obj, dict):
        #	for key, value in obj.items():
        #		print("%s- %s: %s" % ('\t'*(tab+1), key, value))


def resolve(ctx, obj):
    if isinstance(obj, MenuEntry):
        if isinstance(obj.value(), list):
            obj = [y for x in obj.value() for y in IDSKey(x).get_in(ctx.load_rec(obj.attribute_type()))]
        else:
            obj = IDSKey(obj.value()).get_in(ctx.load_rec(obj.attribute_type()))
    return obj


def display(ctx, obj, previous=None, next=None):
    if isinstance(obj, IDSObject):
        print_rec(ctx, obj, 0, 1)
        print('')
    elif isinstance(obj, IDSVehicle):
        print_rec(ctx, obj, 0, 1)
        print('')
    elif isinstance(obj, IDSXMLFile):
        print_rec(ctx, obj, 0, 1)
        print('')
    elif isinstance(obj, dict):
        print_rec(ctx, obj, 0, 1)
        print('')


class MenuEntry(object):
    def __init__(self, attribute_type, value):
        super(MenuEntry, self).__init__()
        self.__attribute_type = attribute_type
        self.__value = value

    def attribute_type(self):
        return self.__attribute_type

    def value(self):
        return self.__value


def menu(ctx, obj, vehicles, references, parents, modules, previous=None, next=None):
    choices = {}

    if isinstance(obj, list):
        for i, k in enumerate(obj):
            print("%d: %s" % (i, object_string(ctx, k)))
            choices[str(i)] = k

    if isinstance(obj, dict):
        for i, (k, v) in enumerate(obj.items()):
            print("%d: %s" % (i, object_string(ctx, k)))
            choices[str(i)] = v

    elif isinstance(obj, IDSObject):
        obj_attributes = obj.attributes()
        datatype = ctx.datatypes_by_name()[obj.type()]
        i = 0
        for key, attribute in datatype.attributes().items():
            if key in obj_attributes:
                value = obj_attributes[key]
                if is_ids_object(value, attribute.type()):
                    print("%d: %s" % (i, attribute.name()))
                    choices[str(i)] = MenuEntry(attribute.type(), attribute.function(value))
                    i += 1
        if references:
            print('r: References')
            choices['r'] = references
        if vehicles:
            print('v: Vehicles')
            choices['v'] = vehicles
    elif isinstance(obj, IDSVehicle):
        if references:
            print('r: References')
            choices['r'] = references
        if parents:
            print('x: Parents')
            choices['x'] = parents
        if modules:
            print('m: Modules')
            choices['m'] = modules

    if previous:
        print('p: Previous')
        choices['p'] = previous
    if next:
        print('n: Next')
        choices['n'] = next
    print('q: Exit')
    choices['q'] = None
    return choices


def browse(ctx, obj):
    PREVIOUS_KEY = "PREVIOUS"
    NEXT_KEY = "NEXT"
    REFERENCES_KEY = "REFERENCES"
    VEHICLES_KEY = "VEHICLES"
    PARENTS_KEY = "PARENTS"
    MODULES_KEY = "MODULES"
    previous = []
    next = []
    while obj is not None:
        # Interpret menu entry
        obj = resolve(ctx, obj)

        # Display current selection
        display(ctx, obj)

        # Print corresponding menu
        choices = menu(ctx, obj, VEHICLES_KEY, REFERENCES_KEY, PARENTS_KEY, MODULES_KEY, PREVIOUS_KEY if len(previous) > 0 else None,
                       NEXT_KEY if len(next) > 0 else None)

        # Interpret the choice
        str = input("Choice? ")
        if str in choices:
            old = obj
            obj = choices[str]
            if obj == PREVIOUS_KEY:
                next.insert(0, old)
                obj = previous.pop()
            elif obj == NEXT_KEY:
                previous.append(old)
                obj = next.pop(0)
            else:
                if obj == REFERENCES_KEY:
                    obj = ctx.get_references(old)
                elif obj == VEHICLES_KEY:
                    obj = ctx.get_vehicles(old)
                elif obj == PARENTS_KEY:
                    obj = ctx.get_parents(old)
                elif obj == MODULES_KEY:
                    obj = ctx.get_modules(old)
                previous.append(old)
                next[:] = []
        else:
            print("Invalid input")
        print('')


