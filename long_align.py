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
from utils.geval import GEval

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

    # unit segments from silences are combined into optimal segments btw 5-19 s
    segmenter = get_optimal_segments(intervention, alignment)

    # segment audiofile
    segmenter.segment_audio('test/c3d9d2a15a76a9fbb591.mp3')
    segment_out = os.path.join(TMP, align.audio_basename+'_beam_search.json')
    with open(segment_out, 'w') as out:
        json.dump(segmenter.best_segments, out, indent = 4)

    # grammar evaluate each segment
    geval = GEval(segmenter.best_segments, MODEL_PATH)
    geval.evaluate()
    segment_out = os.path.join(TMP, align.audio_basename+'_evaluated.json')
    with open(segment_out, 'w') as out:
        json.dump(segmenter.best_segments, out, indent = 4)

def get_optimal_segments(intervention, alignment):
    # get punctuation and speaker information
    m = Map(intervention, alignment)
    m.prepare()

    # get segments using silences
    segmenter = Segmenter(m.alignment)
    segmenter.get_segments()

    # optimize segments using punctuation
    segmenter.optimize()
    return segmenter

if __name__ == "__main__":
    audiofile = sys.argv[1]
    yamlfile = sys.argv[2]
    main(audiofile, yamlfile)
