1. Container bauen:
docker build -t sotra-lsf .

2. Starten des Containers

docker run -v <./models1>:/app/models1 -p 3000:3000 -d --restart always -it sotra-lsf
(wobei <./models1> die absolute Pfadangabe zum models1-Verzeichnis sein muss; Docker erlaubt hier keine relativen Pfadangaben)

3. Test

wget -qO- localhost:3000/info

bzw.

curl -X POST http://localhost:3000/translate -H "Content-Type: application/json" -d '{"text": "To je test.","source_language": "hsb", "target_language": "de"}'


