#!/bin/sh
set -eu

cd "$(dirname "$0")"

if [ "$#" -eq 0 ]; then
    set -- pump-01 pump-02 ingest alerts
fi

if [ -e passwd ]; then
    echo "Файл passwd уже існує."
    exit 1
fi

umask 077
tmp_dir=$(mktemp -d .passwd.XXXXXX)
trap 'rm -rf "$tmp_dir"' EXIT

for user in "$@"; do
    echo "Введи пароль для $user із локального файлу .env"
    if [ -f "$tmp_dir/passwd" ]; then
        mosquitto_passwd "$tmp_dir/passwd" "$user"
    else
        mosquitto_passwd -c "$tmp_dir/passwd" "$user"
    fi
done

mv "$tmp_dir/passwd" passwd
echo "Файл passwd створено."