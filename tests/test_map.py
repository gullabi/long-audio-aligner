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
                                 'c3d9d2a15a76a9fbb591_mapped_align.json',
                                 'Pere Calbó i Roca'],
                                ['2015_06_03_59079_47.json',
                                 'd96ee006b62213506a07_align.json',
                                 'd96ee006b62213506a07_mapped_align.json',
                                 'El president de la Generalitat'],
                                ['2015_02_04_57900_59.json',
                                 '28fd6d0874eecbfdff35_align.json',
                                 '28fd6d0874eecbfdff35_mapped_align.json',
                                 'El president de la Generalitat']]

        if not os.path.exists(TMP_PATH):
            os.mkdir(TMP_PATH)

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
            self.assertEqual(test_files[3], map_test.target_speaker)

            # test enrich alignment
            map_test.enrich_alignment()
            target_in_list = False
            for al in map_test.alignment:
                if al.get('target_speaker'):
                    target_in_list = True
            self.assertTrue(target_in_list)

            # test alignment with original words
            map_test.align()
            with open(os.path.join(TMP_PATH, test_files[2]), 'w') as out:
                json.dump(map_test.alignment, out, indent=2)

            self.assertEqual(map_test.alignment, m_alignment)
