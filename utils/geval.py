jsgf_string = '''#JSGF V1.0;
grammar sentence;
public <sentence> = %s;
'''

class GEval(object):
    '''
    GEval: Grammar evaluate with pocketsphinx.

    Accepts segments dictionary and returns the same dictionary with scores
    '''
    def __init__(self, segments):
        self.segments = segments
        # initialize ps config

    def evaluate(self):
        # TODO implement multithreaded process here
        for segment in self.segments:
            score = self.evaluate_segment(segment)

    def evaluate_segment(self, segment):
        self.create_jsgf(segment)
        return 0

    @staticmethod
    def create_jsgf(segment):
        grammar_file = segment['segment_path'].replace('.wav','.jsgf')
        words = segment['words']
        words_wkleene = ' '.join([word+'*' for word in words.split()])
        with open(grammar_file, 'w') as out:
            out.write(jsgf_string%words_wkleene)
