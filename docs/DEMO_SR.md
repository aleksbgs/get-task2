# Task 2: demonstracija

## 1. Pregled

Prikaži `src/handler.py`: funkcija preko Boto3 objavljuje `Hello, world!` na SNS topic. ARN dobija iz promenljive okruženja; pristup dobija preko IAM role.

U AWS konzoli prikaži:

- EventBridge Scheduler: `get-task2-daily-0100`, grupa `get-task2`, izraz `cron(0 1 * * ? *)`, zona `Europe/Belgrade`, flexible window `OFF`.
- Lambda: `get-task2-hello`, Python 3.14, 128 MB, timeout 10 sekundi.
- SNS: `get-task2-notifications`, Standard topic, ručno potvrđena Email pretplata.
- IAM: Scheduler sme da pozove samo ovu Lambdu; Lambda sme da objavi poruku samo na ovaj topic i upiše svoje logove.

## 2. Ručna provera

Koristi `aws lambda invoke` komandu iz README-a. U odgovoru proveri da nema `FunctionError`, a u rezultatu proveri `message_id` i `Hello, world!`. Zatim pokaži `published` zapis u CloudWatch-u i stvarno primljen email.

Uspešan SNS Publish bez potvrđene pretplate ne dokazuje prijem emaila.

## 3. Provera preko Scheduler-a

Da se test ne bi čekao do noći, u Scheduler konzoli napravi privremeni **one-time** raspored:

1. Ime `get-task2-demo`, grupa `get-task2`.
2. Vreme nekoliko minuta unapred, zona `Europe/Belgrade`, flexible window `OFF`.
3. Target: Lambda `get-task2-hello`, payload `{}`.
4. Izaberi postojeću rolu `get-task2-scheduler`.
5. Uključi automatsko brisanje rasporeda po završetku.

Sačekaj izvršavanje, zatim pokaži novo Lambda izvršavanje, CloudWatch zapis sa MessageId i primljen email. Proveri da je demo raspored uklonjen i da je ostao uključen samo dnevni raspored. One-time test dokazuje isti put Scheduler → Lambda → SNS; dnevno izvršavanje u 01:00 se potvrđuje odvojeno kada taj termin prođe.

## 4. Dokazi

U lokalni `evidence/` sačuvaj konfiguraciju dnevnog rasporeda, rezultat Lambda poziva, CloudWatch zapis i dokaz prijema poruke. Sakrij email adresu ako se screenshot deli. AWS prihvatanje poruke i prijem u sandučetu evidentiraj odvojeno.

## 5. Uklanjanje

Prikaži komande za isključivanje rasporeda i `terraform destroy` iz README-a. AWS upravlja najvećim delom logike; Mac ne mora da ostane uključen da bi dnevni raspored radio.
