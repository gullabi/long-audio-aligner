import sys
import os
import json
import yaml
import subprocess

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

def single(audiofile, yamlfile, outdir):
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
            print('decoding for long alignment')
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
    segmenter.segment_audio(audiofile, base_path=outdir)
    segment_out = os.path.join(TMP, align.audio_basename+'_beam_search.json')
    with open(segment_out, 'w') as out:
        json.dump(segmenter.best_segments, out, indent = 4)

    # grammar evaluate each segment
    geval = GEval(segmenter.best_segments, MODEL_PATH)
    geval.evaluate()
    segment_out = os.path.join(TMP, align.audio_basename+'_evaluated.json')
    with open(segment_out, 'w') as out:
        json.dump(segmenter.best_segments, out, indent = 4)

    # clean
    baseaudio = os.path.basename(audiofile)
    outpath = os.path.join(outdir, baseaudio[0], baseaudio[1], baseaudio[:-4])
    subprocess.call('rm {0}*.jsgf {0}*.raw'.format(outpath), shell=True)

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

def multiple(jsonfile, outdir):
    print('loading all speakers in all sessions')
    sessions = json.load(open(jsonfile))
    for ple_code, session in sessions.items():
        for yaml, intervention in session.items():
            if len(intervention['urls']) > 1:
                print("%s multiple audio file, skipping"%intervention['urls'])
            elif intervention['urls'][0][1] == None:
                print('no audio uri for %s'%yaml)
            else:
                text = ' '.join([text for sp, text in intervention['text']])
                intervention['results'] = process_pipeline(intervention, outdir)
    with open(jsonfile.replace('.json','_res.json'), 'w') as out:
        json.dump(sessions, out)

def process_pipeline(intervention, outdir):
    text = ' '.join([text for sp, text in intervention['text']])

    # assumes there is a single audio uri
    audiofile = intervention['urls'][0][1]
    print('* %s'%audiofile)

    # create lm and convert audio
    align = Align(audiofile, text, DICT_PATH)
    align.create_textcorpus()
    align.create_lm()
    align.convert_audio()

    # run pocketsphinx
    cs = CMU(MODEL_PATH)
    print('decoding for long alignment')
    cs.decode(align.audio_raw, align.lm)
    segs = cs.segs

    # TODO call decode functions in Align object
    decode_align = Text(align.sentences, segs, align.align_outfile)
    decode_align.align()
    alignment = decode_align.align_results

    # unit segments from silences are combined into optimal segments btw 5-19 s
    segmenter = get_optimal_segments(intervention, alignment)

    # segment audiofile
    segmenter.segment_audio(audiofile, base_path=outdir)

    # grammar evaluate each segment
    geval = GEval(segmenter.best_segments, MODEL_PATH)
    geval.evaluate()

    # clean
    baseaudio = os.path.basename(audiofile)
    outpath = os.path.join(outdir, baseaudio[0], baseaudio[1], baseaudio[:-4])
    subprocess.call('rm {0}*.jsgf {0}*.raw'.format(outpath), shell=True)
    return segmenter.best_segments

if __name__ == "__main__":
    if len(sys.argv) == 4:
        audiofile = sys.argv[1]
        yamlfile = sys.argv[2]
        outdir = sys.argv[3]
        single(audiofile, yamlfile, outdir)
    elif len(sys.argv) == 3:
        jsonfile = sys.argv[1]
        outdir = sys.argv[2]
        multiple(jsonfile, outdir)
    else:
        msg = 'long_align accepts either 3 (audio + yaml + outdir)'\
              ' or 2 (json with the local audio uri + outdir) options'
        print(msg)
        sys.exit()

    if not os.path.isdir(outdir):
        msg = '%s does not exist or is not dir'%outdir
        raise IOError(msg)
