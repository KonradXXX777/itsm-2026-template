<!-- ai-generated: 100% - Codex documented the recorded workflow, reproducible checks and limitations without inventing live operations. -->

# Laboratorium 4 — uruchomienie i weryfikacja

Rozwiązanie korzysta z **nagrania `lab4-rec-1`**, przypisanego do loginu `konradxxx777`. Komputer ma 8 GB RAM, więc zgodnie z HANDOUT wybrano recorded path przed uruchamianiem playgroundu. Nie uruchamiano całego sklepu ani Kubernetes. Pełny Stretch wymaga **dwóch z trzech** rozszerzeń: tutaj wykonano S1 (drugi badacz AI) i S2 (zegary powiadomień). Opcjonalny S3/k8sgpt nie jest deklarowany jako wykonany.

Komendy wykonuj w katalogu tego repozytorium, przy uruchomionym Docker Desktop. Program `svcdesk` i rozwiązania Labs 1–3 pozostają bez zmian. Nowe pliki dotyczą analizy incydentu i polityki alarmów, nie zastępują aplikacji atrapą.

## Checker i testy

```sh
docker pull ghcr.io/swasik/itsmlab:2026
./itsmlab.sh --version
./itsmlab.sh recording 4
./itsmlab.sh incident 4
docker compose --profile tests run --rm --build tests
docker compose stop svcdesk kb-index
./itsmlab.sh verify 4 --json report.json
```

Użyty checker: **0.8.6**, digest `sha256:01b2c636d896f90ec4048553780a8d97a8da43008a4c964575d0f135ac1ca87d`. `verify` sprawdza lokalny katalog i uruchamia własne tymczasowe kontenery; niczego nie zgłasza i nie zużywa próby. Kontenery testowe mogą zniknąć po zakończeniu, dlatego nie muszą zostać na liście Docker Desktop. `report.json` jest lokalnym raportem, nie dowodem otrzymania oceny na GitHubie.

Nie uruchamiaj `verify` równolegle z własnym stosem/testami: checker usuwa mapowanie portu svcdesk, ale pomocniczy `kb-index` nadal używa hostowego **8081**. Zatrzymanie lokalnych dwóch usług przed `verify` zwalnia port, nie usuwa ich bazy ani kontenerów. Wykryliśmy ten konflikt podczas prób równoległych; końcową weryfikację wykonujemy już szeregowo.

Wynik lokalny z 24.10.2026: **Core 5/5**, **S1 i S2 zaliczone — pełny pakiet Stretch**, testy aplikacji **34 zaliczone, 0 błędów**; S3 niewykonany. Dwie kontrole wymagające tajnego ground truth (identyfikacja flag i komponentów) lokalnie mają `skip` — dopiero Tier B sprawdzi je na receipted tagu. To nie błąd do obchodzenia. Ocena artefaktu rozumowania należy do prowadzącego; lokalny checker nie gwarantuje maksymalnej oceny opisowej.

Własne testy `tests` sprawdzają także zachowanie dotychczasowego svcdesk. Mogą tworzyć testowe tickety w lokalnej bazie aplikacji; nie zmieniają oryginalnego JSON biletu w `incident/` ani nagrania. Zwykłe uruchomienie API:

```sh
docker compose up -d --build svcdesk
curl http://localhost:8080/health
docker compose ps
```

## Odtworzenie danych i własne zapytania

```sh
bash scripts/lab4_replay.sh start
curl http://127.0.0.1:19091/-/ready
```

Otwórz **http://127.0.0.1:19091/query**, wybierz historyczny czas **2026-10-12T05:06:00Z** (awaria) lub **04:56:00Z** (zdrowa baza). Zapytanie w bieżącym czasie zwróci pusty wynik, bo nagranie nie dopisuje nowych danych. Przykład p99 w milisekundach:

```promql
histogram_quantile(0.99, sum by(service_name,le)(rate(traces_span_metrics_duration_milliseconds_bucket{span_kind="SPAN_KIND_SERVER"}[5m])))
```

Przeliczenie zapisanych dowodów i wszystkich testowalnych hipotez (Python 3, biblioteka standardowa):

