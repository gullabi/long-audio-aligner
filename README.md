# Long Audio Aligner

Intends to reproduce the segmentation method of the [2015 Panayotov et al.](http://www.danielpovey.com/files/2015_icassp_librispeech.pdf) Librispeech paper.

## Use
For now:

```
python align.py <audiofile> <textfile>
```

Needs `pocketsphinx` install and also all the necessary resources for the language (acoustic model, language model, phonetic dictionary).
