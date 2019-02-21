import os
import subprocess
import logging
import utils.clean as cl

from utils.segment import log_subprocess_output
from utils.g2p import G2P

PROJECT_PATH = os.path.dirname(os.path.realpath(__file__)) 
TMP = os.path.join(PROJECT_PATH, '../tmp')

class Align(object):
    def __init__(self, audiofile, text, dictfile):
        if not os.path.isfile(audiofile):
            msg = '%s does not exist'%audiofile
            logging.error(msg)
            raise IOError(msg)

        if not text:
            msg = 'input text is empy'
            logging.error(msg)
            raise IOError(msg)

        self.audio = audiofile
        self.audio_basename = '.'.join(os.path.basename(audiofile).split('.')[:-1])
        tmp_base_dir = os.path.join(TMP,
                                    self.audio_basename[0],
                                    self.audio_basename[1])
        if not os.path.isdir(tmp_base_dir):
            os.makedirs(tmp_base_dir)
        self.audio_raw = os.path.join(tmp_base_dir,
                                      self.audio_basename+'.raw')
        self.audio_wav = self.audio_raw.replace('.raw', '.wav')
        self.text = text
        self.corpus = os.path.join(tmp_base_dir,
                                   self.audio_basename+'_cmu.txt')
        self.dictfile = dictfile
        self.align_outfile =  os.path.join(tmp_base_dir,
                                           self.audio_basename+'_align.json')

        self.sentences = []
        self.oov = set()
        self.words = set([line.split()[0] \
                         for line in open(self.dictfile).readlines()])
        self.g2p = G2P()

    def create_textcorpus(self):
        with open(self.corpus, 'w') as wout:
            clean_paragraph = cl.structure_clean(self.text)
            for token in cl.tokenize(clean_paragraph):
                if token:
                    token = cl.punctuation_normalize(token)
                    cmu = cl.reject.sub('', token.strip().lower())
                    self.oov = self.oov.union(set(cmu.split())\
                                                  .difference(self.words))
                    self.sentences.append(cmu)
                    wout.write('<s> %s </s>\n'%cmu)
        if self.oov:
            msg = 'oov words found for %s\n%s'%(self.audio, str(self.oov))
            logging.warning(msg)
            with open(self.dictfile, 'a') as out:
                for word in self.oov:
                    line = '%s\t%s\n'%(word, self.g2p.decode(word))
                    out.write(line)
                    self.words.add(word)
        if os.stat(self.corpus).st_size == 0:
            msg = "corpus output %s empty"%self.corpus
            logging.error(msg)
            raise ValueError(msg)

    def create_lm(self):
        if os.stat(self.corpus).st_size == 0:
            msg = "can not build lm with empty corpus %s"%self.corpus
            logging.error(msg)
            raise IOError(msg)
        tmp_vocab = self.corpus+'_tmp.vocab'
        idngram = self.corpus+'.idngram'
        self.lm = self.corpus.replace('.txt','.lm')
        if not os.path.isfile(self.lm):
            popen1 = subprocess.Popen(['text2wfreq'],
                                     stdin=open(self.corpus),
                                     stdout=subprocess.PIPE)
            popen1.wait()
            with open(tmp_vocab, 'w') as out:
                popen2 = subprocess.Popen(['wfreq2vocab'],
                                          stdin=popen1.stdout,
                                          stdout=out)
                popen2.wait()
            args3 =  ['text2idngram', '-n', '2', '-vocab', tmp_vocab,
                      '-idngram', idngram]
            popen3 = subprocess.Popen(args3, stdin=open(self.corpus),
                                             stdout=subprocess.DEVNULL,
                                             stderr=subprocess.STDOUT)
            popen3.wait()
            args4 = ['idngram2lm', '-n', '2', '-disc_ranges', '0', '0',
                     '-witten_bell', '-idngram', idngram,
                     '-vocab', tmp_vocab, '-arpa', self.lm]
            popen4 = subprocess.call(args4, stdout=subprocess.DEVNULL,
                                            stderr=subprocess.STDOUT)
        if not os.path.isfile(self.lm):
            msg = 'lm file %s not created'%self.lm
            logging.error(msg)
            raise IOError(msg)
        if os.stat(self.lm).st_size == 0:
            msg = "lm file %s empty"%self.lm
            logging.error(msg)
            raise IOError(msg)
        process = subprocess.Popen(['rm', idngram, tmp_vocab, self.corpus],
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT)
        with process.stdout:
            log_subprocess_output(process.stdout)

    def convert_audio(self):
        args = ['ffmpeg', '-y', '-hide_banner', '-loglevel', 'panic',\
                '-i', self.audio, '-ac', '1', '-ar', '16000',\
                self.audio_wav]
        if not os.path.isfile(self.audio_wav): 
            subprocess.call(args)
        args = ['sox', self.audio_wav, '--bits', '16', '--encoding', 'signed-integer',
                '--endian', 'little', self.audio_raw]
        if not os.path.isfile(self.audio_raw):
            subprocess.call(args)
        if not os.path.isfile(self.audio_raw):
            msg =  '%s does not exist. conversion failed'%self.audio_raw
            logging.error(msg)
            raise IOError(msg)
        process = subprocess.Popen(['rm',self.audio_wav],
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT)
        with process.stdout:
            log_subprocess_output(process.stdout)

    def results_exist(self):
        if os.path.isfile(self.align_outfile):
            if os.stat(self.align_outfile).st_size != 0:
                return True
        return False
