# MOSES SMT

For historical reasons, the first translation system, which was used for sotra until mid-2022 and was then replaced by a neural translator, is provided here. 
The system is based on the statistical translator "Moses" https://www2.statmt.org/moses/ .
The following translation directions are supported:

```
hsb -> de
de -> hsb
```

## Installation

1.
Unpack model.zip containing the moses translation model data for the directions hsb->de and de->hsb.
The directory structure should then look like this:

```
├── Dockerfile
├── model
│   ├── de-hsb
│   └── hsb-de
├── nonbreaking_prefixes
└── script
```

2.
`docker build -t moses-smt .`

3.
`docker run -p 8080:8080 -it moses-smt`



## Test

`curl -X POST http://localhost:8080/translate -H "Content-Type: application/json" -d '{"text": "To je test.", "source_language": "hsb", "target_language": "de"}'`

`curl -X POST http://localhost:8080/translate -H "Content-Type: application/json" -d '{"text": "Dies ist ein Test.", "source_language": "de", "target_language": "hsb"}`

`curl http://localhost:8080/info`

