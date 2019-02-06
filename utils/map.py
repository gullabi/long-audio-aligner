class Map(object):
    def __init__(self, intervention, alignment):
        self.intervention = intervention
        self.alignment = alignment
        self.full_text = ' '
        speakers = []
        corpus = []
        for speaker, text in intervention['text']:
            corpus.append(text)
            speakers.append(speaker)
        self.full_text = ' '.join(corpus)
        self.speakers = set(speakers)

    def prepare(self):
        self.check()
        self.find_speaker()

    def check(self):
        if len(self.full_text.split()) != len(self.alignment):
            msg = 'the original and cleaned text do not have equal tokens'
            raise ValueError(msg)

    def find_speaker(self):
        pass
