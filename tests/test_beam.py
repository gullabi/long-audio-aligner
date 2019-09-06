import unittest
import os
import json

from utils.beam import Beam

TEST_PATH = os.path.dirname(os.path.realpath(__file__))
TEST_FILES_PATH = os.path.join(TEST_PATH, '../test_source')
TMP_PATH = os.path.join(TEST_PATH, '../tmp_test')

class BeamTestCase(unittest.TestCase):
    def setUp(self):
        self.test_files = ['d96ee006b62213506a07_segments.json']
        self.beam_width = 10
        self.t_min = 3 # currently useless
        self.t_max = 10

        if not os.path.exists(TMP_PATH):
            os.mkdir(TMP_PATH)

    def tearDown(self):
        pass
        #os.popen('rm %s/*.*'%TMP_PATH)

    def test_beam(self):
        for test_file in self.test_files:
            segment_file = os.path.join(TEST_FILES_PATH, test_file)
            with open(segment_file) as infile:
                segments = json.load(infile)

            # optimize segments
            beam = Beam(self.beam_width, self.t_min, self.t_max)
            for segment in segments:
                beam.add(segment)
            best_segments = beam.sequences[0]

            # check if there are unreasonably long segments
            max_unoptimized_length = max([segment['end']-segment['start']\
                                    for segment in segments])
            max_length = max([segment['end']-segment['start']\
                              for segment in best_segments])
            reference_length = max(30, max_unoptimized_length)
            self.assertTrue(max_length < reference_length,
                            msg="unreasonably long optimized segments are "\
                                "present in %s with %f seconds wrt %f"%(test_file,
                                                                 max_length,
                                                                 reference_length))
