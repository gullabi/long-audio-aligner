import sys
import os
import subprocess
import json

import utils.clean as cl
import utils.seq_aligner as seq
import pocketsphinx.pocketsphinx as ps

PROJECT_PATH = os.path.dirname(os.path.realpath(__file__)) 
TMP = os.path.join(PROJECT_PATH, 'tmp')
MODEL_PATH = os.path.join(PROJECT_PATH, '../cmusphinx-models/ca-es')
WORDS = set([line.split()[0] for line in open(os.path.join(MODEL_PATH, 
                               'pronounciation-dictionary.dict')).readlines()])

class Align(object):
    def __init__(self, audiofile, textfile):
        for f in [audiofile, textfile]:
            if not os.path.isfile(f):
                msg = '%s does not exist'%f
                raise IOError(msg)

        self.audio = audiofile
        self.audio_basename = '.'.join(os.path.basename(audiofile).split('.')[:-1])
        self.audio_raw = os.path.join(TMP, self.audio_basename+'.raw')
        self.audio_wav = self.audio_raw.replace('.raw', '.wav')
        self.text = textfile
        self.corpus = os.path.join(TMP, os.path.basename(textfile))\
                                                    .replace('.txt','_cmu.txt')
        self.align_outfile =  os.path.join(TMP, self.audio_basename+'_align.json')
        self.sentences = []
        self.oov = set()

    def create_textcorpus(self):
        with open(self.text, 'r') as corpus,\
             open(self.corpus, 'w') as wout:
            for line in corpus.readlines():
                clean_paragraph = cl.structure_clean(line.strip())
                for token in cl.tokenize(clean_paragraph):
                    if token:
                        token = cl.punctuation_normalize(token)
                        cmu = cl.reject.sub('', token.strip().lower())
                        self.oov = self.oov.union(set(cmu.split())\
                                                      .difference(WORDS))
                        self.sentences.append(cmu)
                        wout.write('<s> %s </s>\n'%cmu)
        print(self.oov)
        if os.stat(self.corpus).st_size == 0:
            msg = "corpus output %s empty"%self.corpus
            raise ValueError(msg)

    def create_lm(self):
        if os.stat(self.corpus).st_size == 0:
            msg = "can not build lm with empty corpus %s"%self.corpus
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
            popen3 = subprocess.Popen(args3, stdin=open(self.corpus))
            popen3.wait()
            args4 = ['idngram2lm', '-n', '2', '-disc_ranges', '0', '0',
                     '-witten_bell', '-idngram', idngram,
                     '-vocab', tmp_vocab, '-arpa', self.lm]
            popen4 = subprocess.call(args4)
        if not os.path.isfile(self.lm):
            msg = 'lm file %s not created'%self.lm
            raise IOError(msg)
        if os.stat(self.lm).st_size == 0:
            msg = "lm file %s empty"%self.lm
            raise IOError(msg)
        subprocess.Popen(['rm', idngram, tmp_vocab, self.corpus])

    def convert_audio(self):
        args = ['ffmpeg', '-hide_banner', '-loglevel', 'panic',\
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
           raise IOError(msg)
        subprocess.Popen(['rm',self.audio_wav])

    def results_exist(self):
        if os.path.isfile(self.align_outfile):
            if os.stat(self.align_outfile).st_size != 0:
                return True
        return False


class CMU(object):
    def __init__(self, model_path):
        self.model_path = model_path
        self.config = ps.Decoder.default_config()
        self.config.set_string('-hmm', os.path.join(MODEL_PATH,
                                                 'acoustic-model-ptm'))
        self.config.set_string('-dict', os.path.join(MODEL_PATH,
                                       'pronounciation-dictionary.dict'))
        self.config.set_string('-logfn', '/dev/null')

    def decode(self, raw, lm_file):
        for f in [raw, lm_file]:
            if not os.path.isfile(f):
                msg = '%s does not exist'
                raise IOError(msg)
        self.init_lm(lm_file)
        self.stream_decode(raw)

    def init_lm(self, lm_file):
        self.config.set_string('-lm', lm_file)

    def stream_decode(self, raw):
        self.segs = []
        decoder = ps.Decoder(self.config)
        stream = open(raw, 'rb')
        in_speech_bf = False
        decoder.start_utt()
        while True:
            buf = stream.read(1024)
            if buf:
                decoder.process_raw(buf, False, False)
                if decoder.get_in_speech() != in_speech_bf:
                    in_speech_bf = decoder.get_in_speech()
                    if not in_speech_bf:
                        decoder.end_utt()
                        for seg in decoder.seg():
                            self.segs.append([seg.word,
                                              seg.start_frame/100,
                                              seg.end_frame/100])
                            print(self.segs[-1])
                        decoder.start_utt()
            else:
                # the last buffered stream
                for seg in decoder.seg():
                    self.segs.append([seg.word,
                                      seg.start_frame/100,
                                      seg.end_frame/100])
                    print(self.segs[-1])
                break
        decoder.end_utt()

class Text(object):
    '''
    Class that mixes the cmu cleaned sentences with the aligned word timestamps
    which come from decoding
    '''
    def __init__(self, sentences, decode, outfile):
        self.sentences = sentences
        self.decode = decode
        self.align_outfile = outfile

        self.word_seq = []
        for sentence in self.sentences:
            self.word_seq += sentence.strip().split()

        self.decode_seq = []
        for word_timestamp in self.decode:
            decoded_word = word_timestamp[0]
            if decoded_word not in ['<s>', '<sil>', '</s>']:
                self.decode_seq.append(decoded_word)

        self.align_seq = []
        self.align_results = []
        # if align_outfile exists get alignment
        if os.path.isfile(self.align_outfile):
            msg = 'WARNING: alignment outfile %s exists'%self.align_outfile

    def align(self):
        #TODO cache alignment
        self.align_seq = seq.needle(self.word_seq, self.decode_seq)
        self.write_align()
        self.get_timestamps()

    def write_align(self, debug=False):
        s1, s2 = self.align_seq
        new_align_seq = ([],[])
        for w1, w2 in zip(s1, s2):
            if '--' not in [w1, w2] and w1 != w2:
                new_align_seq[0].append(w1)
                new_align_seq[0].append('--')
                new_align_seq[1].append('--')
                new_align_seq[1].append(w2)
            else:
                new_align_seq[0].append(w1)
                new_align_seq[1].append(w2)
        self.align_seq = new_align_seq
        if debug:
            s1, s2 = self.align_seq
            with open(self.align_outfile.replace('.json','.ls'), 'w') as out:
                for w1, w2 in zip(s1, s2):
                    out.write('%s %s\n'%(w1, w2))

    def read_align(self):
        ref_seq = []
        dec_seq = []
        for line in open(self.align_outfile).readlines():
            ref, dec = line.strip().split()
            ref_seq.append(ref)
            dec_seq.append(dec)
        return (ref_seq, dec_seq)

    def get_timestamps(self):
        s1, s2 = self.align_seq
        cl_decode = [seq for seq in self.decode \
                     if seq[0] not in ['<s>', '<sil>', '</s>']]
        for w1, w2 in zip(s1, s2):
            w = {}
            w['word'] = w1
            if w1 == w2:
                token = cl_decode[0]
                if w2 != token[0]:
                    msg = 'timestamp of word "%s" cannot be found'%w2
                    print(token[0])
                    print(cl_decode)
                    raise ValueError(msg)
                w['start'] = token[1]
                w['end'] = token[2]
                self.align_results.append(w)
                cl_decode.pop(0)
            elif w1 == '--':
                cl_decode.pop(0)
            elif w2 == '--':
                self.align_results.append(w)
            else:
                msg = 'unexpected alignment result: %s vs %s'%(w1, w2) 
                raise ValueError(msg)
        with open(self.align_outfile, 'w') as out:
            json.dump(self.align_results, out, indent=4)

def main(audiofile, textfile):
    align = Align(audiofile, textfile)
    if not align.results_exist():
        align.create_textcorpus()
        align.create_lm()
        align.convert_audio()
        decode_outfile = os.path.join(TMP, align.audio_basename+'_decode.json')
        if not os.path.isfile(decode_outfile):
            cs = CMU(MODEL_PATH)
            cs.decode(align.audio_raw, align.lm)
            segs = cs.segs
            with open(decode_outfile, 'w') as out:
                json.dump(segs, out)
        else:
            segs = json.load(open(decode_outfile))
        # TODO call decode functions in Align object
        decode_align = Text(align.sentences, segs, align.align_outfile)
        decode_align.align()
    else:
        msg = 'results already exist in %s'%align.align_outfile
        print(msg)

if __name__ == "__main__":
    audiofile = sys.argv[1]
    textfile = sys.argv[2]
    main(audiofile, textfile)
