import sys
import os
import json

from utils.align import Align, TMP
from utils.sphinx import CMU
from utils.text import Text

PROJECT_PATH = os.path.dirname(os.path.realpath(__file__)) 
MODEL_PATH = os.path.join(PROJECT_PATH, '../cmusphinx-models/ca-es')
DICT_PATH = os.path.join(MODEL_PATH, 'pronounciation-dictionary.dict')

def main(audiofile, textfile):
    align = Align(audiofile, textfile, DICT_PATH)
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
    else:
        msg = 'results already exist in %s'%align.align_outfile
        print(msg)

if __name__ == "__main__":
    audiofile = sys.argv[1]
    textfile = sys.argv[2]
    main(audiofile, textfile)
