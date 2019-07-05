import os
import re
import subprocess
import logging

from math import floor
from itertools import repeat
from pymongo import MongoClient
from multiprocessing.dummy import Pool
from tqdm import tqdm

DOT = re.compile('(?<=[^l])·(?=[^l])')

def main():
    db = db_connect()
    outdir = './'
    process_list = []
    for element in db.find():
        process_list.append(element)

    logging.info('sending the list to be processed')
    c_tuples = get_clean_list()

    for c_t in c_tuples:
        print(c_t)
        for element in db.find({'Innerfield.words':{'$regex': c_t[0]}}):
            element['Innerfield']['words'] = \
                          element['Innerfield']['words'].replace(c_t[0],c_t[1])
            db.save(element)
    for element in db.find({'Innerfield.words':{'$regex': '[^l]·[^l]'}}):
        element['Innerfield']['words'] = \
                                    DOT.sub('', element['Innerfield']['words'])
        db.save(element)

def get_clean_list():
    return [(' miler ', ' mil '),
            ('-un ','-u '),
            ('·li ','-li '),
            ('·hi ','-hi '),
            ('·la ','-la '),
            ('·i·','-i-'),
            ('to· te','tote'),
            ('·ne ','-ne '),
            ('·me ','-me '),
            ('·te ','-te '),
            ('·ho ','-ho '),
            ('·lo ','-lo '),
            ('·nos ','-nos '),
            ('·vos ','-vos '),
            ('·los ','-los '),
            ('·se ','-se '),
            ('no·soluci','no-soluci'),
            ('sánchez·camacho','sánchez camacho')]

def db_connect():
    client = MongoClient('localhost',27017)
    dbname = 'parlament'
    colname = 'aggregate_mas_v2'
    db = client[dbname]
    return db[colname]

if __name__ == "__main__":
    logging_level = logging.INFO
    log_file = 'clean.log'
    logging.basicConfig(filename=log_file,
                        format="%(asctime)s-%(levelname)s: %(message)s",
                        level=logging_level,
                        filemode='w')
    main()

