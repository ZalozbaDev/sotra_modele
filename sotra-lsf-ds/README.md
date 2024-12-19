# sotra-Übersetzer 
entwickelt von der LMU, siehe https://statmt.org/wmt21/pdf/2021.wmt-1.72.pdf


## Container bauen

docker build -t sotra-lsf .

## Starten des Containers

docker run -v <./models1>:/app/models1 -p 3000:3000 -d --restart always -it sotra-lsf
(wobei <./models1> die absolute Pfadangabe zum models1-Verzeichnis sein muss; Docker erlaubt hier keine relativen Pfadangaben)

## Test

`wget -qO- localhost:3000/info`

bzw.

`curl -X POST http://localhost:3000/translate -H "Content-Type: application/json" -d '{"text": "To je test.","source_language": "hsb", "target_language": "de"}'`

## Libretranslate API (for Jitsi Meet compatibility)

`curl -X POST http://localhost:3000/libretranslate -H "Content-Type: application/json" -d '{"q": "To je test.","source": "hsb", "target": "de", "format": "text"}'`


