from math import exp, log
from copy import deepcopy
from operator import itemgetter

class Beam(object):
    '''
    Converts unit segments into segments of optimal size using beam search

    args:
        beam_width
        TODO function (currently implemented in the object itself)
    '''
    def __init__(self, width):
        self.beam_width = width
        self.sequences = []

    def add(self, segment):
        '''
        Each sequence is a node, when a segment is added to a sequence, it can
        either be added as a new branch or concatenated to the last segment
        '''
        if not self.sequences:
            # add first segment to the first sequence
            self.sequences.append([segment])
        else:
            new_sequences = self.concatenate(segment) + \
                            self.branch(segment)
            self.sequences = self.prune(new_sequences)

    def branch(self, segment):
        bra_seqs = deepcopy(self.sequences)
        for seq in bra_seqs:
            # for each seguence add the new segment as a new seperate segment
            seq.append(segment)
        return bra_seqs

    def concatenate(self, segment):
        conc_seqs = deepcopy(self.sequences)
        for seq in conc_seqs:
            # for each sequence concatenate the last segment with the input seg
            seq[-1] = self.add_token(seq[-1], segment)
        return conc_seqs

    @staticmethod
    def add_token(first, second):
        '''
        adds dictionaries with keys, words, start, end, punctuation
        '''
        # TODO assert second comes after first
        try:
            added = {'words': ' '.join([first['words'], second['words']]),
                 'start': first['start'],
                 'end': second['end']}
        except Exception as e:
            print(first, second)
            raise e
        if second.get('punctuation'):
            added['punctuation'] = second['punctuation']
        return added

    def prune(self, sequences):
        # TODO rather than calculating the scores repeatedly, always work with
        # the sequence score tuples
        score_tuples = []
        for sequence in sequences:
            score = self.get_score(sequence)
            score_tuples.append((sequence, score))
        sorted_tuples = sorted(score_tuples, key=itemgetter(1))
        sorted_tuples.reverse()
        return [pair[0] for pair in sorted_tuples[:self.beam_width]]

    def get_score(self, sequence):
        '''
        Adds logarithms of the probability like [0,1] values for each segment
        and normalizes by dividing to the number of segments
        '''
        # TODO consider alpha parameter for the normalization
        alpha = 0.7
        score = 0
        n_segment = len(sequence)
        for segment in sequence:
            score += log(P_segment(segment))
        return score/n_segment**alpha

def P_segment(segment):
    '''
    Accepts a dict with keys words, start, end, punctuation returns a value
    between [0,1]
    '''
    # TODO punctuation values should be a multiplication factor between [0,1]
    # TODO input t_min, t_max
    # beta is an emprical parameter which makes the result 0.9 at t_min
    # for f_punctuation = 1 and t_min = 5; beta = 0.5
    beta = 0.5
    t_max = 19
    duration = segment['end'] - segment['start']
    if duration < 0:
        msg = 'duration cannot be negative'
        raise ValueError(msg)

    if segment.get('punctuation'):
        if type(segment['punctuation']) == float:
            f_punctuation = segment['punctuation']
        else:
            f_punctuation = 1.0
    else:
        f_punctuation = 0.5
    val = f_punctuation*exp(-beta/duration)
    # Step function to reject segments with durations > t_max
    if duration > t_max:
        val *= 0.01
    return val