```sh
python3 scripts/lab4_evidence.py --url http://127.0.0.1:19091 --output /tmp/lab4-evidence-recheck.json
bash scripts/lab4_replay.sh stop
```

Z zainstalowanym PyYAML skrypt dodatkowo sprawdza cztery proponowane wyrażenia alarmowe. Ich składnię, routing i inhibicję sprawdza również `verify 4`. Replay rozpakowuje archiwum do nowego `/tmp/itsm-lab4-replay.*`; Prometheus ma tam zapisywalną kopię, lecz nie modyfikuje archiwum w repo. Retencja 100 lat zapobiega usunięciu historycznego bloku jako starego. `stop` zatrzymuje tylko własny oznaczony kontener, nie kasuje danych. Nie włącza scrapowania ani ponownej oceny historycznych reguł.

## Co jest dowodem, a co propozycją

- `incident/tsdb-snapshot.tar.gz`, `incident/ticket.json`, `ai-rca/transcript.md`: oryginały z przypisanego nagrania. Zawierają historyczne, nie nasze dzisiejsze działania. Nie poprawiamy transkryptu ani nie zamykamy fikcyjnie biletu.
- `ai-rca/second/transcript.md` i `.jsonl`: rzeczywiste lokalne wywołania agenta kursowego z modelem `qwen3:1.7b`. Zachowano nieudany pierwszy przebieg i powtórzenie z jednoznacznymi godzinami; model nie dostał diagnozy ani nazw flag.
- Dwa pliki `ai-rca-eval*.json`: cytaty hipotez oraz nasze testy PromQL, z wynikami i oceną. Porównanie wyjaśnia również błędy, nie tylko trafienia.
- `postmortem.md`: przyczyny i granice pewności, wpływ, rozdzielenie formalnego recovery od pełnej poprawy, plan działań ITSM-401…406 i osobny otwarty problem.
- `prometheus/demo-alerts.yml`, `alertmanager/`: proponowane reguły i testy, nie dowód, że te dokładne pliki działały historycznie.
- `comms-log.md`: hipotetyczne komunikaty i wyliczone terminy zgodnie z I-30; żaden komunikat nie został wysłany do regulatora.

## Ponowienie drugiego badacza

Nie jest potrzebne do ocenienia gotowego repo. Oryginalne `agent/agent.py`, `prom_mcp.py` i `requirements.txt` znajdują się w paczce Laboratory 4. Uruchom je w osobnym venv z Pythonem ≥3.10 i wersjami z paczki (`mcp==2.2.0`, `openai==3.19.2`). W tym wykonaniu użyto Python 3.13.15 i Ollama z `qwen3:1.7b`, bez płatnego API. Ollama potrzebowała ok. 2.8 GiB RAM i została potem zatrzymana. Nie zmieniano dostarczonego kodu agenta ani serwera MCP.

Ustaw `PROMETHEUS_URL=http://localhost:19091`, `BASE_URL=http://localhost:11434/v1`, `API_KEY=ollama`, `MODEL=qwen3:1.7b`, `MAX_STEPS=6` i **nową** ścieżkę `TRANSCRIPT`, żeby nie zmieniać złożonego dowodu. Pytaj o przedział 2026-10-12 04:55–05:15Z i porównanie 05:06Z z 04:56Z. Zapytania agenta są tylko do odczytu. Odpowiedź AI trzeba sprawdzić — nazwa alertu ani licznik `calls_total` nie dowodzą przyczyny ani czasu odpowiedzi.

## Zgłoszenie

Po lokalnym sprawdzeniu wysyłamy commit i **nowy, nieruszany tag** `lab4/v1`, następnie:

```sh
./itsmlab.sh submit 4 --kind submission --tag lab4/v1
```

Komenda przygotowuje adres formularza issue; samo jej uruchomienie nie otwiera zgłoszenia. Issue w `swasik/itsm-2026-submissions` musi zostać utworzone i otrzymać `receipted`, `lab:4`, `kind:submission`. Bot ocenia właśnie commit pod zarejestrowanym tagiem, nie bieżący katalog ani tekst Moodle. Do Moodle wkleja się **URL tego issue i tag `lab4/v1`**. Nie należy przesuwać tagu po receipt; ewentualna poprawka wymaga kolejnej próby i nowego tagu.
