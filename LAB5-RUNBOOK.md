<!-- ai-generated: 100% - Codex documented the independently tested CI and SARIF workflow for Lab 5. -->

# Lab 5 — CI, atestacje i bake-off

Zachowano działanie `svcdesk` i wcześniejsze tagi laboratoryjne. Lab 5 dodaje siedem zadań CI: build z testami,
skany zależności, sekretów i kodu, skan i publikację obrazu, kontrolę wyjątków oraz zbieranie dowodów SARIF.
Trivy blokuje odpowiednie podatności HIGH/CRITICAL, a gitleaks blokuje wykryte sekrety. Grype, OSV-Scanner
i Semgrep dostarczają raporty; nie blokują same z siebie. Pusta lista wyjątków nie wyłącza żadnej z bramek.

## Uruchomienie u siebie

W katalogu repo, po uruchomieniu Dockera i zalogowaniu `gh`:

```sh
docker pull ghcr.io/swasik/itsmlab:2026
./itsmlab.sh --version
python3 -S -E -m unittest discover -s tests -v
docker compose --profile tests run --rm --build tests
docker compose stop svcdesk kb-index
./itsmlab.sh mutants 5
GH_TOKEN="$(gh auth token)" ./itsmlab.sh verify 5 --json report.json
```

Użyto checkera 0.8.7. `verify 5` uruchamia testy lokalnie, ale **odczytuje GitHuba** w sprawach runów, obrazu
i atestacji. Nie tworzy zgłoszenia i nie zużywa próby. Port 8081 musi być wolny dla tymczasowego kontenera
`kb-index`; dlatego przed checkerem zatrzymujemy swój stos, bez kasowania bazy. Testy obejmują 34 przypadki
aplikacji oraz sześć testów regresyjnych obliczania macierzy. Dwie reguły Semgrep są dodatkowo sprawdzane bez sieci
przez checker, na przykładach pozytywnych, negatywnych i kodzie `src/`.

```sh
python3 -S -E bakeoff.py --labels bakeoff/labels.json bakeoff/sarif/*.sarif
```

Macierz liczy **defekty**, nie alerty: kilka trafień jednego defektu daje jeden TP dla narzędzia. Niezwiązane
trafienia są deduplikowane per reguła/plik/zakres. Zgodność sprawdzano na opublikowanym zestawie ćwiczeniowym
z paczki (rozpakowanym **poza** repo), bez biblioteki zewnętrznej. Nie przepisuj ręcznie wierszy w `bakeoff.json`.

## Dowody z GitHuba

- [Zielony przebieg main](https://github.com/KonradXXX777/itsm-2026-template/actions/runs/43652183021):
  wszystkie siedem zadań zaliczone. Artefakt `sbom` zawiera SPDX 2.3; pakiet GHCR jest publiczny.
- [Kontrolnie czerwony canary](https://github.com/KonradXXX777/itsm-2026-template/actions/runs/43652470581):
  na tym samym pipeline dodano tylko zestaw dla loginu. `deps` i `secrets` odrzucają go celowo; `capture` mimo
  to zebrał i podpisał pięć raportów. **Nie scalaj** `lab5/canary` z `main` i nie modyfikuj raportów.
- W [issue SARIF #424](https://github.com/swasik/itsm-2026-submissions/issues/424) bot rejestruje hashe raportów i
  ujawnia klucz. Nie jest to numer zgłoszenia do Moodle. Pięć plików z CI zweryfikowano poleceniem
  `gh attestation verify` z ograniczeniem do `ci.yml`, `refs/heads/lab5/canary` i commita canary.
- Szósty detektor powstał lokalnie: Ollama `qwen3:1.7b` (model `8f68893c685c`) dostała wyłącznie numerowane
  pliki `lab5-canary/` z commita `99c11a3574f3fc6594db6a17aae07df02009ce80` i prompt z pakietu. Model nie widział
  ani etykiet, ani raportów skanerów. Surowa odpowiedź w `bakeoff/transcript.md` pochodzi z
  2026-11-14 23:19:33 UTC, przed receipt. Bez płatnego API, klucza czy dodatkowego workflow.

Aby ręcznie zweryfikować oba podpisy pod właściwym digestem:

```sh
lab5_image='ghcr.io/konradxxx777/itsm-2026-template@sha256:e6989da5692ba056e639f8913c52be482548b548357baef8d5b8987099a45391'
lab5_repo='KonradXXX777/itsm-2026-template'
gh attestation verify "oci://$lab5_image" -R "$lab5_repo" \
  --signer-workflow "$lab5_repo/.github/workflows/ci.yml" --source-ref refs/heads/main
gh attestation verify "oci://$lab5_image" -R "$lab5_repo" \
  --signer-workflow "$lab5_repo/.github/workflows/ci.yml" --source-ref refs/heads/main \
  --predicate-type https://spdx.dev/Document/v2.3
```

W Moodle potrzebny jest URL **issue typu `submission`** z etykietami `receipted`, `lab:5`, `kind:submission`
oraz odpowiadający mu tag. Weryfikacja liczy się na jego niezmiennym commicie; w razie poprawki użyj nowego tagu,
nie przesuwaj już receipted tagu. Osobną ocenę za uzasadnienie w `TRIAGE.md` wystawia prowadzący.
