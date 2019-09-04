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
                                 'c3d9d2a15a76a9fbb591_best_segments.json',
                                 0.94],
                                ['2015_06_03_59079_47.json',
                                 'd96ee006b62213506a07_align.json',
                                 'd96ee006b62213506a07_mapped_align.json',
                                 'd96ee006b62213506a07_best_segments.json',
                                  0.94],
                                ['2015_02_04_57900_59.json',
                                 '28fd6d0874eecbfdff35_align.json',
                                 '28fd6d0874eecbfdff35_mapped_align.json',
                                 '28fd6d0874eecbfdff35_best_segments.json',
                                 0.80]]
        if not os.path.exists(TMP_PATH):
            os.mkdir(TMP_PATH)

    def tearDown(self):
        os.popen('rm %s/*.*'%TMP_PATH)

    def test_segmenter(self):

        for test_files in self.test_files_list:
            test_file = os.path.join(TEST_FILES_PATH, test_files[0])
            alignment_file = os.path.join(TEST_FILES_PATH, test_files[1])
            comparison_mapped_alignment_file = os.path.join(TEST_FILES_PATH,
                                                                  test_files[2])
            with open(comparison_mapped_alignment_file) as infile:
                self.comparison_mapped_alignment = json.load(infile)
            self.base_segments_file = os.path.join(TEST_FILES_PATH,
                                                   test_files[3])
            tmp_segments_file = os.path.join(TMP_PATH, test_files[3])

            # get beginning and end of the target speaker segments
            for token in self.comparison_mapped_alignment:
                if token.get("target_speaker") and token.get('start'):
                    self.target_start = token['start']
                    break

            for token in self.comparison_mapped_alignment[::-1]:
                if token.get("target_speaker") and token.get('end'):
                    self.target_end = token['end']
                    break

            with open(test_file) as infile:
                intervention_full = json.load(infile)
            for key, value in intervention_full.items():
                self.intervention = value

            with open(alignment_file) as infile:
                self.alignment = json.load(infile)

            # to get optimal segments
            # get punctuation and speaker information
            m = Map(self.intervention, self.alignment)
            m.prepare()

            # check map enrichment
            #with open(comparison_mapped_alignment_file, 'w') as out:
            #    json.dump(m.alignment, out, indent=2)
            self.assertEqual(m.alignment, self.comparison_mapped_alignment)

            # get segments using silences
            segmenter = Segmenter(m.alignment)
            segmenter.get_segments()

            # check if results are consistent with the
            self.assertEqual(segmenter.segments[0]['start'], self.target_start)
            self.assertEqual(segmenter.segments[-1]['end'], self.target_end,
                             msg='for %s last segment ends before the '\
                                 'intervention probably bsc of multiple '\
                                 'blocks of the speaker'%test_files[0])

            # optimize segments
            segmenter.optimize()
            with open(tmp_segments_file, 'w') as out:
                json.dump(segmenter.best_segments, out, indent=2)

            # check if optimized segments are > 94% of the whole duration
            target_fraction = test_files[4]
            segment_duration = 0
            for segment in segmenter.best_segments:
                segment_duration += (segment['end'] - segment['start'])
            total_duration = self.target_end - self.target_start # not exactly
            segment_fraction = segment_duration/total_duration
            self.assertTrue(segment_fraction > target_fraction,
                            msg = 'total optimized segment duration is smaller than'\
                                  ' %1.2f: %1.2f for %s'%(target_fraction,
                                                          segment_fraction,
                                                          test_files[3]))

            #with open(self.base_segments_file, 'w') as out:
            #    json.dump(segmenter.best_segments, out, indent=2)
