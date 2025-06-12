import unittest
import xml.etree.ElementTree as ET

from ids import IDSVehicle, IDSXMLVehicle, IDSKey


class TestIDSVehicle(unittest.TestCase):
    def test_parse_and_check(self):
        elem = ET.Element('m', n='123', s='abc', CM_MODEL='M3')
        vehicle = IDSVehicle.parse(elem)
        self.assertEqual(vehicle.id(), IDSKey('123', 'abc'))
        other = IDSVehicle('123', 'abc', {'CM_MODEL': 'M3'})
        self.assertTrue(vehicle.check(other))


class TestIDSXMLVehicle(unittest.TestCase):
    def test_parse_base(self):
        vehicle = IDSXMLVehicle({'CM_BASE': 'BASE'})
        self.assertTrue(vehicle.base())
        elem = ET.Element('Vehicle', CM_PROJECT='MZ')
        vehicle = IDSXMLVehicle.parse(elem)
        self.assertIn('CM_Project', vehicle.qualifiers())
        self.assertEqual(vehicle.qualifiers()['CM_Project'], 'MZ')


if __name__ == '__main__':
    unittest.main()
