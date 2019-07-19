import os
import re
import logging
import yaml
import operator
import utils.clean as cl
from utils.seq_aligner import needle, water

#from itertools import repeat
#from pymongo import MongoClient

DOT = re.compile('(?<=[^l])·(?=[^l])')

def main():
    '''
    db = db_connect()
    db_int = db_connect(col='mas')
    re_intervention = {} 
    for element in db.find():
        id_int = element['field_id']
        if not re_intervention.get(id_int):
            re_intervention[id_int] = {}
            re_intervention[id_int]['text'] = db_int.find_one({'_id':id_int})['value']['text']
            re_intervention[id_int]['segments'] = []
        keys = ['start','end','words']
        segment = {key:element['Innerfield'][key] for key in keys}
        re_intervention[id_int]['segments'].append(segment)
    '''

    #output()
    re_intervention = yaml.load(open('scripts/test.yml'), yaml.FullLoader)
    recuperate(re_intervention)

def db_connect(col='aggregate_mas'):
    client = MongoClient('localhost',27017)
    dbname = 'parlament'
    colname = col
    db = client[dbname]
    return db[colname]

def output():
    with open('test.yml', 'w') as out:
        yaml.dump(re_intervention, out)

def recuperate(interventions):
    for id_int, intervention in interventions.items():
        print(id_int)
        align(intervention)

def align(intervention):
    segments = intervention['segments']
    segment_list = [segment['words'] for segment in sorted(segments,
                                             key=operator.itemgetter('start'))]
    text = get_text(intervention['text']) # TODO dangerous
    text_clean_tuples = clean(text)

    s_wc = get_segment_word_count(segment_list)
    dif_wc = abs(s_wc-len(text_clean_tuples))
    if dif_wc > 5:
        print('WARNING: word count difference is large: %i'%dif_wc)
    else:
        clean_words = [cl for cl, tx in text_clean_tuples]
        segment_words = []
        for segment in segment_list:
            segment_words += segment.split()
        align_seq = needle(clean_words, segment_words)
        clean_aligned, segment_aligned = align_seq
        original_aligned = get_original(clean_aligned, text_clean_tuples)
        i_start, i_end = get_start_end_indices(segment_aligned)
        original_align_seq = list(zip(original_aligned[i_start:i_end+1],
                                      segment_aligned[i_start:i_end+1]))
        #print(list(zip(clean_aligned, segment_aligned)))
        #print(original_align_seq)
        if '--' in original_align_seq[0] or '--' in original_align_seq[1]:
            print(original_align_seq)
            return None
        else:
            get_original_segments(segments, original_align_seq)

def get_text(intervention_text):
    if len(intervention_text) > 1:
        return intervention_text[1][1]
    else:
        return intervention_text[0][1]

def clean(text):
    cl_text = cl.structure_clean(text)
    cl_text = cl.punctuation_normalize(cl_text)
    cl_text = cl.reject.sub('', cl_text.lower())
    if len(cl_text.split()) != len(text.split()):
        print('WARNING: cleaned worded count is not equal to original '\
              '%i vs %i'%(len(cl_text.split()),len(text.split())))
        raise NotImplementedError("no solution yet")
    else:
        return list(zip(cl_text.strip().split(), text.split()))

def get_segment_word_count(s_list):
    count = 0
    for s in s_list:
        count += len(s.split())
    return count

def get_original(aligned_t0, tuple_list):
    reverse_aligned_t1 = []
    for t in aligned_t0[::-1]:
        if t == '--':
            reverse_aligned_t1.append('--')
        elif t == tuple_list[-1][0]:
            reverse_aligned_t1.append(tuple_list[-1][1])
            tuple_list.pop()
        else:
            print('WARNING')
    return reverse_aligned_t1[::-1]

def get_start_end_indices(aligned):
    # assumes non aligned tokens are --
    if not aligned:
        raise ValueError("input sequence empty for start and end calculation")
    for i, el in enumerate(aligned):
        if el != '--':
            start = i
            break

    for i, el in reversed(list(enumerate(aligned))):
        if el != '--':
            end = i
            break

    if start == len(aligned) or end == 0:
        print(start, end)
        raise ValueError('finding the start and end index did'\
                         ' not work for %s'%str(aligned))
    return start, end

def get_original_segments(segments, aligned_tuples):
    for segment in sorted(segments, key=operator.itemgetter('start')):
        original_words = []
        original_words_clean = []
        for word in segment['words'].split():
            if word == aligned_tuples[0][1]:
                original_words.append(aligned_tuples[0][0])
                original_words_clean.append(recover_punc(aligned_tuples[0][0],
                                                         word))
                #print(aligned_tuples[0][0], word)
                aligned_tuples.pop(0)
            else:
                print(segments, aligned_tuples[:5])
                raise ValueError('word not found in the following index')
        segment['original_words'] = ' '.join(original_words)
        print('%s\n%s'%(segment['words'],segment['original_words']))

def recover_punc(original, clean):
    # recovers punctuation from aligned tokens
    # cases:
    # punctuation signs: , . ... ! ? : ; –
    # first letter capitalized
    # all letters capitalized
    pass

if __name__ == "__main__":
    logging_level = logging.INFO
    log_file = 'clean.log'
    logging.basicConfig(filename=log_file,
                        format="%(asctime)s-%(levelname)s: %(message)s",
                        level=logging_level,
                        filemode='w')
    main()

