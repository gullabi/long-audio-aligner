import sys
import os
import json
import yaml
import subprocess
import logging

from itertools import repeat
from multiprocessing.dummy import Pool
from tqdm import tqdm
from datetime import datetime
from utils.align import Align, TMP
from utils.sphinx import CMU
from utils.text import Text
from utils.map import Map
from utils.segment import Segmenter
from utils.beam import Beam
from utils.geval import GEval
from utils.db import ParlaDB
from utils.convert import get_new_key

PROJECT_PATH = os.path.dirname(os.path.realpath(__file__)) 
MODEL_PATH = os.path.join(PROJECT_PATH, '../cmusphinx-models/ca-es')
DICT_PATH = os.path.join(MODEL_PATH, 'pronounciation-dictionary.dict')

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
    logging.info('loading all speakers in all sessions')
    interventions = json.load(open(jsonfile))
    for int_code, intervention in interventions.items():
        if len(intervention['urls']) > 1:
            msg = "%s multiple audio file, skipping"%intervention['urls']
            logging.info(msg)
        elif intervention['urls'][0][1] == None:
            msg = 'no audio uri for %s'%int_code
            logging.info(msg)
        else:
            intervention['results'] = process_pipeline(intervention, outdir)
    with open(jsonfile.replace('.json','_res.json'), 'w') as out:
        json.dump(interventions, out, indent=2)

def process_pipeline(intervention, outdir):
    text = ' '.join([text for sp, text in intervention['text']])

    # assumes there is a single audio uri
    audiofile = intervention['urls'][0][1]
    logging.info('* %s'%audiofile)
    if not text:
        msg = '%s has empty text'%audiofile
        logging.error(msg)
        return []

    # create lm and convert audio
    align = Align(audiofile, text, DICT_PATH)
    align.create_textcorpus()
    align.create_lm()
    align.convert_audio()

    # run pocketsphinx
    cs = CMU(MODEL_PATH)
    logging.info('decoding for long alignment')
    try:
        cs.decode(align.audio_raw, align.lm)
    except Exception as e:
        msg = '%s decoding failed'%audiofile
        logging.error(msg)
        logging.error(str(e))
        return []
    segs = cs.segs

    # TODO call decode functions in Align object
    decode_align = Text(align.sentences, segs, align.align_outfile)
    decode_align.align()
    alignment = decode_align.align_results

    # unit segments from silences are combined into optimal segments btw 5-19 s
    # exception handling needed since multiple block per speaker not implemented
    # if the speaker does not speak most of his/her text in the first block it
    # is possible to end up with 0 segments
    try:
        segmenter = get_optimal_segments(intervention, alignment)
    except Exception as e:
        msg = 'segmentation not possible for %s'%audiofile
        logging.error(msg)
        logging.error(str(e))
        return []

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

def from_db(outdir, threads = 1):
    if not os.path.isdir(outdir):
        msg = '%s is not a directory'%outdir
        raise IOError(msg)
    start = datetime.now()
    db = ParlaDB()
    db.connect()
    logging.info('loading the speakers from the db')
    process_list = []
    for value in db.collection.find():
        ple_code = value['value']['ple_code']
        int_code = get_new_key(ple_code, value['value']['source'])
        intervention = value['value']
        if not intervention.get('urls'):
            msg = 'dictionary does not have key urls, something wrong'\
                  ' with the structure for the code for %s'%value['value']['source']
            raise KeyError(msg)
        if len(intervention['urls']) > 1:
            msg = "%s multiple audio file, skipping"%intervention['urls']
            logging.info(msg)
        elif intervention['urls'][0][1] == None:
            msg = 'no audio uri for %s'%int_code
            logging.info(msg)
        else:
            if intervention.get('results'):
                msg = '%s already processed in db, skipping'%int_code
                logging.info(msg)
            else:
                process_list.append(intervention)
    if threads == 1:
        print('starting single thread process')
        for intervention in process_list:
            process_and_upsert(intervention, outdir, db)
    else:
        with Pool(threads) as pool:
            with tqdm(total=len(process_list)) as pbar:
                for i, _ in tqdm(enumerate(pool.imap(process_and_upsert_star,
                                                     zip(process_list,
                                                         repeat(outdir),
                                                         repeat(db))))):
                    pbar.update()
    end = datetime.now()
    print("It took: %s"%(end-start))

def process_and_upsert_star(int_out_db):
    return process_and_upsert(*int_out_db)

def process_and_upsert(intervention, outdir, db):
    int_code = get_new_key(intervention['ple_code'], intervention['source'])
    results = process_pipeline(intervention, outdir)
    if results:
        intervention['results'] = results
        db.insert_one(int_code, intervention, upsert=True)

if __name__ == "__main__":
    #TODO put argparse

    logging_level = logging.INFO
    log_file = 'long_align.log'
    logging.basicConfig(filename=log_file,
                        format="%(asctime)s-%(levelname)s: %(message)s",
                        level=logging_level,
                        filemode='a')

    if len(sys.argv) == 4:
        audiofile = sys.argv[1]
        yamlfile = sys.argv[2]
        outdir = sys.argv[3]
        single(audiofile, yamlfile, outdir)
    elif len(sys.argv) == 3:
        jsonfile = sys.argv[1]
        outdir = sys.argv[2]
        multiple(jsonfile, outdir)
    elif len(sys.argv) == 2:
        outdir = sys.argv[1]
        from_db(outdir, threads = 1)
    else:
        msg = 'long_align accepts either 3 (audio + yaml + outdir)'\
              ' or 2 (json with the local audio uri + outdir) options'
        print(msg)
        sys.exit()
