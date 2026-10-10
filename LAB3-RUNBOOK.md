<!-- ai-generated: 100% - Codex documented the implemented lab, reproducible measurements and receipt workflow. -->

# Laboratory 3 — uruchamianie i sprawdzanie

Wszystkie komendy wykonuj w katalogu repozytorium:

```sh
cd /Users/konradsieradzki/Documents/ChatGPT/ITSM
```

## Co działa

`GET /kb/search?q=...` waliduje zapytanie o długości 1–200 znaków i wykonuje
dokładnie jedno wywołanie `kb-index`. Nie ma cache ani ponawiania. Odpowiedź
200 zawiera niezmienione wyniki; błąd indeksu, brak połączenia albo timeout
dają 502 z kodem `upstream_unavailable`. Indeks ma profil opóźnień i błędów
Twojego loginu, nie profil kolegi ani wspólną stałą.

Middleware mierzy czas obsługi każdej odpowiedzi w sekundach i wystawia
histogram na `/metrics`. Etykiety to tylko metoda, szablon trasy i status HTTP.
ID zgłoszenia, tekst zapytania i nieznana ścieżka nie tworzą nowych szeregów.
Prometheus pobiera metryki co 5 s. Grafana pokazuje ruch, dostępność, p99,
udział odpowiedzi do 200 ms i szybkość zużywania obu budżetów błędów.

SLO: 99% dostępności i 99% odpowiedzi w 200 ms w oknie 30 dni. Każdy budżet
to 1% żądań, czyli czasowo równoważne 432 min. Cztery alerty porównują
dwa okna jednocześnie: szybki burn 14,4 (1h + 5m, P1) i wolny burn 6
(6h + 30m, P2), dla dostępności oraz opóźnienia. Reguły mają 5 min oczekiwania.
Pliki są provisionowane, więc start Grafany nie wymaga ręcznej konfiguracji.
Laboratoria 1 i 2 oraz trwałe zgłoszenia w nazwanym wolumenie pozostają dostępne.

## Uruchomienie aplikacji i dashboardu

Docker Desktop musi być uruchomiony. Następnie:

```sh
docker compose --profile observability up -d --build
curl http://localhost:8080/health
curl 'http://localhost:8080/kb/search?q=VPN'
curl 'http://localhost:8080/kb/search?q=force-error-demo'
curl http://localhost:8080/metrics
docker compose ps
```

Adresy:

- aplikacja / dokumentacja API: http://localhost:8080/docs
- dashboard Grafany: http://localhost:3000/d/svcdesk-lab3
- Prometheus / zapytania / reguły: http://localhost:9090
- statystyki indeksu: http://localhost:8081/stats

Grafana udostępnia anonimowy podgląd lokalnie. To konfiguracja laboratoryjna,
nie bezpieczne wdrożenie publiczne. Pierwszy wykres potrzebuje kilku scrape'ów
i ruchu; pusty wykres zaraz po starcie nie oznacza błędu. Wyślij kilka zapytań
lub wykonaj pomiar. Długie okna alertów wymagają dłuższej historii.

## Pełny checker i własne testy

```sh
docker pull ghcr.io/swasik/itsmlab:2026
./itsmlab.sh --version
./itsmlab.sh verify 3 --json report.json
docker compose --profile tests run --rm --build tests
```

`verify 3` buduje osobny tymczasowy projekt Compose, wykonuje pomiar,
sprawdza liczność szeregów, uruchamia zapytania dashboardu oraz testuje alerty
i ich mutacje. Zajmuje kilka minut i sprząta swoje kontenery. Nie zatrzymuje
Twojego projektu `itsm` i nie wysyła zgłoszenia na GitHub ani Moodle.
`report.json` jest lokalnym, ignorowanym raportem; wynik lokalny nie jest oceną.
Własne testy kończą się `ITSMLAB-TESTS: passed=34 failed=0`.

Same testy alertów, bez kilkuminutowego pomiaru:

```sh
docker run --rm -v "$PWD/prometheus:/p" -w /p --entrypoint promtool prom/prometheus:v3.15.0 check rules alerts.yml
docker run --rm -v "$PWD/prometheus:/p" -w /p --entrypoint promtool prom/prometheus:v3.15.0 test rules alerts_test.yml
```

