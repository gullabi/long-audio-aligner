import os
import re
import sys

from pymongo import MongoClient

NUM = re.compile('[0-9]')

def main(collection):
    client = MongoClient('localhost', 27017)
    tables = client['segments']
    db = tables[collection]
    cleans = get_segments(db, option = 'clean')
    others = get_segments(db, option = 'other')

    output(cleans, '_'.join([collection,'clean']))
    output(others, '_'.join([collection,'other']))

def get_segments(db, option = 'clean'):
    segments = []
    if option == 'clean':
        query = {"value.score": {'$gte':0.9}}
    elif option == 'other':
        query = {"value.score": {'$gte':0.8, '$lt':0.9}}
    else:
        raise ValueError('unknown option for the query')
    total_duration = 0
    for segment in db.find(query):
        words = segment['value']['words']
        fileid, basename = get_pathid(segment['value']['segment_path'])
        duration = get_duration(basename)
        if not NUM.search(words):
            segments.append([words, basename, fileid])
            total_duration += duration
        if total_duration > 14400:
            break
    return segments

def get_pathid(path):
    dirs = path.split('/')
    rel_path = '/'.join(dirs[dirs.index('wav')+1:])
    return remove_ext(rel_path), remove_ext(dirs[-1])

def remove_ext(string):
    return '.'.join(string.split('.')[:-1])

def get_duration(basename):
    start, end = basename.split('_')[-2:]
    return float(end) - float(start)

def output(segments, name):
    with open('test/%s.transcription'%name, 'w') as tra,\
         open('test/%s.fileids'%name, 'w') as fid:
        for segment in segments:
            tra_str = '<s> %s </s> (%s)\n'%(segment[0], segment[1])
            fid_str = '%s\n'%segment[2]
            tra.write(tra_str)
            fid.write(fid_str)

if __name__ == "__main__":
    collection = sys.argv[1]
    main(collection)
