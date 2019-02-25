import logging
import json
import sys

from pymongo import MongoClient

def batch_insert(filename, db_name, collection):
    sdb = SegmentDb(db_name, collection)
    sdb.connect()
    segments = json.load(open(filename))
    sdb.insert(segments)

class SegmentDb(object):
    def __init__(self, db_name, collection):
        self.db_name = db_name
        self.collection_name = collection

    def connect(self):
        client = MongoClient('localhost', 27017)
        self.db = client[self.db_name]
        self.collection = self.db[self.collection_name]

    def insert(self, elements):
        for key, value in elements.items():
            self.insert_one(key, value)

    def insert_one(self, key, value, upsert=True):
        ref = self.collection.find_one({'_id': key})
        if ref:
            if upsert:
                self.collection.update({'_id': key},
                                       {'_id': key,
                                        'value': value},
                                       upsert=True)
            else:
                logging.info('%s already in db skipping'%key)
        else:
            self.collection.insert({'_id': key,
                                    'value': value})

    def get(self, segment_id):
        ref = self.collection.find_one({'_id': segment_id})
        if ref:
            return ref
        else:
            return None

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print('usage: utils/segment_db.py <filename> <db_name> <collection>')
        msg = 'one of the arguments missing'
        raise ValueError(msg)
       
    filename = sys.argv[1]
    db_name = sys.argv[2]
    collection = sys.argv[3]
    batch_insert(filename, db_name, collection)
