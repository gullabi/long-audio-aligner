import hashlib
import logging
import json
import sys

from pymongo import MongoClient

def batch_insert(filename):
    pdb = ParlaDB()
    pdb.connect()
    sessions = json.load(open(filename))
    pdb.insert(sessions)

class ParlaDB(object):
    def __init__(self):
        self.db_name = 'parlament'
        self.collection_name = 'v2'

    def connect(self):
        client = MongoClient('localhost',27017)
        self.db = client[self.db_name]
        self.collection = self.db[self.collection_name]

    def insert(self, elements):
        for key, value in elements.items():
            self.insert_one(key, value)

    def insert_one(self, key, value, upsert=False):
        h = hashlib.md5(key.encode('utf8'))
        ref = self.collection.find_one({'_id': h.hexdigest()})

        if ref:
            if upsert:
                self.collection.update({'_id': h.hexdigest()},
                                       {'_id': h.hexdigest(),
                                        'value': value},
                                         upsert=True)
            else:
                logging.info("%s already in db skipping"%key)
        else:
            self.collection.insert({'_id': h.hexdigest(),
                                    'value': value})

    def get(self, ple_code):
        h = hashlib.md5(ple_code.encode('utf8'))
        ref = self.collection.find_one({'_id': h.hexdigest()})
        if ref:
            return ref
        else:
            return None

if __name__ == "__main__":
    filename = sys.argv[1]
    batch_insert(filename)
