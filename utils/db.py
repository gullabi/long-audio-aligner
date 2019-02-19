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
        self.collection_name = 'v1'

    def connect(self):
        client = MongoClient('localhost',27017)
        self.db = client[self.db_name]
        self.cache = self.db[self.collection_name]

    def insert(self, elements):
        for key, value in elements.items():
            value['ple_code'] = key
            self.insert_one(key, value)

    def insert_one(self, key, value, upsert=False):
        h = hashlib.md5(key.encode('utf8'))
        ref = self.cache.find_one({'_id': h.hexdigest()})

        while self.is_clean(value) != True:
            self.clean_keys(value)

        if ref:
            if upsert:
                self.cache.update({'_id': h.hexdigest()},
                                  {'_id': h.hexdigest(),
                                   'value': value},
                                   upsert=True)
            else:
                logging.info("%s already in db skipping"%key)
        else:
            self.cache.insert({'_id': h.hexdigest(),
                               'value': value})

    def get(self, ple_code):
        h = hashlib.md5(ple_code.encode('utf8'))
        ref = self.cache.find_one({'_id': h.hexdigest()})
        if ref:
            return ref
        else:
            return None

    def clean_keys(self, dic): 
        for key, value in dic.items():
            if '.' in key:
                # assumes the form sessions/2018_03_22_245800/text/12.yaml
                dic[key.split('.')[0]] = value
                dic.pop(key)
            if type(value) == dict:
                self.clean_keys(value)
            elif type(value) == list:
                for v in value:
                    if type(v) == dict:
                        self.clean_keys(v)

    def is_clean(self, dic):
        result = True
        for key, value in dic.items():
            if '.' in key:
                result =  False
                break
            if result == True:
                if type(value) == dict:
                    result = self.is_clean(value)
                    if result == False: break
                elif type(value) == list:
                    for v in value:
                        if type(v) == dict:
                            result = self.is_clean(v)
                            if result == False: break
        return result

if __name__ == "__main__":
    filename = sys.argv[1]
    batch_insert(filename)
