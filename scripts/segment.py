import os
import subprocess
import logging

from math import floor
from itertools import repeat
from pymongo import MongoClient
from multiprocessing.dummy import Pool
from tqdm import tqdm

def main():
    db = db_connect()
    outdir = './'
    threads = 4
    process_list = []
    for element in db.find():
        process_list.append(element)

    logging.info('sending the list to be processed')
    if threads == 1:
        for element in process_list[:10]:
            segment(element, outdir)
    else:
        with Pool(threads) as pool:
            with tqdm(total=len(process_list)) as pbar:
                for i, _ in tqdm(enumerate(pool.imap(segment_all_star,
                                                     zip(process_list,
                                                         repeat(outdir))))):
                    pbar.update()
        pass

def segment(element, outdir):
    uri = element['value']['urls'][0][1]
    outfile = element['Innerfield']['segment_path']
    start = element['Innerfield']['start']
    end = element['Innerfield']['end']
    cut(uri, start, end, outfile)

def cut(uri, start, end, outfile):
    try:
        duration = end - start
    except:
        raise ValueError('start or end for segmentation is not given.')
    outpath = os.path.dirname(outfile)
    if not os.path.isdir(outpath):
        try:
            os.makedirs(outpath)
        except FileExistsError:
            # might be trying to mkdir simultaneously
            pass
    audio_tool = 'ffmpeg'
    seek = floor(start)
    seek_start = start - seek
    filename = os.path.basename(uri)
    basename, extension = filename.split('.')
    # TODO check basename fits the outfile
    if outfile.find(basename) == -1:
        print('basename does not fit the outfile\n %s vs %s'\
              %(basename, outfile))
        return False
    args = [audio_tool, '-hide_banner', '-loglevel', 'panic',
            '-ss', str(seek), '-i', uri, '-ss', \
            str(seek_start), '-t', str(duration), '-ac', '1', '-ar', '16000', \
            outfile]  
    if os.path.isfile(outfile):
        logging.info("%s already exists skipping"%outfile)
        return True
    else:
        logging.info('creating %s'%outfile)
        logging.debug(' '.join(args))
        subprocess.call(args)
        if not os.path.isfile(outfile):
            raise IOError("File not created from %s operation"
                          " %s"%(audio_tool, outfile))
        return True

def segment_all_star(process_outdir):
    return segment(*process_outdir)

def db_connect():
    client = MongoClient('localhost',27017)
    dbname = 'parlament'
    colname = 'aggregate_v3'
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

