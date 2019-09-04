import unittest
import os
import json

from utils.text import Text

TEST_PATH = os.path.dirname(os.path.realpath(__file__))
TEST_FILES_PATH = os.path.join(TEST_PATH, '../test_source')
TMP_PATH = os.path.join(TEST_PATH, '../tmp_test')

class TextTestCase(unittest.TestCase):
    def setUp(self):
        self.test_intervention_files = [['c3d9d2a15a76a9fbb591_sentences.txt',
                                         'c3d9d2a15a76a9fbb591_decode.json',
                                         'c3d9d2a15a76a9fbb591_align.json'],
                                        ['d96ee006b62213506a07_sentences.txt',
                                         'd96ee006b62213506a07_decode.json',
                                         'd96ee006b62213506a07_align.json'],
                                        ['28fd6d0874eecbfdff35_sentences.txt',
                                         '28fd6d0874eecbfdff35_decode.json',
                                         '28fd6d0874eecbfdff35_align.json']]
        if not os.path.exists(TMP_PATH):
            os.mkdir(TMP_PATH)

    def tearDown(self):
        os.popen('rm %s/*.*'%TMP_PATH)

    def test_text_aligner(self):

        for test_intervention in self.test_intervention_files: 
            sentence_file = os.path.join(TEST_FILES_PATH, test_intervention[0])
            decode_file = os.path.join(TEST_FILES_PATH, test_intervention[1])
            alignment_file = os.path.join(TMP_PATH, test_intervention[2])
            comparison_alignment_file = os.path.join(TEST_FILES_PATH,
                                                     test_intervention[2])

            with open(sentence_file) as infile:
                sentences = [line.strip() for line in infile.readlines()]
            with open(decode_file) as infile:
                decode = json.load(infile)
            with open(comparison_alignment_file) as infile:
                self.comparison_alignment = json.load(infile)

            # initialize
            self.text_ops = Text(sentences, decode, alignment_file)

            self.text_ops.align()
            alignment = self.text_ops.align_results 
            self.assertEqual(alignment, self.comparison_alignment)
