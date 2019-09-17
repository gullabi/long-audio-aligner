import unittest
import os
import json

from utils.segment import Segmenter
from utils.map import Map

TEST_PATH = os.path.dirname(os.path.realpath(__file__))
TEST_FILES_PATH = os.path.join(TEST_PATH, '../test_source')
TMP_PATH = os.path.join(TEST_PATH, '../tmp_test')

class SegmenterTestCase(unittest.TestCase):
    def setUp(self):
        self.test_files_list = [['2013_06_05_57807-14-c3d9d2a15a76a9fbb591.json',
                                 'c3d9d2a15a76a9fbb591_align.json',
                                 'c3d9d2a15a76a9fbb591_mapped_align.json'],
                                ['2015_06_03_59079_47.json',
                                 'd96ee006b62213506a07_align.json',
                                 'd96ee006b62213506a07_mapped_align.json'],
                                ['2015_02_04_57900_59.json',
                                 '28fd6d0874eecbfdff35_align.json',
                                 '28fd6d0874eecbfdff35_mapped_align.json']]

    def tearDown(self):
        pass

    def test_map(self):
        for test_files in self.test_files_list:
            with open(os.path.join(TEST_FILES_PATH, test_files[0])) as infile:
                intervention = json.load(infile)

            with open(os.path.join(TEST_FILES_PATH, test_files[1])) as infile:
                alignment = json.load(infile)

            with open(os.path.join(TEST_FILES_PATH, test_files[2])) as infile:
                m_alignment = json.load(infile)

            map_test = Map(list(intervention.values())[0], alignment)

            # test check
            map_test.check()

            # test find speaker
            map_test.find_speaker()

            # test enrich alignment
            map_test.enrich_alignment()
            self.assertEqual(map_test.alignment, m_alignment)
