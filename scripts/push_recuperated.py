import os
import yaml

from pymongo import MongoClient
from bson.objectid import ObjectId

from recuperate_punct import db_connect

def main():
    recuperated = yaml.load(open("scripts/recuparate.yml"), yaml.FullLoader)
    db = db_connect()
    for value in recuperated.values():
        segments = value['segments']
        for segment in segments:
            if segment.get('original_words'):
                db_segment = db.find_one({'_id':segment['segment_id']})
                db_segment['Innerfield']['original_words'] = segment['original_words']
                db.update({'_id': segment['segment_id']},
                          {'Innerfield': db_segment['Innerfield']},
                          upsert=True)

if __name__ == "__main__":
    main()
