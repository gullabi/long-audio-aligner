import sys
import os
import json
import yaml
import subprocess
import logging
import argparse

from itertools import repeat
from multiprocessing.dummy import Pool
from tqdm import tqdm
from datetime import datetime
from copy import deepcopy
from utils.align import Align, TMP
from utils.sphinx import CMU, DICT_FILE
from utils.text import Text
from utils.map import Map
from utils.segment import Segmenter
from utils.beam import Beam
from utils.geval import GEval
from utils.db import ParlaDB
from utils.segment_db import SegmentDB
from utils.convert import get_new_key

PROJECT_PATH = os.path.dirname(os.path.realpath(__file__)) 
MODEL_PATH = os.path.join(PROJECT_PATH, '../cmusphinx-models/ca-es')
DICT_PATH = os.path.join(MODEL_PATH, DICT_FILE)

def get_optimal_segments(intervention, mapped_alignment):
    # get segments using silences
    segmenter = Segmenter(mapped_alignment, t_min=4, t_max=15)
    segmenter.get_segments()

    # optimize segments using punctuation
    segmenter.optimize()
    return segmenter

def multiple(jsonfile, outdir):
    logging.info('loading all speakers in all sessions')
    interventions = json.load(open(jsonfile))
    for int_code, session in interventions.items():
        for intervention in session.values():
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

    if not intervention.get('words'):
        # create lm and convert audio
        align = Align(audiofile, text, DICT_PATH)
        if not align.results_exist():
            # if tmp exists uses the decode results from there
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
        else:
            with open(align.align_outfile) as res_file:
                alignment = json.load(res_file)

        # get punctuation and speaker information
        try:
            m = Map(intervention, alignment)
            m.prepare()

            intervention['words'] = m.alignment
        except Exception as e:
            msg = 'mapping alignment failed for %s'%audiofile
            logging.error(msg)
            logging.error(str(e))

    # unit segments from silences are combined into optimal segments btw 5-19 s
    # exception handling needed since multiple block per speaker not implemented
    # if the speaker does not speak most of his/her text in the first block it
    # is possible to end up with 0 segments
    try:
        segmenter = get_optimal_segments(intervention, intervention['words'])
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


def from_db(outdir, threads = 1, overwrite=False, collection='mas_v5'):
    if not os.path.isdir(outdir):
        msg = '%s is not a directory'%outdir
        raise IOError(msg)
    start = datetime.now()
    db = ParlaDB(collection_name=collection)
    db.connect()
    logging.info('loading the speakers from the db: %s'%collection)
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
            #if not overwrite and intervention.get('results'):
            if not overwrite and (intervention.get('words') and intervention.get('results')):
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

def segments_db(collection, threads = 1, option='parlament'):
    '''
    evaluates the score of the already existing segments in the db
    '''
    start = datetime.now()
    db = SegmentDB(collection, db_name=option)
    db.connect()
    count = db.collection.find().count()
    logging.info('%i segments found in collection'%count)
    logging.info('loading the segments from the db')
    process_list = []
    for segment in db.collection.find():
        segment_id = segment['_id']
        if option == 'parlament':
            value = segment['Innerfield']
        else:
            value = segment['value']
        if not value.get('segment_path'):
            msg = 'dictionary does not have key a path, something wrong'\
                  ' with the structure for the code for %s'%segment_id
            raise KeyError(msg)
        if value.get('score'):
            msg = '%s already processed in db, skipping'%segment_id
            logging.info(msg)
        else:
            process_list.append(segment)
    if threads == 1:
        print('starting single thread process')
        for segment in process_list:
            gevaluate_and_upsert(segment, db)
    else:
        with Pool(threads) as pool:
            with tqdm(total=len(process_list)) as pbar:
                for i, _ in tqdm(enumerate(pool.imap(gevaluate_and_upsert_star,
                                                     zip(process_list,
                                                         repeat(db))))):
                    pbar.update()
    end = datetime.now()
    print("It took: %s"%(end-start))

def gevaluate_and_upsert_star(in_db):
    return gevaluate_and_upsert(*in_db)

def gevaluate_and_upsert(segment, db):
    segment_id = segment['_id']
    results = gevaluate_pipeline(segment)
    if results:
        segment['value'] = {**segment['value'], **results}
        db.insert_one(segment_id, segment['value'], upsert=True)

def gevaluate_pipeline(segment):
    # grammar evaluate each segment
    geval = GEval([segment['value']], MODEL_PATH)
    geval.evaluate()

    # clean
    baseaudio = os.path.basename(segment['value']['segment_path'])
    outdir = os.path.dirname(segment['value']['segment_path'])
    outpath = os.path.join(outdir, baseaudio[:-4])
    subprocess.call('rm {0}*.jsgf {0}*.raw'.format(outpath), shell=True)
    return geval.segments[0]

if __name__ == "__main__":
    usage = 'usage: %(prog)s [options]'
    parser = argparse.ArgumentParser(description='long audio aligner',
                                     usage=usage)
    parser.add_argument("-o", "--outdir", dest="outdir", default=None,\
                        help="output directory", type=str)
    parser.add_argument("-f", "--file", dest="jsonfile", default=None,\
                        help="input file (json)", type=str)
    parser.add_argument("-s", "-segment_collection", dest="s_collection",\
                        default=None,
                        help="collection name for the db segments",
                        type=str)
    parser.add_argument("-c", "-collection", dest="collection",\
                        default=None,
                        help="collection name for the db interventions",
                        type=str)
    parser.add_argument("-r", "-overwrite", dest="overwrite",\
                        action="store_true",\
                        help="overwrite results")
    parser.add_argument("-t", "-threads", dest="threads",\
                        help="number of threads", type=int,
                        default=1)

    args = parser.parse_args()
    if args.collection and args.jsonfile:
        msg = "cannot have both collection and jsonfile"
        raise ValueError(msg)
    if not args.collection and not args.outdir:
        msg = 'output dir is needed for processing'
        raise ValueError(msg)

    logging_level = logging.INFO
    log_file = 'long_align.log'
    logging.basicConfig(filename=log_file,
                        format="%(asctime)s-%(levelname)s: %(message)s",
                        level=logging_level,
                        filemode='a')
    if args.outdir:
        if args.jsonfile:
            # from file
            multiple(args.jsonfile, args.outdir)
        elif args.collection:
            from_db(args.outdir, threads = args.threads,
                    collection=args.collection, overwrite=args.overwrite)
        else:
            print('either collection name or jsonfile necessary')
    elif args.s_collection:
        # for segment decode score evaluation
        segments_db(args.s_collection, threads = 3)
