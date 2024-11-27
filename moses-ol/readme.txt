For historical reasons, the first translation system, which was used for sotra until mid-2022 and was then replaced by a neural translator, is provided here. 
The system is based on the statistical translator "Moses" https://www2.statmt.org/moses/ .
The following translation directions are supported:
HSB -> DE
DE -> HSB






Installation:
1.
Unpack model.zip containing moses translation model data for the directions hsb->de and de->hsb.
The directory structure should then look like this:

├── Dockerfile
├── model
│   ├── de-hsb
│   │   ├── Corpus.blm.hsb
│   │   ├── de-hsb.zip
│   │   ├── git.log
│   │   ├── moses.ini
│   │   ├── phrase-table.minphr
│   │   ├── reordering-table.minlexr
│   │   ├── train.log
│   │   └── truecase-model.de
│   └── hsb-de
│       ├── Corpus.blm.de
│       ├── git.log
│       ├── hsb-de.zip
│       ├── moses.ini
│       ├── phrase-table.minphr
│       ├── reordering-table.minlexr
│       ├── train.log
│       └── truecase-model.hsb
├── nonbreaking_prefixes
│   ├── nonbreaking_prefix.de
│   └── nonbreaking_prefix.hsb
├── readme.txt
└── script
    ├── info_moses.sh
    ├── main_splitsentences.pl
    ├── nm_translate_de-hsb.sh
    ├── nm_translate_hsb-de.sh
    ├── ph_nes.pl
    ├── preproc_splitsentences.pl
    ├── sm_translate.sh
    ├── sm_translate_de-hsb.sh
    ├── sm_translate_hsb-de.sh
    ├── smt-ws.py
    ├── split_sequences_test.pl
    └── unksplit.pl



2.
docker build -t moses-smt .

3.
docker run -p 8080:8080 -it moses-smt

4.
curl -X POST http://localhost:8080/translate -H "Content-Type: application/json" -d '{"text": "To je test.", "source_language": "hsb", "target_language": "de"}'
curl -X POST http://localhost:8080/translate -H "Content-Type: application/json" -d '{"text": "Dies ist ein Test.", "source_language": "de", "target_language": "hsb"}

