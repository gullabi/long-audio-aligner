import os
import json
import subprocess
import logging

from math import floor
from itertools import repeat
from pymongo import MongoClient
from multiprocessing.dummy import Pool
from tqdm import tqdm

from long_align import get_optimal_segments,\
                       GEval,\
                       MODEL_PATH

def main():
    db = db_connect()
    outdir = './sessions_mas'
    threads = 4
    process_list = []
    for element in db.find():
        #if not element['value'].get('words'):
        if element['value'].get('results'):
            for result in element['value'].get('results'):
                if not result.get('score'):
                    process_list.append(element)
                    break

    logging.info('sending the list to be processed')
    if threads == 1:
        for element in process_list:
            logging.info(element['value']['ple_code'])
            try:
                commit(element, db, outdir)
            except Exception as e:
                logging.error(e)
    else:
        with Pool(threads) as pool:
            with tqdm(total=len(process_list)) as pbar:
                for i, _ in tqdm(enumerate(pool.imap(commit_all_star,
                                                     zip(process_list,
                                                         repeat(db),
                                                         repeat(outdir))))):
                    pbar.update()
        pass

def insert_words(element, db):
    uri = element['value']['urls'][0][1]
    filepath = get_file(uri)
    ts = json.load(open(filepath))
    element['value']['words'] = ts
    db.update({'_id': element['_id']},
              element, upsert=True)

def get_file(uri):
    base = os.path.join('tmp', '/'.join(uri.split('/')[-3:]))
    return base.replace('.mp3','_align.json')

def commit(element, db, outdir):
    intervention = element['value']
    alignment = intervention['words']
    audiofile = intervention['urls'][0][1]

    # unit segments from silences are combined into optimal segments btw 5-10 s
    # exception handling needed since multiple block per speaker not implemented
    # if the speaker does not speak most of his/her text in the first block it
    # is possible to end up with 0 segments
    try:
        segmenter = get_optimal_segments(intervention, alignment)
    except Exception as e:
        msg = 'segmentation not possible for %s'%audiofile
        logging.error(msg)
        logging.error(str(e))
        segmenter = []

    if segmenter:
        # segment audiofile
        segmenter.segment_audio(audiofile, base_path=outdir)

        # grammar evaluate each segment
        geval = GEval(segmenter.best_segments, MODEL_PATH)
        geval.evaluate()

        # clean
        baseaudio = os.path.basename(audiofile)
        outpath = os.path.join(outdir, baseaudio[0], baseaudio[1], baseaudio[:-4])
        subprocess.call('rm {0}*.jsgf {0}*.raw'.format(outpath), shell=True)

        element['value']['results'] = segmenter.best_segments
        db.update({'_id': element['_id']},
                  element, upsert=True)

def commit_all_star(process_outdir):
    return commit(*process_outdir)

def db_connect():
    client = MongoClient('localhost',27017)
    dbname = 'parlament'
    colname = 'mas'
    db = client[dbname]
    return db[colname]

if __name__ == "__main__":
    logging_level = logging.INFO
    log_file = 'timestamps.log'
    logging.basicConfig(filename=log_file,
                        format="%(asctime)s-%(levelname)s: %(message)s",
                        level=logging_level,
                        filemode='w')
    main()
