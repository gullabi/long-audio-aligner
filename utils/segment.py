import os
import subprocess
import logging

from math import floor
from utils.beam import Beam

class Segmenter(object):
    def __init__(self, alignment, silence = 0.099):
        # TODO assert alignment object has target_speaker and punctuation
        self.alignment = alignment
        self.silence = silence
        self.get_target_blocks()
        self.segments = []
        self.best_segments = []

    def get_target_blocks(self):
        '''
        Currently gets only the first block, works 100% under the assumption that
        there is only one single speaker block
        '''
        target_found = False
        start = -1
        end = 0
        for i, token in enumerate(self.alignment):
            if not target_found:
                # find the beginning of the speaker block
                if token.get('target_speaker'):
                    start = i
                    target_found = True
            else:
                if not token.get('target_speaker'):
                    end = i
                    break
        if start == -1:
            msg = 'starting index not found smt wrong'
            raise ValueError(msg)
        elif start != -1 and end == 0:
            # start index found but not the end index
            end = len(self.alignment)

        # TODO implement multiple block processing
        # for now it gives a warning
        for token in self.alignment[end:]:
            if token.get('target_speaker'):
                msg = 'target speaker found past last speaker block'
                logging.warning(msg)
        self.alignment_blocks = [self.alignment[start:end]]

    def get_segments(self):
        for block in self.alignment_blocks:
            self.segments += self.get_block_segments(block)

    def get_block_segments(self, block):
        # the block should start and with with a token with start (end) time
        indicies = [i for i, token in enumerate(block) if token.get('start')]
        start_index, end_index = indicies[0], indicies[-1]+1
        cropped_block = block[start_index:end_index]
        unit_segments = []
        # first segment
        segment = {'words': '', 'start': cropped_block[0]['start']}
        for i, element in enumerate(cropped_block):
            if i < len(cropped_block)-1:
                segment['words'] += element['word'] + ' '
                next_element = cropped_block[i+1]
                if element.get('end') and next_element.get('start'):
                    if (float(next_element['start'])-float(element['end'])) > \
                                                                  self.silence:
                        segment['end'] = element['end']
                        segment['words'] = segment['words'].strip()
                        if element.get('punctuation'):
                            segment['punctuation'] = element['punctuation']
                        unit_segments.append(segment)
                        # new segment
                        segment = {'words': '', 'start':next_element['start']}
            else:
                segment['words'] += element['word']
                segment['end'] = element['end']
                unit_segments.append(segment)
        return unit_segments

    def optimize(self, beam_width=10):
        beam = Beam(beam_width)
        for segment in self.segments:
            beam.add(segment)
        # sequences are ordered according to the score
        # and the first element has the best score
        self.best_segments = beam.sequences[0]

    def segment_audio(self, audio_file, base_path='tmp'):
        base_name = '.'.join(os.path.basename(audio_file).split('.')[:-1])
        path = os.path.join(base_path, base_name[0], base_name[1])
        if not os.path.isdir(path):
            os.makedirs(path)

        for segment in self.best_segments:
            self.segment_cue(audio_file, segment, path)
            if (float(segment['end']) - float(segment['start'])) > 15.:
                msg = '%s longer than 15 s'%segment['segment_path']
                logging.info(msg)

    @staticmethod
    def segment_cue(audio, cue, base_path):
        audio_tool = 'ffmpeg'
        seek = floor(cue['start'])
        start = cue['start'] - seek
        end = cue['end']
        duration = end - cue['start']
        basename = '.'.join(os.path.basename(audio).split('.')[:-1])
        cue['segment'] = '_'.join([basename, str(cue['start']), str(cue['end'])])
        cue['segment_path'] = os.path.join(base_path, cue['segment'])+'.wav'
        args = [audio_tool, '-y', '-hide_banner', '-loglevel', 'panic',\
                '-ss', str(seek), '-i', audio, '-ss', str(start), \
                '-t', str(duration), '-ac', '1', '-ar', '16000', \
                cue['segment_path']]
        if os.path.isfile(cue['segment_path']):
            logging.info("%s already exists skipping"%cue['segment'])
        else:
            subprocess.call(args)
            if not os.path.isfile(cue['segment_path']):
                msg = "File not created from ffmpeg operation %s"\
                       %cue['segment_path']
                logging.error(msg)
                raise IOError(msg)

def log_subprocess_output(pipe):
    for line in iter(pipe.readline, b''): # b'\n'-separated lines
        logging.info('subprocess stderr: %r', line)
