import sys
import os
import json
import yaml

from utils.align import Align, TMP
from utils.sphinx import CMU
from utils.text import Text
from utils.map import Map
from utils.segment import Segmenter
from utils.beam import Beam

PROJECT_PATH = os.path.dirname(os.path.realpath(__file__)) 
MODEL_PATH = os.path.join(PROJECT_PATH, '../cmusphinx-models/ca-es')
DICT_PATH = os.path.join(MODEL_PATH, 'pronounciation-dictionary.dict')

def main(audiofile, yamlfile):
    intervention = yaml.load(open(yamlfile))
    text = ' '.join([text for sp, text in intervention['text']])
    align = Align(audiofile, text, DICT_PATH)
    if not align.results_exist():
        align.create_textcorpus()
        align.create_lm()
        align.convert_audio()
        decode_outfile = os.path.join(TMP, align.audio_basename+'_decode.json')
        if not os.path.isfile(decode_outfile):
            cs = CMU(MODEL_PATH)
            cs.decode(align.audio_raw, align.lm)
            segs = cs.segs
            with open(decode_outfile, 'w') as out:
                json.dump(segs, out)
        else:
            segs = json.load(open(decode_outfile))
        # TODO call decode functions in Align object
        decode_align = Text(align.sentences, segs, align.align_outfile)
        decode_align.align()
        alignment = decode_align.align_results
    else:
        msg = 'results already exist in %s'%align.align_outfile
        print(msg)
        alignment = json.load(open(align.align_outfile))

    m = Map(intervention, alignment)
    m.prepare()

    segments = beam_search(m.alignment, 10)
    segment_out = os.path.join(TMP, align.audio_basename+'_beam_search.json')
    with open(segment_out, 'w') as out:
        json.dump(segments, out, indent = 4)

def beam_search(alignment, width):
    segmenter = Segmenter(alignment)
    segmenter.get_segments()
    beam = Beam(width)
    for segment in segmenter.segments:
        beam.add(segment)
    # sequences are ordered according to the score
    # and the first element has the best score
    return beam.sequences[0]

if __name__ == "__main__":
    audiofile = sys.argv[1]
    yamlfile = sys.argv[2]
    main(audiofile, yamlfile)
