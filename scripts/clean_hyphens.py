import re
import sys
import pickle

from utils.clean import hyphenfix

def main(infile):
    
    lexicon = '../parlament-scrape/utils/lexicon_set_ca2.bin'
    with open(lexicon, 'rb') as lexicon_file:
        lexicon_set = pickle.load(lexicon_file)

    re_dot = re.compile('(?<=[^l])·(?=[^l])')

    outfile = get_out_name(infile)
    logfile = 'test/hyphen.log'
    with open(outfile, 'w') as out,\
         open(logfile, 'w') as log:
        for line in open(infile).readlines():
            dcleaned_line = re_dot.sub('-', line)
            hcleaned_line = hyphenfix(dcleaned_line, lexicon_set)
            if hcleaned_line != line:
                log.write('%s%s'%(line, hcleaned_line))
            out.write(hcleaned_line) 

def get_out_name(infile):
    basename = '.'.join(infile.split('.')[:-1])
    ext = infile.split('.')[-1]
    return '.'.join([basename+'_out', ext])

if __name__ == "__main__":
    infile = sys.argv[1]
    main(infile)
