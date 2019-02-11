import operator
import re

class Map(object):
    '''
    Post processes the word sequence with time stamps to add the
    target speaker and punctuation information using the original
    cleaned text of the intervention
    '''
    def __init__(self, intervention, alignment):
        self.intervention = intervention
        self.alignment = alignment
        self.full_text = ' '
        self.speaker_stats = {}
        corpus = []
        for speaker, text in intervention['text']:
            corpus.append(text)
            if not self.speaker_stats.get(speaker):
                self.speaker_stats[speaker] = 0
            self.speaker_stats[speaker] += len(text.split())
        self.full_text = ' '.join(corpus)

        self.target_speaker = None

        self.re_stop = re.compile('\.|:|\?|!')
        self.re_comma = re.compile(',|;')

    def prepare(self):
        self.check()
        self.find_speaker()
        self.enrich_alignment()

    def check(self):
        if len(self.full_text.split()) != len(self.alignment):
            msg = 'the original and cleaned text do not have equal tokens'
            raise ValueError(msg)

    def find_speaker(self):
        '''
        Finds the main (desired) speaker in the dictonary which can have the
        mesa or interruptions

        Currently operates under the assumption that there are no interruptions
        Extracts only the speaker with the most word tokens
        TODO mesa needs to be carried from past steps
        '''
        speakers_sorted = sorted(self.speaker_stats.items(), key=operator.itemgetter(1))
        self.target_speaker = speakers_sorted[-1][0]
        if 'president' in self.target_speaker.lower():
            msg = 'WARNING: could the target speaker be mesa?\n' + \
                  str(list(self.speaker_stats.keys()))
            print(msg)

    def enrich_alignment(self):
        '''
        Enriches the alignment dictionary with speaker and punctuation
        information.
        '''
        # create equivalent alignment dictionary from intervention dict
        reference_dicts = []
        if self.target_speaker == None:
            msg = ''
            raise ValueError()
        for speaker, text in self.intervention['text']:
            for word in text.split():
                token = {'word': word}
                if speaker == self.target_speaker:
                    token['target_speaker'] = True
                # Punctuation weights are used in segmentation search algorithm
                # commas get lower preference
                if self.re_stop.search(word):
                    token['punctuation'] = 1.0
                elif self.re_comma.search(word):
                    token['punctuation'] = 0.9
                reference_dicts.append(token)

        # assuming they are of the same length
        for reference, target in zip(reference_dicts, self.alignment):
            if not re.search(target['word'], reference['word'].lower()):
                msg = 'WARNING: %s vs %s target not in reference'\
                      %(target['word'], reference['word'])
                print(msg)
            for key in ['target_speaker', 'punctuation']:
                if reference.get(key):
                    target[key] = reference[key]
