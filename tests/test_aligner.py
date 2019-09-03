import unittest
import os
import json

from utils.align import Align

TEST_PATH = os.path.dirname(os.path.realpath(__file__))
TEST_FILES_PATH = os.path.join(TEST_PATH, '../test_files')
MODEL_PATH = os.path.join(TEST_PATH, '../../cmusphinx-models/ca-es')
DICT_PATH = os.path.join(MODEL_PATH, 'pronounciation-dictionary.dict')
TMP_PATH = os.path.join(TEST_PATH, '../tmp_test')

class AlignerTestCase(unittest.TestCase):
    def setUp(self):
        #test_aligner = Align()
        align_test_wav = os.path.join(TEST_FILES_PATH,
                                      'c3d9d2a15a76a9fbb591.mp3')
        align_test_text = os.path.join(TEST_FILES_PATH,
                                '2013_06_05_57807-14-c3d9d2a15a76a9fbb591.txt')
        self.aligner = Align(align_test_wav, align_test_text, DICT_PATH)
        # get files
        if not os.path.exists(TMP_PATH):
            os.mkdir(TMP_PATH)

    def tearDown(self):
        pass
        #os.popen('rm smt')

    def test_aligner(self):
        self.assertEqual(1,1)
