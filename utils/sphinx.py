import os
import sys
import subprocess
import pocketsphinx.pocketsphinx as ps

class CMU(object):
    def __init__(self, model_path):
        self.model_path = model_path
        self.config = ps.Decoder.default_config()
        self.config.set_string('-hmm', os.path.join(model_path,
                                                 'acoustic-model-ptm'))
        self.config.set_string('-dict', os.path.join(model_path,
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
        self.config.set_string('-jsgf', None)

    def init_jsgf(self, grammar_file):
        self.config.set_string('-jsgf', grammar_file)
        self.config.set_string('-lm', None)

    def stream_decode(self, raw):
        if raw.endswith('.wav') and not os.path.isfile(raw.replace('.wav','.raw')):
                msg = 'converting %s to raw'%raw
                print(msg)
                self.convert2raw(raw)
                raw = raw.replace('.wav','.raw')
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
                            #print(self.segs[-1])
                        decoder.start_utt()
            else:
                # the last buffered stream
                for seg in decoder.seg():
                    self.segs.append([seg.word,
                                      seg.start_frame/100,
                                      seg.end_frame/100])
                    #print(self.segs[-1])
                break
        decoder.end_utt()

    @staticmethod
    def convert2raw(raw):
        args = ['sox', raw, '--bits', '16', '--encoding', 'signed-integer',
                '--endian', 'little', raw.replace('.wav', '.raw')]
        subprocess.call(args)

if __name__ == "__main__":
    audio = sys.argv[1]
    jsgf = sys.argv[2]
    cmu = CMU('../cmusphinx-models/ca-es')
    cmu.init_jsgf(jsgf)
    cmu.stream_decode(audio)
    print([s[0] for s in cmu.segs if s[0] not in ['<sil>', '(NULL)']])
