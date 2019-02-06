import os
import json

import utils.seq_aligner as seq

class Text(object):
    '''
    Class that mixes the cmu cleaned sentences with the aligned word timestamps
    which come from decoding
    '''
    def __init__(self, sentences, decode, outfile):
        self.sentences = sentences
        self.decode = decode
        self.align_outfile = outfile

        self.word_seq = []
        for sentence in self.sentences:
            self.word_seq += sentence.strip().split()

        self.decode_seq = []
        for word_timestamp in self.decode:
            decoded_word = word_timestamp[0]
            if decoded_word not in ['<s>', '<sil>', '</s>']:
                self.decode_seq.append(decoded_word)

        self.align_seq = []
        self.align_results = []
        # if align_outfile exists get alignment
        if os.path.isfile(self.align_outfile):
            msg = 'WARNING: alignment outfile %s exists'%self.align_outfile

    def align(self):
        #TODO cache alignment
        self.align_seq = seq.needle(self.word_seq, self.decode_seq)
        self.write_align()
        self.get_timestamps()

    def write_align(self, debug=False):
        s1, s2 = self.align_seq
        new_align_seq = ([],[])
        for w1, w2 in zip(s1, s2):
            if '--' not in [w1, w2] and w1 != w2:
                new_align_seq[0].append(w1)
                new_align_seq[0].append('--')
                new_align_seq[1].append('--')
                new_align_seq[1].append(w2)
            else:
                new_align_seq[0].append(w1)
                new_align_seq[1].append(w2)
        self.align_seq = new_align_seq
        if debug:
            s1, s2 = self.align_seq
            with open(self.align_outfile.replace('.json','.ls'), 'w') as out:
                for w1, w2 in zip(s1, s2):
                    out.write('%s %s\n'%(w1, w2))

    def read_align(self):
        ref_seq = []
        dec_seq = []
        for line in open(self.align_outfile).readlines():
            ref, dec = line.strip().split()
            ref_seq.append(ref)
            dec_seq.append(dec)
        return (ref_seq, dec_seq)

    def get_timestamps(self):
        s1, s2 = self.align_seq
        cl_decode = [seq for seq in self.decode \
                     if seq[0] not in ['<s>', '<sil>', '</s>']]
        for w1, w2 in zip(s1, s2):
            w = {}
            w['word'] = w1
            if w1 == w2:
                token = cl_decode[0]
                if w2 != token[0]:
                    msg = 'timestamp of word "%s" cannot be found'%w2
                    print(token[0])
                    print(cl_decode)
                    raise ValueError(msg)
                w['start'] = token[1]
                w['end'] = token[2]
                self.align_results.append(w)
                cl_decode.pop(0)
            elif w1 == '--':
                cl_decode.pop(0)
            elif w2 == '--':
                self.align_results.append(w)
            else:
                msg = 'unexpected alignment result: %s vs %s'%(w1, w2) 
                raise ValueError(msg)
        with open(self.align_outfile, 'w') as out:
            json.dump(self.align_results, out, indent=4)
