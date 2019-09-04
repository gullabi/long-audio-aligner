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
        search_beginning = True
        block_tuples = []
        start = -1
        end = 0

        for i, token in enumerate(self.alignment):
            if i > end:
                if search_beginning:
                    if token.get('target_speaker'):
                        start = i
                        search_beginning = False
                else:
                    if not token.get('target_speaker'):
                        end = i-1
                        block_tuples.append((start, end))
                        search_beginning = True
        # if end is not found for the last block, it means
        # target speaker block is the last block and
        # needs to be added to the block_tuples
        if not block_tuples:
            if start != -1:
                # there is a single block that ends with the
                # target speaker
                block_tuples.append((start,i))
            else:
                msg = 'no target speaker block was found'
                logging.error(msg)
                raise ValueError(msg)
        else:
            # for multiple blocks ending with the target speaker
            if end == block_tuples[-1][1] and\
               start != block_tuples[-1][0]:
                block_tuples.append((start,i))

        self.alignment_blocks = []
        for start, end in block_tuples:
            self.alignment_blocks.append(self.alignment[start:end+1])

    def get_segments(self):
        for block in self.alignment_blocks:
            self.segments += self.get_block_segments(block)

    def get_block_segments(self, block):
        '''
        calculates the minimum length segments based on adjacent tokens
        with timestamps and silences between them
        '''

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
