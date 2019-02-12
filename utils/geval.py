from utils.sphinx import CMU
from utils.seq_aligner import needle

jsgf_string = '''#JSGF V1.0;
grammar sentence;
public <sentence> = %s;
'''

class GEval(object):
    '''
    GEval: Grammar evaluate with pocketsphinx.

    Accepts segments dictionary and returns the same dictionary with scores
    '''
    def __init__(self, segments, model_path):
        self.segments = segments
        self.ps = CMU(model_path)
        # initialize ps config

    def evaluate(self):
        # TODO implement multithreaded process here
        for segment in self.segments:
            segment['score'], segment['decode'] = self.evaluate_segment(segment)

    def evaluate_segment(self, segment):
        grammar_file = self.create_jsgf(segment)
        self.ps.init_jsgf(grammar_file)
        self.ps.stream_decode(segment['segment_path'])
        decoded_words = [s[0] for s in self.ps.segs
                             if s[0] not in ['<sil>', '(NULL)']]
        return self.calculate(segment, decoded_words), ' '.join(decoded_words)

    @staticmethod
    def create_jsgf(segment):
        grammar_file = segment['segment_path'].replace('.wav','.jsgf')
        words = segment['words']
        words_wkleene = ' '.join([word+'*' for word in words.split()])
        with open(grammar_file, 'w') as out:
            out.write(jsgf_string%words_wkleene)
        return grammar_file

    @staticmethod
    def calculate(segment, decoded_words):
        ref, tar = needle(segment['words'].split(), decoded_words)
        # workaround since needle not working properly
        err_count = 0
        for w1, w2 in zip(ref, tar):
            if '--' not in [w1, w2] and w1 != w2:
                err_count += 1
            elif '--' in [w1, w2]:
                err_count += 1
        ref_count = len(segment['words'].split())
        return (1.0 - err_count/ref_count)
