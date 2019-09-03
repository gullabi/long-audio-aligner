import unittest
import os
import json

from utils.segment import Segmenter

TEST_PATH = os.path.dirname(os.path.realpath(__file__))
TEST_FILES_PATH = os.path.join(TEST_PATH, '../test_files')

class SegmenterTestCase(unittest.TestCase):
    def setUp(self):
        #test_segmenter = Segmenter()
        segmentation_test_file = os.path.join(TEST_FILES_PATH,
                                              '2009_02_18_57660_32.json')
        self.segmentation_interventions = json.load(open(segmentation_test_file))
        # get files

    def tearDown(self):
        pass
        #os.popen('rm smt')

    def test_segmenter(self):
        self.assertEqual(1,1)
