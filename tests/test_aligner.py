import unittest
import os
import json

from utils.align import Align
from utils.sphinx import CMU

TEST_PATH = os.path.dirname(os.path.realpath(__file__))
TEST_FILES_PATH = os.path.join(TEST_PATH, '../test_source')
MODEL_PATH = os.path.join(TEST_PATH, '../../cmusphinx-models/ca-es')
DICT_PATH = os.path.join(MODEL_PATH, 'pronounciation-dictionary.dict')
TMP_PATH = os.path.join(TEST_PATH, '../tmp_test')

class AlignerTestCase(unittest.TestCase):
    def setUp(self):
        #test_aligner = Align()
        align_test_wav = os.path.join(TEST_FILES_PATH,
                                      'c3d9d2a15a76a9fbb591.mp3')
        align_test_text = open(os.path.join(TEST_FILES_PATH,
                                '2013_06_05_57807-14-c3d9d2a15a76a9fbb591.txt')).read()
        self.aligner = Align(align_test_wav, align_test_text, DICT_PATH, TMP_PATH)
        self.decode_outfile = self.aligner.align_outfile.replace('_align','_decode')
        self.cs = CMU(MODEL_PATH)
        # get files
        if not os.path.exists(TMP_PATH):
            os.mkdir(TMP_PATH)

    def tearDown(self):
        os.popen('rm -r %s'%TMP_PATH)

    def test_aligner(self):
        # create corpus
        self.aligner.create_textcorpus()
        # assert that corpus has more than one line
        self.assertTrue(len(open(self.aligner.corpus).readlines()) > 1)

        # create lm file
        self.aligner.create_lm()
        # check its format
        last_line = open(self.aligner.lm).readlines()[-1].strip()
        self.assertEqual(last_line, '\\end\\', msg='LM file has wrong format')

        # convert audio
        self.aligner.convert_audio()

        # decode
        self.cs.decode(self.aligner.audio_raw, self.aligner.lm)
        self.assertTrue(len(self.cs.segs) > 1, msg="decode did not yield results")
        '''
        with open(self.decode_outfile, 'w') as out:
            json.dump(self.cs.segs, out, indent=2)
        with open(self.decode_outfile.replace('_decode.json',
                                              '_sentences.txt'), 'w') as out:
            for sentence in self.aligner.sentences:
                out.write('%s\n'%sentence)
        '''
