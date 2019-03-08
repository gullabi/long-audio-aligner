import os
import re
import sys

from pymongo import MongoClient

NUM = re.compile('[0-9]')

def main(collection, option):
    client = MongoClient('localhost', 27017)
    if option == 'parlament':
        parlament_extract(collection, client)
    else:
        segment_extract(collection, client)

def segment_extract(collection, client):
    tables = client['segments']
    db = tables[collection]
    seg_key = 'values'
    seconds = 14400 # 4 hours
    score_tuple = [0.9, 0.8]
    cleans = get_segments(db, seg_key, 'clean', score_tuple, seconds)
    others = get_segments(db, seg_key, 'other', score_tuple, seconds)

    output(cleans, '_'.join([collection,'clean']))
    output(others, '_'.join([collection,'other']))

def get_segments(db, seg_key, option, score_tuple, max_seconds):
    segments = []
    lower_score, upper_score = score_tuple
    if option == 'clean':
        query = {"%s.score"%seg_key: {'$gte':upper_score}}
    elif option == 'other':
        query = {"%s.score"%seg_key: {'$gte':lower_score, '$lt':upper_score}}
    else:
        raise ValueError('unknown option for the query')
    total_duration = 0
    lost_duration = 0
    for segment in db.find(query):
        words = segment[seg_key]['words']
        # quick hack for switching between parlament and segments
        if seg_key == 'values':
            fileid, basename = get_pathid(segment[seg_key]['segment_path'])
        elif seg_key == 'Innerfield':
            basename = segment[seg_key]['segment']
            fileid = remove_ext(segment[seg_key]['segment_path'])
        else:
            raise ValueError('segment key %s unknown'%seg_key)
        duration = get_duration(basename)
        if not NUM.search(words):
            if duration > 20:
                lost_duration += duration
            else:
                segments.append([words, basename, fileid])
                total_duration += duration
        if total_duration > max_seconds:
            break
    if total_duration < max_seconds:
        print(max_seconds-total_duration, 'seconds missing')
    print('lost duration', lost_duration)
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
         open('test/%s.fileids'%name, 'w') as fid,\
         open('test/%s.filelist'%name, 'w') as flist:
        for segment in segments:
            tra_str = '<s> %s </s> (%s)\n'%(segment[0], segment[1])
            fid_str = '%s\n'%segment[2]
            flist_str = '%s.wav\n'%segment[2]
            tra.write(tra_str)
            fid.write(fid_str)
            flist.write(flist_str)

def parlament_extract(collection, client):
    tables = client['parlament']
    db = tables[collection]
    seg_key = 'Innerfield'
    score_tuple = [0.7, 0.89]
    clean_seconds = 324000 # 90 hours
    other_seconds = 828000 # 230 hours
    cleans = get_segments(db, seg_key, 'clean', score_tuple, clean_seconds)
    others = get_segments(db, seg_key, 'other', score_tuple, other_seconds)

    name = 'parlament_v1.0'
    output(cleans, '_'.join([name,'clean']))
    output(others, '_'.join([name,'other']))

if __name__ == "__main__":
    collection = sys.argv[1]
    option = 'parlament'
    if collection == None:
        raise ValueError('colllection not given')
    main(collection, option)
