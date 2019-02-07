class Segmenter(object):
    def __init__(self, alignment):
        # TODO assert alignment object has target_speaker and punctuation
        self.alignment = alignment
        self.get_target_blocks()
        self.segments = []

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
                msg = 'WARNING: target speaker found past last speaker block'
                print(msg)
        self.alignment_blocks = [self.alignment[start:end]]

    def get_segments(self):
        for block in self.alignment_blocks:
            self.segments += self.get_block_segments(block)

    def get_block_segments(self, block):
        silence = 0.099

        # the block should start and with with a token with start (end) time
        indicies = [i for i, token in enumerate(block) if token.get('start')]
        start_index, end_index = indicies[0], indicies[-1]
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
                                                                        silence:
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
        return self.optimize(unit_segments)

    @staticmethod 
    def optimize(segments):
        return segments
