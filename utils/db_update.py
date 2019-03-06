import sys
import re

from pymongo import MongoClient
from bson.objectid import ObjectId

def main(dbname, colname, filename):
    client = MongoClient('localhost',27017)
    db = client[dbname]
    col = db[colname]

    keys, data = read_file(filename)
    for d in data:
        match = re.search('ObjectId\((.+)\)', d[0])
        if match:
            idno = match.groups()[0]
            el = col.find_one({'_id':ObjectId(idno)})
            if el:
                levels = keys[1].split('.')
                if len(levels) == 1:
                    el[keys[1]] = d[1]
                elif len(levels) == 2:
                    el[levels[0]][levels[1]] = d[1]
                else:
                    msg = '%s cannot handle more than 2 levels'%keys[1]
                    raise ValueError(msg)
                col.update({'_id':ObjectId(idno)},
                           el, upsert=True)

def read_file(filename):
    elements = [line.strip().split(',') for line in open(filename).readlines()]
    keys = elements[0]
    return keys, elements[1:]

if __name__ == "__main__":
    db = sys.argv[1]
    col = sys.argv[2]
    filename = sys.argv[3]
    main(db, col, filename)
