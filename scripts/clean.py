import os
import re
import subprocess
import logging

from math import floor
from itertools import repeat
from pymongo import MongoClient
from multiprocessing.dummy import Pool
from tqdm import tqdm

RE_DOT = '((?<=[^l])·(?=[^l])|(?<=[^l])·|·(?=[^l]))'
DOT = re.compile(RE_DOT)
S = '(?=[,.?!: ])'

def main():
    clean('intervention')

def clean(option):
    if option == 'intervention':
        db = db_connect('v3')
    else:
        db = db_connect('aggregate_mas_v2')

    outdir = './'
    process_list = []
    for element in db.find():
        process_list.append(element)

    logging.info('sending the list to be processed')
    c_tuples = get_clean_list()

    if option == 'intervention':
        for ct in c_tuples:
            print(ct)
            for element in db.find():
                for i, speaker_text in enumerate(element['value']['text']):
                    speaker, text = speaker_text
                    find = re.search(ct[0], text)
                    if find:
                        #print(text)
                        element['value']['text'][i][1] = re.sub(ct[0], ct[1], text)
                        db.save(element)
        for element in db.find():
            for i, speaker_text in enumerate(element['value']['text']):
                speaker, text = speaker_text
                find = re.search(RE_DOT, text)
                if find:
                    if find.start()-10 < 0:
                        start = 0
                    else:
                        start = find.start()-10
                    print(text[start:start+20])
                    element['value']['text'][i][1] = DOT.sub('', text)
                    db.save(element)
    else:
        for c_t in c_tuples:
            print(c_t)
            for element in db.find({'Innerfield.words':{'$regex': c_t[0]}}):
                element['Innerfield']['words'] = \
                              element['Innerfield']['words'].replace(c_t[0],c_t[1])
                db.save(element)
        for element in db.find({'Innerfield.words':{'$regex': RE_DOT}}):
            element['Innerfield']['words'] = \
                                        DOT.sub('', element['Innerfield']['words'])
            db.save(element)

def get_clean_list():
    return [(' miler'+S, ' mi '),
            ('-un'+S,'-u'),
            ('·li'+S,'-li'),
            ('·hi'+S,'-hi'),
            ('·la'+S,'-la'),
            ('·i·','-i-'),
            ('to· te','tote'),
            ('·ne'+S,'-ne'),
            ('·me'+S,'-me'),
            ('·te'+S,'-te'),
            ('·ho'+S,'-ho'),
            ('·lo'+S,'-lo'),
            ('·nos'+S,'-nos'),
            ('·vos'+S,'-vos'),
            ('·los'+S,'-los'),
            ('·les'+S,'-les'),
            ('·se'+S,'-se'),
            ('·u'+S,'-u'),
            ('no·soluci','no-soluci'),
            ('sánchez·camacho','sánchez-camacho'),
            ('·dos'+S,'-dos'),
            ('·tres'+S,'-tres'),
            ('·quatre'+S,'-quatre'),
            ('·cinc'+S,'-cinc'),
            ('·sis'+S,'-sis'),
            ('·set'+S,'-set'),
            ('·vuit'+S,'-vuit'),
            ('·nou'+S,'-nou'),
            ('a·bandera','a bandera'),
            ('·(?=[A-ZÀÁÉÈÜÚÍÏÓÒÇ])', ' ')]

def db_connect(colname):
    client = MongoClient('localhost',27017)
    dbname = 'parlament'
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

