import operator
import re
import logging

from utils import recuperate_punct

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
        self.align()

    def check(self):
        if len(self.full_text.split()) != len(self.alignment):
            msg = 'the original and cleaned text do not have equal tokens'\
                  '\ncleaning the tokens not present in cmu cleaned text'
            logging.warning(msg)
            # remove the tokens not appearing in full_text
            # assumes len(self.full_text.split()) > len(self.alignment)
            # this might happen when symbols surrounded by white spaces
            # appear in the full_text
            i = 0
            skip = 0
            new_int_text = []
            for speaker, text in self.intervention['text']:
                int_text = ''
                for word in text.split():
                    if re.search(self.alignment[i+skip]['word'], word.lower()):
                        int_text += ' %s'%word
                    else:
                        msg = "%s does not appear in clean text"%word
                        logging.warning(msg)
                        skip -= 1
                    i += 1
                new_int_text.append((speaker, int_text))
            self.intervention['text'] = new_int_text

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
            msg = 'could the target speaker be mesa?\n' + \
                  str(list(self.speaker_stats.keys()))
            logging.warning(msg)

    def enrich_alignment(self):
        '''
        Enriches the alignment dictionary with speaker and punctuation
        information.
        '''
        # create equivalent alignment dictionary from intervention dict
        reference_dicts = []
        if self.target_speaker == None:
            msg = 'non existent target speaker in mapping'
            logging.error(msg)
            raise ValueError(msg)
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
                msg = '%s vs %s target not in reference'\
                      %(target['word'], reference['word'])
                logging.warning(msg)
            for key in ['target_speaker', 'punctuation']:
                if reference.get(key):
                    target[key] = reference[key]

    def align(self):
        alignment_words = [token['word'] for token in self.alignment]
        # create a list of tuples cleaned vs original word
        text_clean_tuples = recuperate_punct.clean(self.full_text)
        clean_words =  [cl for cl, tx in text_clean_tuples]

        diff_wc = abs(len(text_clean_tuples)-len(alignment_words))
        if diff_wc > 5:
            logging.warning('word count difference is large: %i'%diff_wc)

        # align words from decode with the clean_words
        # first do the alignment with the clean versions in the text_clean_tuples
        align_seq = recuperate_punct.needle(clean_words, alignment_words)
        clean_aligned, full_text_aligned = align_seq
        # create the aligned version with the original words using text_clean_tuples
        original_aligned = recuperate_punct.get_original(clean_aligned,
                                                         text_clean_tuples)
        # no of decoded words will always be greater or equal to the original
        # hence it is necessary to find where the decode starts and ends
        # TODO might be unnecessary bcs alignment already has non decoded words
        i_start, i_end = recuperate_punct.get_start_end_indices(full_text_aligned)
        self.original_align_seq = list(zip(original_aligned[i_start:i_end+1],
                                      full_text_aligned[i_start:i_end+1]))
        recuperate_punct.get_original_alignment(self.alignment, self.original_align_seq)
