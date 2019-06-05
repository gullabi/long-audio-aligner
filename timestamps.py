import os
import json
import subprocess
import logging

from math import floor
from itertools import repeat
from pymongo import MongoClient
from multiprocessing.dummy import Pool
from tqdm import tqdm

from long_align import get_optimal_segments

def main():
    db = db_connect()
    outdir = './'
    threads = 1
    process_list = []
    for element in db.find():
        #if not element['value'].get('words'):
        process_list.append(element)

    logging.info('sending the list to be processed')
    if threads == 1:
        for element in process_list:
            logging.info(element['value']['ple_code'])
            try:
                commit(element, db)
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

def commit(element, db):
    alignment = element['value']['words']
    segmenter = get_optimal_segments(element['value'], alignment)
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
