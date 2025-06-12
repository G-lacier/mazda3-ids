import unittest
import xml.etree.ElementTree as ET

from ids import IDSQualifier, IDSXMLFile

class TestIDSQualifier(unittest.TestCase):
    def test_parse(self):
        elem = ET.Element('q', m='ID', v='Description')
        q = IDSQualifier.parse(elem)
        self.assertEqual(q.id(), 'ID')
        self.assertEqual(q.description(), 'Description')

class TestIDSXMLFile(unittest.TestCase):
    def test_parse(self):
        elem = ET.Element('f', xmlType='Type', xmlName='file.xml', TSBOnly='No')
        f = IDSXMLFile.parse(elem)
        self.assertEqual(f.name(), 'Type')
        self.assertEqual(f.filename(), 'file.xml')
        self.assertFalse(f.tsb())

if __name__ == '__main__':
    unittest.main()
