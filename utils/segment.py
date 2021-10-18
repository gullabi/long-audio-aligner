import os
import subprocess
import logging

from math import floor
from utils.beam import Beam

class Segmenter(object):
    def __init__(self, alignment, silence = 0.099, t_min = 2, t_max = 10):
        # TODO assert alignment object has target_speaker and punctuation
        self.alignment = alignment
        self.silence = silence
        self.t_min = t_min # TODO for now useless
        self.t_max = t_max
        self.beam_width = 10
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
        segments = []
        for block in self.alignment_blocks:
            segments += self.get_block_segments(block)

        # check if all segments are shorter than t_max
        for segment in segments:
            if (segment['end'] - segment['start']) > self.t_max:
                #logging.warning('long segment found, cutting it\n%s'\
                #                 %segment['words'])
                shorter_segments = self.shorten_segment(segment)
                # shorthen segment might fail
                if shorter_segments:
                    for shorter_segment in shorter_segments:
                        self.segments.append(shorter_segment)
                        #logging.warning('* resulting in: %s'\
                        #                %shorter_segment['words'])
                else:
                    self.segments.append(segment)
            else:
                self.segments.append(segment)

    def get_block_segments(self, block):
        '''
        calculates the minimum length segments based on adjacent tokens
        with timestamps and silences between them
        '''

        # the block should start and with with a token with start (end) time
        indicies = [i for i, token in enumerate(block) if token.get('start')]
        start_index, end_index = indicies[0], indicies[-1]+1
        cropped_block = block[start_index:end_index]
        unit_segments = join_block(cropped_block, self.silence)
        return unit_segments

    def shorten_segment(self, segment):
        '''
        takes a segment longer than t_max and divides it
        until all the parts are smaller than t_max
        '''
        found = False
        tokens = []
        for token in self.alignment:
            if token.get('start') == segment['start']:
                found = True
            if found:
                tokens.append(token)
                if token.get('end') == segment['end']:
                    break
        if not found:
            msg = "the segment to be shortened not found in alignment "\
                  "tokens"
            logging.error(msg)
            raise ValueError(msg)

        # get silences
        silences = []
        for i, token in enumerate(tokens):
            if i > 0:
                token_before = tokens[i-1]
                if token_before.get('end') and token.get('start'):
                    silences.append(token['start']-token_before['end'])
                else:
                    silences.append(0)

        int_set = set(silences)
        if 0 in int_set:
            int_set.remove(0)
        silence_values = list(int_set)
        silence_values.sort(reverse=True)

        # get cut indicies starting from the longest silence
        cut_index = []
        for val in silence_values:
            for i, silence in enumerate(silences):
                if silence == val:
                    cut_index.append(i)

        # cut the segment starting from the longest silence interval
        final_cut_index = []
        new_segments = []
        for index in cut_index:
            final_cut_index.append(index)
            new_segments = join_tokens(tokens, final_cut_index)
            max_duration = max([nsegment['end']-nsegment['start']\
                                for nsegment in new_segments])
            if max_duration <= self.t_max:
                break

        # cut_index and hence new_segments could end up empty
        if new_segments:
            # optimize the new segments since there could be many single token ones
            sh_beam = Beam(5, 0.4*self.t_min, 0.72*self.t_max)
            for segment in new_segments:
                sh_beam.add(segment)
            return sh_beam.sequences[0]
        else:
            return []

    def optimize(self):
        beam = Beam(self.beam_width, self.t_min, self.t_max)
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
            logging.debug("%s already exists skipping"%cue['segment'])
        else:
            subprocess.call(args)
            if not os.path.isfile(cue['segment_path']):
                msg = "File not created from ffmpeg operation %s"\
                       %cue['segment_path']
                logging.error(msg)
                raise IOError(msg)

def join_block(cropped_block, silence):
    unit_segments = []
    segment = {'words': '', 'original_words': '',
               'start': cropped_block[0]['start']}
    for i, element in enumerate(cropped_block):
        if i < len(cropped_block)-1:
            segment['words'] += element['word'] + ' '
            segment['original_words'] += element['original_word'] + ' '
            next_element = cropped_block[i+1]
            if element.get('end') and next_element.get('start'):
                if (float(next_element['start'])-float(element['end'])) >= \
                                                                       silence:
                    segment['end'] = element['end']
                    segment['words'] = segment['words'].strip()
                    segment['original_words'] = segment['original_words'].strip()
                    if element.get('punctuation'):
                        segment['punctuation'] = element['punctuation']
                    unit_segments.append(segment)
                    # new segment
                    segment = {'words': '', 'original_words': '',
                               'start':next_element['start']}
        else:
            segment['words'] += element['word']
            segment['original_words'] += element['original_word']
            segment['end'] = element['end']
            unit_segments.append(segment)
    return unit_segments

def join_tokens(tokens, indicies):
    '''
    takes cut indicies and joins tokens accordingly
    cut index of 0 means, there will be two segments tokens[:1], tokens[1:]
    cut indicies of 0 and 4 means tokens[:1], tokens[1:5], tokens[5:]
    '''
    segments = []
    indicies.sort()
    for i, index in enumerate(indicies):
        if i == 0:
            segments.append(add_tokens(tokens[:index+1]))
            if len(indicies) == 1:
                # we need to end the last segment manually
                segments.append(add_tokens(tokens[index+1:]))
        else:
            last_index = indicies[i-1]+1
            segments.append(add_tokens(tokens[last_index:index+1]))
            if i == len(indicies)-1:
                segments.append(add_tokens(tokens[index+1:]))
    return segments

def add_tokens(tokens):
    segment = {'words': '', 'original_words': '',
               'start': tokens[0]['start']}
    for i, token in enumerate(tokens):
        if i < len(tokens)-1:
            segment['words'] += token['word'] + ' '
            segment['original_words'] += token['original_word'] + ' '
        else:
            segment['words'] += token['word']
            segment['original_words'] += token['original_word']
            segment['end'] = token['end']
            if token.get('punctuation'):
                segment['punctuation'] = token['punctuation']
    return segment

def log_subprocess_output(pipe):
    for line in iter(pipe.readline, b''): # b'\n'-separated lines
        logging.debug('subprocess stderr: %r', line)
