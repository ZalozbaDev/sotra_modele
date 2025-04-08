# CTranslator Webservice

## Bauen des Containers

`docker build -t ctranslator .
`
## Starten des Containers

`docker run -d -p 25000:5000 --mount type=bind,source=$(pwd)/version.txt,target=/app/version.txt -it ctranslator`

## Test

`curl http://localhost:25000/info`





