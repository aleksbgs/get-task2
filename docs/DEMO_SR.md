# Task 2: demonstracija

## 1. Pregled

Prikaži `src/handler.py`: funkcija preko Boto3 objavljuje `Hello, world!` na SNS topic. ARN dobija iz promenljive okruženja; pristup dobija preko IAM role.

U AWS konzoli prikaži:

- EventBridge Scheduler: `get-task2-daily-0100`, grupa `get-task2`, izraz `cron(0 1 * * ? *)`, zona `Europe/Belgrade`, flexible window `OFF`.
- Lambda: `get-task2-hello`, Python 3.14, 128 MB, timeout 10 sekundi.
- SNS: `get-task2-notifications`, Standard topic, ručno potvrđena Email pretplata.
- IAM: Scheduler sme da pozove samo ovu Lambdu; Lambda sme da objavi poruku samo na ovaj topic i upiše svoje logove.

## 2. Ručna provera

Iz korena projekta, uz podešen `AWS_PROFILE`, pokreni:

```bash
make status
make subscriptions
make invoke
make logs SINCE=10m
```

`make invoke` proverava da nema `FunctionError`, kao i `message_id` i `Hello, world!` u rezultatu. Zatim pokaži `published` zapis u CloudWatch-u i stvarno primljen email. `make verify` objedinjuje status, poziv i logove; svaki poziv šalje novu test poruku. `make logs-follow` prati logove do Ctrl-C.

Uspešan SNS Publish bez potvrđene pretplate ne dokazuje prijem emaila.

## 3. Provera preko Scheduler-a

Da se test ne bi čekao do noći, napravi privremeni **one-time** raspored:

```bash
make demo-schedule DELAY=180
# Posle zakazanog vremena:
make logs
make demo-status
```

Komanda računa vreme u UTC-u, kreira `get-task2-demo` u postojećoj grupi i uključuje automatsko brisanje. Koristi postojeću Scheduler rolu i Lambdu. Dnevni raspored ostaje na `Europe/Belgrade`. Postojeći demo istog imena se ne prepisuje; prvo ga pregledaj, pa po potrebi ukloni sa `make demo-delete`.

Ekvivalentni ručni postupak u Scheduler konzoli:

1. Ime `get-task2-demo`, grupa `get-task2`.
2. Vreme nekoliko minuta unapred, zona `Europe/Belgrade`, flexible window `OFF`.
3. Target: Lambda `get-task2-hello`, payload `{"source":"demo-schedule"}`.
4. Izaberi postojeću rolu `get-task2-scheduler`.
5. Uključi automatsko brisanje rasporeda po završetku.

Sačekaj izvršavanje, zatim pokaži novo Lambda izvršavanje, CloudWatch zapis sa MessageId i primljen email. Proveri da je demo raspored uklonjen i da je ostao uključen samo dnevni raspored. One-time test dokazuje isti put Scheduler → Lambda → SNS; dnevno izvršavanje u 01:00 se potvrđuje odvojeno kada taj termin prođe.

## 4. Dokazi

Status, odgovor Lambda poziva, demo zahtev i logovi automatski se čuvaju u zasebnim poddirektorijumima `evidence/`. Dodaj dokaz prijema poruke. Sakrij email adresu ako se screenshot deli. AWS prihvatanje poruke i prijem u sandučetu evidentiraj odvojeno. Nestanak demo rasporeda sam po sebi nije dokaz da je email stigao.

## 5. Uklanjanje

```bash
make pause-plan
make show-plan PLAN=pause.tfplan
make pause
make demo-delete
make destroy-plan
make show-plan PLAN=destroy.tfplan
make destroy
make state
```

Pokreni sledeći korak tek kada prethodni uspe. Primena sačuvanog plana ne traži dodatnu potvrdu. Privremeni demo ukloni pre brisanja Terraform resursa. Za ponovno uključivanje postojeće infrastrukture koristi `make resume-plan`, pregled plana i `make resume`. Ako pauza treba da važi i za budući običan `make plan`, promeni i `schedule_enabled` u lokalnom tfvars fajlu.

`make help` prikazuje sve komande; `make package` pravi arhivu za predaju. AWS upravlja najvećim delom logike; lokalni računar ne mora da ostane uključen da bi dnevni raspored radio.
