# Розгортання та перевірка IIoT-системи

Для запуску потрібні Docker Desktop із Docker Compose і вільний локальний
порт 1883. Команди нижче виконуються з кореня репозиторію у Windows CMD.

## Підготовка після клонування

1. Запустити Docker Desktop і дочекатися статусу `Engine running`.
2. Підготувати локальні файли конфігурації:

   ```cmd
   copy deploy\.env.example deploy\.env
   copy acl deploy\acl
   notepad deploy\.env
   ```

3. Заповнити `SIGNING_KEY` випадковим ключем, а чотири поля `*_PASSWORD` —
   окремими паролями для `pump-01`, `pump-02`, `ingest` і `alerts`.
   Випадковий ключ можна створити командою
   `python -c "import secrets; print(secrets.token_hex(32))"`.

4. Створити `deploy\passwd`. У Windows для цього потрібна утиліта
   `mosquitto_passwd.exe`. Нижче наведено команди для встановлення Mosquitto
   в `D:\Mosquitto`. Якщо програма в іншій папці, підставити її шлях.
   Для кожного користувача ввести той самий пароль, що й у `.env`.
   Першу команду з `-c` виконувати лише під час створення нового файлу.

   ```cmd
   "D:\Mosquitto\mosquitto_passwd.exe" -c deploy\passwd pump-01
   "D:\Mosquitto\mosquitto_passwd.exe" deploy\passwd pump-02
   "D:\Mosquitto\mosquitto_passwd.exe" deploy\passwd ingest
   "D:\Mosquitto\mosquitto_passwd.exe" deploy\passwd alerts
   ```

   У Linux із встановленою утилітою `mosquitto_passwd` ці чотири команди
   замінює `./deploy/make_passwd.sh`.

## Запуск

```cmd
docker compose -f deploy\docker-compose.yml up --build -d --wait
docker compose -f deploy\docker-compose.yml ps
```

Очікуваний результат — п’ять контейнерів у стані `healthy`: `broker`,
`gateway-01`, `gateway-02`, `ingest` та `alerts`.

## Демонстрація

Через 15 секунд після старту `gateway-01` симулятор вмикає несправність
підшипника. Коли вібрація перевищує поріг три виміри поспіль, сервіс `alerts`
реєструє `high_vibration raised`. Переглянути подію:

```cmd
docker compose -f deploy\docker-compose.yml logs --tail=10 alerts
```

Щоб продемонструвати зняття сповіщення, після появи `raised` перезапустити
лише перший шлюз. Симулятор почне з нормальної вібрації, а сервіс сповіщень
збереже попередній стан правила:

```cmd
docker compose -f deploy\docker-compose.yml restart gateway-01
docker compose -f deploy\docker-compose.yml logs -f alerts
```

У журналі з’явиться `cleared`, а після повторної несправності — нове `raised`.
Для виходу з перегляду журналу натиснути Ctrl+C.

Кількість записів у SQLite для кожного насоса перевіряється командою:

```cmd
docker compose -f deploy\docker-compose.yml exec -T ingest python -c "import sqlite3; db = sqlite3.connect('file:/data/iiot.db?mode=ro', uri=True); print(*db.execute('SELECT device_id, COUNT(*) FROM telemetry GROUP BY device_id ORDER BY device_id'), sep='\n'); db.close()"
```

У результаті мають бути два рядки: `pump-01` і `pump-02`.

## Зупинка

```cmd
docker compose -f deploy\docker-compose.yml down
```

Іменовані томи `db-data` і `broker-data` зберігаються між запусками.