## Pomiar rozkładu opóźnień

```sh
./itsmlab.sh load 3
```

To 5 s rozgrzewki, 60 s ruchu open-loop przy 40 żądaniach/s i 64 połączeniach,
a następnie osobny pomiar indeksu przez 30 s. p99 oznacza czas, którego nie
przekroczyło 99% żądań, nie średnią. Granice histogramu dobrano do pomiaru
Twojego loginu; ich uzasadnienie jest w `slo.md`. Zwykły pomiar nie korzysta
z Toxiproxy, nie zużywa prób zgłoszenia i nie publikuje wyników.

Nie przebudowuj ani nie restartuj aplikacji w trakcie pomiaru: reset liczników
psuje porównanie przed/po. Nie uruchamiaj równolegle innego obciążenia.

## Stretch: różnica klient–serwer

```sh
docker compose --profile gap up -d svcdesk kb-index toxiproxy
python3 gap/setup.py
./itsmlab.sh load 3 --base-url http://host.docker.internal:8666 --service-url kb-index=http://host.docker.internal:8081
```

Na tym Macu wrapper działa w kontenerze, dlatego `host.docker.internal`, a nie
`localhost`. Toxiproxy dodaje na drodze odpowiedzi 100 ms ± 10 ms. Klient widzi
to opóźnienie; timer wewnątrz aplikacji go nie widzi. Wyniki i interpretacja
są w `gap.json` i `gap/README.md`. Wyłączanie toksycznego proxy nie zmienia
zwykłego endpointu na 8080. Port 8666 służy tylko eksperymentowi.

## Stretch: rzeczywiste spany GenAI

`genai/capture.py` wykonał jedno rzeczywiste zapytanie do lokalnego modelu
Ollama, a oficjalna instrumentacja OpenTelemetry zapisała `genai/spans.json`.
`genai/DIFF.md` porównuje wszystkie emitowane klucze `gen_ai.*` z konkretną
wersją konwencji, wskazuje brakujące opcjonalne pola i ograniczenia telemetryczne.
Nie wymaga to płatnego API i nie wprowadza modelu do zależności aplikacji.

Model i kontener `itsm-lab3-ollama` są zachowane lokalnie, ale zatrzymane:

```sh
docker start itsm-lab3-ollama
uv venv .venv-genai --python 3.13
uv pip install --python .venv-genai/bin/python -r genai/requirements.txt
.venv-genai/bin/python genai/capture.py
docker stop itsm-lab3-ollama
```

Eksporter dopisuje nowe batche do pliku. Nie nadpisuj zgłoszonego dowodu
bez świadomego przeglądu i nowego commita. Pełny Stretch wymaga dowolnych
dwóch z trzech opcji; GenAI i latency-gap go spełniają. Kubernetes jest
opcjonalny i nie zwiększa dalej punktacji pakietu.

## Zatrzymanie bez utraty danych

```sh
docker compose --profile observability --profile gap down
```

Nie dopisuj `-v`, jeśli chcesz zachować zgłoszenia i dane monitoringu.

## Co jest faktycznie oceniane

GitHub issue w `swasik/itsm-2026-submissions` jest pokwitowaniem zgłoszenia,
nie issue w Twoim repo. Bot musi nadać etykiety `receipted`, `lab:3`,
`kind:submission`. Tier B pobiera pliki z pokwitowanego taga i ponownie
wykonuje checker. Nie ocenia lokalnego katalogu ani tekstu wpisanego w Moodle.
Tag po pokwitowaniu jest niezmienny. Poprawka wymaga nowego taga/próby.
W Moodle wklejasz URL tego issue i tag. Lab 3 nie wymaga receipt specs ani prediction.

Maksymalny pakiet automatyczny to wszystkie 6 Core oraz dowolne 2 Stretch.
Uzasadnienia czyta i ostateczną ocenę przyznaje prowadzący: automatyczny PASS
nie jest sam w sobie obietnicą maksymalnej oceny końcowej.
