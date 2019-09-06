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
                                 0.93],
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

        self.long_segments = [
        {"end": 104.21,
         "words": "no compartim que no puguin col\u00b7laborar amb els mossos d'acord amb la llei per evitar robatoris el partit popular no dir\u00e0 mai als ciutadans que han d'aguantar que els robin sense fer res i que s'ho quedin mirant",
         "punctuation": 1.0,
         "start": 92.55
        },
        {'words': "no compartim que no puguin col·laborar amb els mossos d'acord amb la llei per evitar robatoris el partit popular no dirà mai als ciutadans que han d'aguantar que els robin sense fer res i que s'ho quedin mirant direm als pagesos que d'acord amb la llei col·laborin amb la policia per evitar els robatoris i al govern li exigirem que augmenti els agents que destina a l'àmbit rural que incrementi les actuacions preventives i que garanteixi la seguretat que aquesta és la seva responsabilitat",
        'start': 92.55,
        'end': 122.5,
        'punctuation': 1.0}]

        if not os.path.exists(TMP_PATH):
            os.mkdir(TMP_PATH)

    def tearDown(self):
        pass
        #os.popen('rm %s/*.*'%TMP_PATH)

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
            tmp_segments_file = os.path.join(TMP_PATH,
                                             test_files[3].replace('_best',''))
            tmp_best_segments_file = os.path.join(TMP_PATH, test_files[3])

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

            # initialize segmenter
            segmenter = Segmenter(m.alignment)

            # test shorten_segment
            if test_files[1] == 'c3d9d2a15a76a9fbb591_align.json':
                for long_segment in self.long_segments:
                    new_segments = segmenter.shorten_segment(long_segment)
                    max_new_length = max([nsegment['end']-nsegment['start']\
                                         for nsegment in new_segments])
                    # check if it works
                    self.assertTrue(max_new_length <= segmenter.t_max,
                                    msg='shorten segment not working\n%s'
                                        %str(new_segments))
                    # check tokens are lost in the process
                    total_duration = sum([n['end']-n['start']\
                                         for n in new_segments])
                    reference_duration = long_segment['end'] -\
                                         long_segment['start']
                    self.assertEqual(' '.join([n['words'] for n in new_segments]),
                                     long_segment['words'],
                                     msg="shorten_segment loses tokens")
                    # check if there are many single tokens
                    singles = len([1 for n in new_segments\
                                     if len(n['words'].split()) == 1])
                    self.assertTrue(singles < 2)

            # get segments using silences
            segmenter.get_segments()

            # check if results are consistent with the
            self.assertEqual(segmenter.segments[0]['start'], self.target_start)
            self.assertEqual(segmenter.segments[-1]['end'], self.target_end,
                             msg='for %s last segment ends before the '\
                                 'intervention probably bsc of multiple '\
                                 'blocks of the speaker'%test_files[0])

            # get segments before optimization
            with open(tmp_segments_file, 'w') as out:
                json.dump(segmenter.segments, out, indent=2)
            max_unoptimized_length = max([segment['end']-segment['start']\
                                    for segment in segmenter.segments])
            self.assertTrue(max_unoptimized_length <= segmenter.t_max,
                            msg="for %s longest segment is longer than t_max:"\
                                " %2.1f vs %2.1f"%(tmp_segments_file,
                                                   max_unoptimized_length,
                                                   segmenter.t_max))

            # optimize segments
            segmenter.optimize()
            with open(tmp_best_segments_file, 'w') as out:
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

            # check if there are unreasonably long segments
            max_unoptimized_length = max([segment['end']-segment['start']\
                                    for segment in segmenter.segments])
            max_length = max([segment['end']-segment['start']\
                              for segment in segmenter.best_segments])
            reference_length = max(30, max_unoptimized_length)
            self.assertTrue(max_length < reference_length,
                            msg="unreasonably long optimized segments are "\
                                "present in %s with %f seconds wrt %f"%(test_files[3],
                                                                 max_length,
                                                                 reference_length))
